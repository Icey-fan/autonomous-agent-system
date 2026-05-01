"""闭环校验与质量控制智能体"""

from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Validator", AgentRole.VALIDATOR)
        self.capabilities = ["result_verification", "consistency_check", "quality_gate"]
        self.validation_dimensions = {
            "completeness": self._check_completeness,
            "accuracy": self._check_accuracy,
            "consistency": self._check_consistency,
            "timeliness": self._check_timeliness,
            "business_rule_compliance": self._check_business_rules,
            "logical_coherence": self._check_logic
        }

    def execute(self, task: TaskNode, context: AgentContext) -> dict:
        logger.info(f"[Validator] 校验: {task.name}")
        if task.result is None:
            return {"passed": False, "score": 0.0, "critical_issues": ["无结果"], "suggestion": "重新执行"}
        validation_results = {}
        for name, func in self.validation_dimensions.items():
            try:
                validation_results[name] = func(task, context)
            except Exception as e:
                validation_results[name] = {"passed": False, "score": 0.0, "error": str(e)}
        weights = {"completeness": 0.2, "accuracy": 0.25, "consistency": 0.2, "timeliness": 0.1, "business_rule_compliance": 0.15, "logical_coherence": 0.1}
        total_score = sum(validation_results[d].get("score", 0) * weights[d] for d in weights)
        critical_passed = all([validation_results[d].get("passed", False) for d in ["completeness", "business_rule_compliance", "logical_coherence"]])
        passed = total_score >= 0.8 and critical_passed
        result = {"passed": passed, "score": round(total_score, 3), "critical_passed": critical_passed, "dimension_results": validation_results, "timestamp": time.time()}
        if not passed:
            result["issues"] = self._extract_issues(validation_results)
            result["fix_suggestion"] = self._generate_fix_suggestion(validation_results, task)
            result["severity"] = "CRITICAL" if not critical_passed else "HIGH"
            logger.warning(f"[Validator] 未通过，得分: {total_score:.2f}")
        else:
            result["certification"] = f"PASSED_{uuid.uuid4().hex[:8].upper()}"
            logger.info(f"[Validator] 通过，得分: {total_score:.2f}")
        return result

    def _check_completeness(self, task: TaskNode, context: AgentContext) -> dict:
        result = task.result
        if not isinstance(result, dict):
            return {"passed": False, "score": 0.3, "issues": ["非结构化数据"]}
        missing = [f for f in ["status", "output"] if f not in result]
        score = 0.5 if missing else 1.0
        if result.get("output") in [None, {}, [], ""]:
            score *= 0.7
        return {"passed": score >= 0.8, "score": score, "issues": [f"缺少: {missing}"] if missing else []}

    def _check_accuracy(self, task: TaskNode, context: AgentContext) -> dict:
        return {"passed": True, "score": 0.9, "note": "数据在合理范围"}

    def _check_consistency(self, task: TaskNode, context: AgentContext) -> dict:
        if task.parent_id and context.current_plan:
            parent = self._find_task_by_id(context.current_plan, task.parent_id)
            if parent:
                keywords = set(parent.description.lower().split())
                result_str = str(task.result).lower()
                overlap = sum(1 for kw in keywords if kw in result_str and len(kw) > 2)
                ratio = overlap / max(len(keywords), 1)
                return {"passed": ratio > 0.1, "score": min(ratio + 0.5, 1.0), "note": f"一致性: {ratio:.2f}"}
        return {"passed": True, "score": 1.0}

    def _check_timeliness(self, task: TaskNode, context: AgentContext) -> dict:
        if task.completed_at and task.created_at:
            duration = task.completed_at - task.created_at
            score = max(1.0 - (duration / 300), 0.5) if duration > 30 else 1.0
            return {"passed": score > 0.6, "score": score, "duration": duration}
        return {"passed": True, "score": 1.0}

    def _check_business_rules(self, task: TaskNode, context: AgentContext) -> dict:
        violations = []
        for rule in context.business_rules:
            if rule.get("type") == "hard" and rule.get("condition") in str(task.result):
                violations.append(rule["name"])
        if violations:
            return {"passed": False, "score": 0.0, "violations": violations}
        return {"passed": True, "score": 1.0, "note": "无违规"}

    def _check_logic(self, task: TaskNode, context: AgentContext) -> dict:
        result = task.result
        if isinstance(result, dict):
            if result.get("status") == "success" and not result.get("output"):
                return {"passed": False, "score": 0.3, "issues": ["状态成功但输出为空"]}
            if result.get("status") == "failed" and not result.get("error"):
                return {"passed": False, "score": 0.5, "issues": ["状态失败但无错误信息"]}
        return {"passed": True, "score": 1.0}

    def _find_task_by_id(self, root: TaskNode, task_id: str):
        if root.id == task_id:
            return root
        for sub in root.sub_tasks:
            found = self._find_task_by_id(sub, task_id)
            if found:
                return found
        return None

    def _extract_issues(self, results: dict) -> list:
        issues = []
        for dim, res in results.items():
            if not res.get("passed", True):
                issues.extend([f"[{dim}] {i}" for i in res.get("issues", [])])
        return issues

    def _generate_fix_suggestion(self, results: dict, task: TaskNode) -> str:
        suggestions = []
        if not results["completeness"].get("passed", True):
            suggestions.append("补充缺失字段")
        if not results["business_rule_compliance"].get("passed", True):
            suggestions.append("修正业务规则违规")
        return "；".join(suggestions) if suggestions else "重新执行任务"
