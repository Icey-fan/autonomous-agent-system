"""长链推理与业务规则判断智能体"""

import statistics
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ReasonerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Reasoner", AgentRole.REASONER)
        self.capabilities = ["logical_deduction", "causal_analysis", "rule_engine"]
        self.inference_chains: dict = {}

    def execute(self, task: TaskNode, context: AgentContext) -> dict:
        logger.info(f"[Reasoner] 推理: {task.description}")
        chain_id = task.id
        steps = []
        ctx_analysis = self._analyze_context(task, context)
        steps.append({"step": 1, "type": "context_analysis", "thought": f"分析上下文: {list(context.external_data.keys())}", "confidence": 0.9})
        matched_rules = self._match_business_rules(task, context)
        steps.append({"step": 2, "type": "rule_matching", "thought": f"匹配到 {len(matched_rules)} 条规则", "confidence": 0.85 if matched_rules else 0.5})
        inference = self._perform_inference(task, context, matched_rules, ctx_analysis)
        steps.append({"step": 3, "type": "logical_inference", "thought": inference["reasoning_process"], "confidence": inference["step_confidence"]})
        final_confidence = inference.get("confidence", 0.8)
        if final_confidence < 0.7:
            steps.append({"step": 4, "type": "uncertainty_handling", "thought": f"置信度不足({final_confidence:.2f})", "action": "request_additional_verification"})
        self.inference_chains[chain_id] = steps
        return {
            "conclusion": inference["conclusion"],
            "reasoning_chain": steps,
            "confidence": final_confidence,
            "recommendations": inference.get("actions", []),
            "assumptions": inference.get("assumptions", [])
        }

    def _analyze_context(self, task: TaskNode, context: AgentContext) -> dict:
        return {"available_data": list(context.external_data.keys()), "rules_count": len(context.business_rules)}

    def _match_business_rules(self, task: TaskNode, context: AgentContext) -> list:
        matched = []
        task_desc = task.description.lower()
        for rule in context.business_rules:
            if any(kw.lower() in task_desc for kw in rule.get("keywords", [])):
                matched.append(rule)
        return matched

    def _perform_inference(self, task: TaskNode, context: AgentContext, rules: list, ctx: dict) -> dict:
        desc = task.description.lower()
        data = context.external_data
        if any(kw in desc for kw in ["流失", "churn", "留存"]):
            return self._infer_churn_risk(task, data, rules)
        elif any(kw in desc for kw in ["市场", "market", "进入"]):
            return self._infer_market_entry(task, data, rules)
        else:
            return self._infer_generic(task, data, rules)

    def _infer_churn_risk(self, task: TaskNode, data: dict, rules: list) -> dict:
        user_data = data.get("数据收集", {}).get("data", {})
        churn_rate = user_data.get("churn_rate", "5%")
        satisfaction = user_data.get("satisfaction", 4.0)
        rate_val = float(str(churn_rate).replace("%", ""))
        if rate_val > 10 or satisfaction < 3.5:
            conclusion = {"judgment": "高风险", "risk_level": "HIGH", "factors": [f"流失率{churn_rate}", f"满意度{satisfaction}"]}
            actions = ["启动用户召回计划", "优化产品体验", "建立预警机制"]
            confidence = 0.92
        elif rate_val > 7:
            conclusion = {"judgment": "中风险", "risk_level": "MEDIUM", "factors": [f"流失率{churn_rate}"]}
            actions = ["加强用户关怀", "分析流失原因"]
            confidence = 0.85
        else:
            conclusion = {"judgment": "低风险", "risk_level": "LOW", "factors": ["指标健康"]}
            actions = ["持续监控", "优化增长策略"]
            confidence = 0.88
        return {"conclusion": conclusion, "actions": actions, "confidence": confidence, "reasoning_process": f"基于流失率{churn_rate}和满意度{satisfaction}评估", "step_confidence": 0.9, "assumptions": ["数据样本具有代表性"]}

    def _infer_market_entry(self, task: TaskNode, data: dict, rules: list) -> dict:
        market_data = data.get("信息收集", {}).get("data", {})
        growth = market_data.get("growth_rate", "10%")
        growth_val = float(str(growth).replace("%", ""))
        if growth_val > 15:
            conclusion = {"judgment": "强烈推荐进入", "feasibility": "HIGH", "factors": [f"增长率{growth}优异"]}
            actions = ["制定进入策略", "寻找合作伙伴", "申请资质"]
            confidence = 0.9
        elif growth_val > 8:
            conclusion = {"judgment": "谨慎进入", "feasibility": "MEDIUM", "factors": ["市场增长稳健"]}
            actions = ["深入竞品分析", "小规模试点"]
            confidence = 0.82
        else:
            conclusion = {"judgment": "暂不推荐", "feasibility": "LOW", "factors": ["市场增长乏力"]}
            actions = ["持续观察", "寻找细分市场"]
            confidence = 0.85
        return {"conclusion": conclusion, "actions": actions, "confidence": confidence, "reasoning_process": f"基于增长率{growth}评估", "step_confidence": 0.88, "assumptions": ["宏观经济稳定"]}

    def _infer_generic(self, task: TaskNode, data: dict, rules: list) -> dict:
        return {"conclusion": {"judgment": "需进一步分析", "status": "INCONCLUSIVE"}, "actions": ["收集更多数据"], "confidence": 0.6, "reasoning_process": "任务类型不明确", "step_confidence": 0.7, "assumptions": ["基础数据完整"]}
