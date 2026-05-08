"""
Final decision output agent (Fixed)
Fixes: template-based decisions replaced with data-driven synthesis
"""

import uuid
import time
import statistics
from collections import Counter
from typing import Dict, List, Any, Optional
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class DecisionAgent(BaseAgent):
    """Data-driven decision synthesis agent"""

    def __init__(self):
        super().__init__("Decision", AgentRole.DECISION)
        self.capabilities = ["risk_assessment", "decision_synthesis", "output_formatting"]

    async def execute(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        logger.info("synthesizing_decision", task_id=task.id)
        
        sub_results = self._collect_sub_results(task)
        
        if not sub_results:
            logger.warning("no_sub_results", task_id=task.id)
            return self._create_fallback_decision(context)
        
        risk = self._assess_risk(sub_results, context)
        confidence = self._calculate_confidence(sub_results)
        impact = self._assess_impact(sub_results, context)
        
        decision = {
            "decision_id": f"DEC-{uuid.uuid4().hex[:8].upper()}",
            "recommendation": self._synthesize_recommendation(sub_results),
            "primary_plan": self._generate_primary_plan(sub_results),
            "alternative_plans": self._generate_alternatives(sub_results, context),
            "risk_assessment": risk,
            "confidence": confidence,
            "impact_assessment": impact,
            "action_items": self._extract_action_items(sub_results),
            "key_assumptions": self._extract_assumptions(sub_results),
            "decision_trace": {
                "input_tasks": len(sub_results),
                "data_sources": list(context.external_data.keys()),
                "rules_applied": len(context.business_rules),
                "execution_history_length": len(context.execution_history),
            },
            "timestamp": time.time(),
            "version": "2.0",
        }
        
        decision["quality_score"] = self._calculate_quality(decision)
        context.final_decision = decision
        
        logger.info(
            "decision_complete",
            task_id=task.id,
            quality=decision["quality_score"],
            risk_level=risk["level"],
            confidence=confidence["overall"],
        )
        return decision

    def _collect_sub_results(self, task: TaskNode) -> List[Dict[str, Any]]:
        """Collect all sub-task results recursively"""
        results = []
        
        def collect(node: TaskNode) -> None:
            if node.result is not None:
                results.append({
                    "task_id": node.id,
                    "task_name": node.name,
                    "role": node.role.value,
                    "result": node.result,
                    "validation": node.validation_result,
                    "status": node.status.name,
                })
            for sub in node.sub_tasks:
                collect(sub)
        
        collect(task)
        return results

    def _assess_risk(self, results: List[Dict[str, Any]], context: AgentContext) -> Dict[str, Any]:
        """Assess risk based on actual execution results"""
        factors = []
        score = 0.0
        
        for r in results:
            result_data = r.get("result", {})
            if isinstance(result_data, dict):
                # Check confidence from reasoning
                conf = result_data.get("confidence", 1.0)
                if conf < 0.7:
                    factors.append({
                        "source": r["task_name"],
                        "type": "LOW_CONFIDENCE",
                        "severity": "HIGH" if conf < 0.5 else "MEDIUM",
                        "confidence": conf,
                    })
                    score += (0.7 - conf)
                
                # Check for high-risk conclusions
                conclusion = result_data.get("conclusion", {})
                if isinstance(conclusion, dict):
                    risk_level = conclusion.get("risk_level", "LOW")
                    if risk_level == "HIGH":
                        factors.append({
                            "source": r["task_name"],
                            "type": "HIGH_RISK_CONCLUSION",
                            "severity": "HIGH",
                        })
                        score += 0.5
                    elif risk_level == "MEDIUM":
                        score += 0.2
        
        # Check validation failures
        failed_validations = [
            r for r in results 
            if r.get("validation") and not r["validation"].get("passed", True)
        ]
        if failed_validations:
            factors.append({
                "source": "validation",
                "type": "VALIDATION_FAILURE",
                "severity": "HIGH",
                "failed_count": len(failed_validations),
            })
            score += len(failed_validations) * 0.2
        
        # Check for failed tasks
        failed_tasks = [r for r in results if r.get("status") == "FAILED"]
        if failed_tasks:
            factors.append({
                "source": "execution",
                "type": "TASK_FAILURE",
                "severity": "HIGH",
                "failed_count": len(failed_tasks),
            })
            score += len(failed_tasks) * 0.3
        
        level = "HIGH" if score > 1.0 else "MEDIUM" if score > 0.5 else "LOW"
        
        return {
            "level": level,
            "score": min(score, 3.0),
            "factors": factors,
            "mitigation_suggestions": self._generate_mitigations(factors),
        }

    def _calculate_confidence(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate confidence statistics from results"""
        scores = []
        
        for r in results:
            result_data = r.get("result", {})
            if isinstance(result_data, dict):
                # Result confidence
                if "confidence" in result_data:
                    scores.append(result_data["confidence"])
                
                # Validation score
                validation = r.get("validation")
                if isinstance(validation, dict) and "score" in validation:
                    scores.append(validation["score"])
        
        if not scores:
            return {"overall": 0.5, "min": 0.5, "max": 0.5, "variance": 0, "sample_size": 0}
        
        return {
            "overall": round(sum(scores) / len(scores), 3),
            "min": round(min(scores), 3),
            "max": round(max(scores), 3),
            "variance": round(statistics.variance(scores), 3) if len(scores) > 1 else 0,
            "sample_size": len(scores),
        }

    def _assess_impact(self, results: List[Dict[str, Any]], context: AgentContext) -> Dict[str, Any]:
        """Assess business impact"""
        impacts = {
            "financial": {"level": "LOW", "factors": []},
            "operational": {"level": "LOW", "factors": []},
            "strategic": {"level": "LOW", "factors": []},
            "reputational": {"level": "LOW", "factors": []},
        }
        
        for r in results:
            task_name = r["task_name"].lower()
            result_data = r.get("result", {})
            
            # Market-related tasks
            if any(kw in task_name for kw in ["市场", "market", "进入", "entry", "expansion"]):
                impacts["strategic"]["level"] = "HIGH"
                impacts["strategic"]["factors"].append(f"Market decision: {r['task_name']}")
            
            # User/churn tasks
            if any(kw in task_name for kw in ["用户", "user", "流失", "churn", "留存", "retention"]):
                impacts["financial"]["level"] = "HIGH"
                impacts["financial"]["factors"].append(f"User impact: {r['task_name']}")
            
            # Check conclusion for impact hints
            if isinstance(result_data, dict):
                conclusion = result_data.get("conclusion", {})
                if isinstance(conclusion, dict):
                    if conclusion.get("risk_level") == "HIGH":
                        impacts["operational"]["level"] = "MEDIUM"
                        impacts["operational"]["factors"].append(f"High risk: {r['task_name']}")
        
        return impacts

    def _synthesize_recommendation(self, results: List[Dict[str, Any]]) -> str:
        """Synthesize recommendation from all judgments"""
        judgments = []
        confidences = []
        
        for r in results:
            result_data = r.get("result", {})
            if isinstance(result_data, dict) and "conclusion" in result_data:
                conclusion = result_data["conclusion"]
                if isinstance(conclusion, dict):
                    judgment = conclusion.get("judgment", "")
                    if judgment:
                        judgments.append(judgment)
                        confidences.append(result_data.get("confidence", 0.8))
        
        if judgments:
            # Weighted by confidence
            weighted_judgments = []
            for j, c in zip(judgments, confidences):
                weighted_judgments.extend([j] * int(c * 10))
            
            if weighted_judgments:
                most_common = Counter(weighted_judgments).most_common(1)[0][0]
                avg_confidence = sum(confidences) / len(confidences)
                return f"Recommendation: {most_common} (confidence: {avg_confidence:.2f})"
        
        return "Recommendation: Proceed with caution. Continue collecting key data before final decision."

    def _generate_primary_plan(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate primary action plan"""
        actions = []
        timeline_suggestions = []
        
        for r in results:
            result_data = r.get("result", {})
            if isinstance(result_data, dict):
                # Collect recommendations
                actions.extend(result_data.get("recommendations", []))
                actions.extend(result_data.get("actions", []))
                
                # Check for timeline hints
                if "timeline" in result_data:
                    timeline_suggestions.append(result_data["timeline"])
        
        # Deduplicate while preserving order
        seen = set()
        unique_actions = [a for a in actions if not (a in seen or seen.add(a))]
        
        # Prioritize actions
        prioritized = []
        for action in unique_actions:
            priority = "HIGH" if any(kw in action for kw in ["立即", "urgent", "critical", "launch"]) else "MEDIUM"
            prioritized.append({"action": action, "priority": priority})
        
        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        prioritized.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return {
            "name": "Primary Plan",
            "actions": prioritized[:5],
            "timeline": timeline_suggestions[0] if timeline_suggestions else "Recommend starting within 30 days",
        }

    def _generate_alternatives(self, results: List[Dict[str, Any]], context: AgentContext) -> List[Dict[str, Any]]:
        """Generate alternative plans based on risk assessment"""
        # Analyze results to customize alternatives
        has_high_risk = any(
            r.get("result", {}).get("conclusion", {}).get("risk_level") == "HIGH"
            for r in results
            if isinstance(r.get("result"), dict)
        )
        
        alternatives = [
            {
                "name": "Conservative Plan",
                "description": "Reduce risk, phased implementation",
                "pros": ["Risk controllable", "Lower initial investment", "Easy to rollback"],
                "cons": ["Higher opportunity cost", "Slower time-to-market"],
                "suitable_for": "High risk scenarios or limited resources",
            },
            {
                "name": "Aggressive Plan",
                "description": "Fast implementation, first-mover advantage",
                "pros": ["First-mover advantage", "Maximum market capture", "Competitive barrier"],
                "cons": ["High failure cost", "Resource intensive", "Difficult to change course"],
                "suitable_for": "Low risk, high opportunity scenarios",
            },
        ]
        
        # Add conditional alternative
        if has_high_risk:
            alternatives.append({
                "name": "Pilot Program",
                "description": "Small-scale test before full commitment",
                "pros": ["Validate assumptions", "Limited exposure", "Data-driven scaling"],
                "cons": ["Delayed full deployment", "Pilot may not represent full scale"],
                "suitable_for": "Uncertain markets or new initiatives",
            })
        else:
            alternatives.append({
                "name": "Wait-and-See",
                "description": "Maintain status quo, monitor signals",
                "pros": ["Zero additional cost", "More time to gather intelligence"],
                "cons": ["Potential missed opportunity", "Competitors may move first"],
                "suitable_for": "Stable situations with no urgency",
            })
        
        return alternatives

    def _extract_action_items(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract actionable items with priorities"""
        actions = []
        
        for r in results:
            result_data = r.get("result", {})
            if isinstance(result_data, dict):
                for action in result_data.get("actions", []):
                    priority = "HIGH" if any(kw in action for kw in ["立即", "urgent", "critical", "马上"]) else "MEDIUM"
                    actions.append({
                        "action": action,
                        "source": r["task_name"],
                        "priority": priority,
                        "task_id": r["task_id"],
                    })
        
        # Sort by priority
        priority
