"""
Long-chain reasoning and business rules agent (Fixed)
Fixes: hardcoded logic replaced with LLM-based reasoning
"""

import json
from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ReasonerAgent(BaseAgent):
    """LLM-based reasoning agent with chain-of-thought"""

    def __init__(self, llm_client: Optional[Any] = None):
        super().__init__("Reasoner", AgentRole.REASONER)
        self.capabilities = ["logical_deduction", "causal_analysis", "rule_engine"]
        self.llm_client = llm_client
        self.inference_chains: Dict[str, List[Dict[str, Any]]] = {}

    async def execute(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        logger.info("reasoning", task_id=task.id, description=task.description[:50])
        
        chain_id = task.id
        steps: List[Dict[str, Any]] = []
        
        # Step 1: Context analysis
        ctx_analysis = self._analyze_context(task, context)
        steps.append({
            "step": 1,
            "type": "context_analysis",
            "thought": f"Available data sources: {list(context.external_data.keys())}",
            "confidence": 0.9,
        })
        
        # Step 2: Business rule matching
        matched_rules = self._match_business_rules(task, context)
        steps.append({
            "step": 2,
            "type": "rule_matching",
            "thought": f"Matched {len(matched_rules)} business rules",
            "confidence": 0.85 if matched_rules else 0.5,
            "matched_rules": [r.get("name", "unnamed") for r in matched_rules],
        })
        
        # Step 3: Core inference
        if self.llm_client:
            inference = await self._llm_inference(task, context, matched_rules, ctx_analysis)
        else:
            inference = self._fallback_inference(task, context, matched_rules)
        
        steps.append({
            "step": 3,
            "type": "logical_inference",
            "thought": inference.get("reasoning_process", "Inference completed"),
            "confidence": inference.get("step_confidence", 0.8),
        })
        
        # Step 4: Uncertainty handling
        final_confidence = inference.get("confidence", 0.8)
        if final_confidence < 0.7:
            steps.append({
                "step": 4,
                "type": "uncertainty_handling",
                "thought": f"Confidence insufficient ({final_confidence:.2f}), requesting verification",
                "action": "request_additional_verification",
                "confidence": final_confidence,
            })
        
        self.inference_chains[chain_id] = steps
        
        result = {
            "conclusion": inference["conclusion"],
            "reasoning_chain": steps,
            "confidence": final_confidence,
            "recommendations": inference.get("actions", []),
            "assumptions": inference.get("assumptions", []),
        }
        
        logger.info("reasoning_complete", task_id=task.id, confidence=final_confidence)
        return result

    def _analyze_context(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        return {
            "available_data": list(context.external_data.keys()),
            "rules_count": len(context.business_rules),
            "task_type": task.name,
        }

    def _match_business_rules(self, task: TaskNode, context: AgentContext) -> List[Dict[str, Any]]:
        matched = []
        task_desc = task.description.lower()
        for rule in context.business_rules:
            keywords = rule.get("keywords", [])
            if any(kw.lower() in task_desc for kw in keywords):
                matched.append(rule)
        return matched

    async def _llm_inference(
        self, 
        task: TaskNode, 
        context: AgentContext, 
        rules: List[Dict[str, Any]], 
        ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM for sophisticated inference"""
        prompt = f"""Analyze the following task and data. Provide structured reasoning.
        
        Task: {task.description}
        Available Data: {json.dumps(ctx, ensure_ascii=False)}
        Business Rules: {json.dumps(rules, ensure_ascii=False)}
        External Data: {json.dumps({k: v.get('data', {}) for k, v in context.external_data.items()}, ensure_ascii=False)}
        
        Return JSON with:
        - conclusion: {{"judgment": "...", "risk_level": "HIGH|MEDIUM|LOW", "factors": [...]}}
        - actions: list of recommended actions
        - confidence: float 0-1
        - reasoning_process: string explaining the reasoning
        - assumptions: list of assumptions made
        """
        
        try:
            response = await self.llm_client.complete(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error("llm_inference_failed", error=str(e), fallback=True)
            return self._fallback_inference(task, context, rules)

    def _fallback_inference(
        self, 
        task: TaskNode, 
        context: AgentContext, 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Pattern-based fallback inference with real data analysis"""
        desc = task.description.lower()
        data = context.external_data
        
        # Extract actual metrics from research data
        metrics = self._extract_metrics(data)
        
        if any(kw in desc for kw in ["流失", "churn", "留存", "retention"]):
            return self._infer_churn_risk(task, metrics, rules)
        elif any(kw in desc for kw in ["市场", "market", "进入", "entry"]):
            return self._infer_market_entry(task, metrics, rules)
        else:
            return self._infer_generic(task, metrics, rules)

    def _extract_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actual metrics from research data"""
        metrics = {}
        for source_name, source_data in data.items():
            if isinstance(source_data, dict) and "data" in source_data:
                metrics.update(source_data["data"])
        return metrics

    def _infer_churn_risk(
        self, 
        task: TaskNode, 
        metrics: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Data-driven churn risk inference"""
        churn_rate = metrics.get("churn_rate", "5%")
        satisfaction = metrics.get("satisfaction", 4.0)
        active_users = metrics.get("active_users", 0)
        
        # Parse churn rate
        try:
            rate_val = float(str(churn_rate).replace("%", ""))
        except (ValueError, TypeError):
            rate_val = 5.0
        
        # Parse satisfaction
        try:
            sat_val = float(satisfaction)
        except (ValueError, TypeError):
            sat_val = 4.0
        
        factors = []
        if rate_val > 10:
            factors.append(f"High churn rate: {churn_rate}")
        if sat_val < 3.5:
            factors.append(f"Low satisfaction: {satisfaction}")
        if active_users < 10000:
            factors.append(f"Low user base: {active_users}")
        
        if rate_val > 10 or sat_val < 3.5:
            conclusion = {
                "judgment": "High Risk",
                "risk_level": "HIGH",
                "factors": factors or [f"Churn rate {churn_rate}, Satisfaction {satisfaction}"],
            }
            actions = ["Launch user recall campaign", "Optimize product experience", "Establish early warning system"]
            confidence = 0.92
        elif rate_val > 7:
            conclusion = {
                "judgment": "Medium Risk",
                "risk_level": "MEDIUM",
                "factors": factors or [f"Churn rate {churn_rate}"],
            }
            actions = ["Strengthen user engagement", "Analyze churn causes"]
            confidence = 0.85
        else:
            conclusion = {
                "judgment": "Low Risk",
                "risk_level": "LOW",
                "factors": factors or ["Metrics healthy"],
            }
            actions = ["Continue monitoring", "Optimize growth strategy"]
            confidence = 0.88
        
        return {
            "conclusion": conclusion,
            "actions": actions,
            "confidence": confidence,
            "reasoning_process": f"Based on churn rate {churn_rate}, satisfaction {satisfaction}, and {active_users} active users",
            "step_confidence": 0.9,
            "assumptions": ["Data sample is representative", "Metrics are current"],
        }

    def _infer_market_entry(
        self, 
        task: TaskNode, 
        metrics: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Data-driven market entry inference"""
        growth = metrics.get("growth_rate", "10%")
        market_size = metrics.get("market_size", "50B")
        
        try:
            growth_val = float(str(growth).replace("%", ""))
        except (ValueError, TypeError):
            growth_val = 10.0
        
        if growth_val > 15:
            conclusion = {
                "judgment": "Strongly recommended",
                "feasibility": "HIGH",
                "factors": [f"Excellent growth rate: {growth}", f"Market size: {market_size}"],
            }
            actions = ["Develop entry strategy", "Find local partners", "Apply for licenses"]
            confidence = 0.9
        elif growth_val > 8:
            conclusion = {
                "judgment": "Cautious entry",
                "feasibility": "MEDIUM",
                "factors": ["Steady market growth", f"Market size: {market_size}"],
            }
            actions = ["Deep competitor analysis", "Small-scale pilot"]
            confidence = 0.82
        else:
            conclusion = {
                "judgment": "Not recommended for now",
                "feasibility": "LOW",
                "factors": [f"Sluggish growth: {growth}"],
            }
            actions = ["Continue monitoring", "Look for niche segments"]
            confidence = 0.85
        
        return {
            "conclusion": conclusion,
            "actions": actions,
            "confidence": confidence,
            "reasoning_process": f"Based on growth rate {growth} and market size {market_size}",
            "step_confidence": 0.88,
            "assumptions": ["Macroeconomic stability", "Regulatory environment favorable"],
        }

    def _infer_generic(
        self, 
        task: TaskNode, 
        metrics: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generic inference with data awareness"""
        return {
            "conclusion": {
                "judgment": "Further analysis needed",
                "status": "INCONCLUSIVE",
                "available_metrics": list(metrics.keys()),
            },
            "actions": ["Collect more specific data"],
            "confidence": 0.6,
            "reasoning_process": "Task type unclear or insufficient data",
            "step_confidence": 0.7,
            "assumptions": ["Basic data is complete"],
        }
