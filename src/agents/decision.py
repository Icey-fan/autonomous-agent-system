"""最终决策输出智能体"""

import uuid
import time
import statistics
from collections import Counter
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class DecisionAgent(BaseAgent):
    def __init__(self):
        super().__init__("Decision", AgentRole.DECISION)
        self.capabilities = ["risk_assessment", "decision_synthesis", "output_formatting"]

    def execute(self, task: TaskNode, context: AgentContext) -> dict:
        logger.info(f"[Decision] 合成最终决策...")
        sub_results = self._collect_sub_results(task)
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
            "decision_trace": {"input_tasks": len(sub_results), "data_sources": list(context.external_data.keys()), "rules_applied": len(context.business_rules)},
            "timestamp": time.time(),
            "version": "1.0"
        }
        decision["quality_score"] = self._calculate_quality(decision)
        context.final_decision = decision
        logger.info(f"[Decision] 完成，质量: {decision['quality_score']:.2f}, 风险: {risk['level']}")
        return decision

    def _collect_sub_results(self, task: TaskNode) -> list:
        results = []
        def collect(node: TaskNode):
            if node.result is not None:
                results.append({"task_id": node.id, "task_name": node.name, "role": node.role.value, "result": node.result, "validation": node.validation_result})
            for sub in node.sub_tasks:
                collect(sub)
        collect(task)
        return results

    def _assess_risk(self, results: list, context: AgentContext) -> dict:
        factors = []
        score = 0.0
        for r in results:
            if isinstance(r.get("result"), dict):
                conf = r["result"].get("confidence", 1.0)
                if conf < 0.7:
                    factors.append({"source": r["task_name"], "type": "LOW_CONFIDENCE", "severity": "HIGH" if conf < 0.5 else "MEDIUM"})
                    score += (0.7 - conf)
        failed = [r for r in results if r.get("validation") and not r["validation"].get("passed", True)]
        if failed:
            factors.append({"source": "validation", "type": "VALIDATION_FAILURE", "severity": "HIGH"})
            score += len(failed) * 0.2
        level = "HIGH" if score > 1.0 else "MEDIUM" if score > 0.5 else "LOW"
        return {"level": level, "score": min(score, 3.0), "factors": factors, "mitigation_suggestions": self._generate_mitigations(factors)}

    def _calculate_confidence(self, results: list) -> dict:
        scores = []
        for r in results:
            if isinstance(r.get("result"), dict):
                scores.append(r["result"].get("confidence", 0.8))
            if r.get("validation"):
                scores.append(r["validation"].get("score", 1.0))
        if not scores:
            return {"overall": 0.5, "min": 0.5, "max": 0.5, "variance": 0}
        return {"overall": sum(scores)/len(scores), "min": min(scores), "max": max(scores), "variance": statistics.variance(scores) if len(scores) > 1 else 0, "sample_size": len(scores)}

    def _assess_impact(self, results: list, context: AgentContext) -> dict:
        impacts = {"financial": {"level": "MEDIUM"}, "operational": {"level": "LOW"}, "strategic": {"level": "HIGH"}, "reputational": {"level": "LOW"}}
        for r in results:
            if "市场" in r["task_name"] or "进入" in r["task_name"]:
                impacts["strategic"]["level"] = "HIGH"
            if "用户" in r["task_name"] and "流失" in r["task_name"]:
                impacts["financial"]["level"] = "HIGH"
        return impacts

    def _synthesize_recommendation(self, results: list) -> str:
        judgments = []
        for r in results:
            if isinstance(r.get("result"), dict) and "conclusion" in r["result"]:
                judgments.append(r["result"]["conclusion"].get("judgment", ""))
        if judgments:
            most_common = Counter(judgments).most_common(1)[0][0]
            return f"综合评估建议：{most_common}"
        return "建议采取审慎策略，继续收集关键数据后再决策"

    def _generate_primary_plan(self, results: list) -> dict:
        actions = []
        for r in results:
            if isinstance(r.get("result"), dict):
                actions.extend(r["result"].get("recommendations", []))
                actions.extend(r["result"].get("actions", []))
        return {"name": "主方案", "actions": list(dict.fromkeys(actions))[:5], "timeline": "建议30天内启动"}

    def _generate_alternatives(self, results: list, context: AgentContext) -> list:
        return [
            {"name": "保守方案", "description": "降低风险，分阶段推进", "pros": ["风险可控"], "cons": ["机会成本高"]},
            {"name": "激进方案", "description": "快速推进，抢占先机", "pros": ["先发优势"], "cons": ["失败成本高"]},
            {"name": "观望方案", "description": "维持现状，等待信号", "pros": ["零额外成本"], "cons": ["可能错失机会"]}
        ]

    def _extract_action_items(self, results: list) -> list:
        actions = []
        for r in results:
            if isinstance(r.get("result"), dict):
                for action in r["result"].get("actions", []):
                    actions.append({"action": action, "source": r["task_name"], "priority": "HIGH" if "立即" in action else "MEDIUM"})
        return actions

    def _extract_assumptions(self, results: list) -> list:
        assumptions = []
        for r in results:
            if isinstance(r.get("result"), dict):
                assumptions.extend(r["result"].get("assumptions", []))
        return list(dict.fromkeys(assumptions)) if assumptions else ["市场环境稳定", "数据来源可靠"]

    def _calculate_quality(self, decision: dict) -> float:
        factors = [decision["confidence"]["overall"] * 0.3, (1.0 if decision["risk_assessment"]["level"] != "HIGH" else 0.5) * 0.25, (len(decision["alternative_plans"]) / 3) * 0.2, (1.0 if decision["action_items"] else 0.3) * 0.15, (decision["confidence"]["sample_size"] / 10) * 0.1]
        return min(sum(factors), 1.0)

    def _generate_mitigations(self, factors: list) -> list:
        mitigations = []
        for f in factors:
            if f["type"] == "LOW_CONFIDENCE":
                mitigations.append(f"针对'{f['source']}'补充数据收集")
            elif f["type"] == "VALIDATION_FAILURE":
                mitigations.append("重新执行失败任务，检查参数")
        return mitigations if mitigations else ["持续监控关键指标"]
