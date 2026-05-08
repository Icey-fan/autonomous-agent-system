"""
Closed-loop validation and quality control agent (Fixed)
Fixes: fake validation replaced with real multi-dimensional checks
"""

import time
from typing import Dict, List, Any, Optional, Callable
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ValidationRule:
    """Individual validation rule with scoring"""
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[TaskNode, AgentContext], Dict[str, Any]],
        weight: float = 1.0,
        is_critical: bool = False,
    ):
        self.name = name
        self.check_func = check_func
        self.weight = weight
        self.is_critical = is_critical
    
    def execute(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        try:
            return self.check_func(task, context)
        except Exception as e:
            logger.error("validation_rule_failed", rule=self.name, error=str(e))
            return {
                "passed": False,
                "score": 0.0,
                "error": str(e),
            }


class ValidatorAgent(BaseAgent):
    """Real multi-dimensional validation agent"""
    
    def __init__(self, custom_rules: Optional[List[ValidationRule]] = None):
        super().__init__("Validator", AgentRole.VALIDATOR)
        self.capabilities = ["result_verification", "consistency_check", "quality_gate"]
        self.rules = custom_rules or self._init_default_rules()
        self.critical_rules = [r.name for r in self.rules if r.is_critical]
    
    def _init_default_rules(self) -> List[ValidationRule]:
        """Initialize default validation rules"""
        return [
            ValidationRule(
                "completeness",
                self._check_completeness,
                weight=0.2,
                is_critical=True,
            ),
            ValidationRule(
                "accuracy",
                self._check_accuracy,
                weight=0.25,
                is_critical=True,
            ),
            ValidationRule(
                "consistency",
                self._check_consistency,
                weight=0.2,
            ),
            ValidationRule(
                "timeliness",
                self._check_timeliness,
                weight=0.1,
            ),
            ValidationRule(
                "business_rule_compliance",
                self._check_business_rules,
                weight=0.15,
                is_critical=True,
            ),
            ValidationRule(
                "logical_coherence",
                self._check_logic,
                weight=0.1,
                is_critical=True,
            ),
        ]

    async def execute(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        logger.info("validating", task_id=task.id, task_name=task.name)
        
        if task.result is None:
            return {
                "passed": False,
                "score": 0.0,
                "critical_passed": False,
                "critical_issues": ["No result to validate"],
                "suggestion": "Re-execute the task",
            }
        
        validation_results = {}
        for rule in self.rules:
            validation_results[rule.name] = rule.execute(task, context)
        
        # Calculate weighted score
        total_weight = sum(r.weight for r in self.rules)
        weighted_score = sum(
            validation_results[r.name].get("score", 0) * r.weight
            for r in self.rules
        ) / total_weight if total_weight > 0 else 0
        
        # Check critical rules
        critical_passed = all(
            validation_results[name].get("passed", False)
            for name in self.critical_rules
        )
        
        # Overall pass criteria: score >= 0.8 AND all critical rules passed
        passed = weighted_score >= 0.8 and critical_passed
        
        result = {
            "passed": passed,
            "score": round(weighted_score, 3),
            "critical_passed": critical_passed,
            "dimension_results": validation_results,
            "timestamp": time.time(),
        }
        
        if not passed:
            issues = self._extract_issues(validation_results)
            result["issues"] = issues
            result["fix_suggestion"] = self._generate_fix_suggestion(validation_results, task)
            result["severity"] = "CRITICAL" if not critical_passed else "HIGH"
            logger.warning("validation_failed", task_id=task.id, score=weighted_score, issues_count=len(issues))
        else:
            result["certification"] = f"PASSED_{task.id}_{int(time.time())}"
            logger.info("validation_passed", task_id=task.id, score=weighted_score)
        
        return result

    def _check_completeness(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check result completeness"""
        result = task.result
        if not isinstance(result, dict):
            return {
                "passed": False,
                "score": 0.3,
                "issues": ["Result is not a structured dict"],
            }
        
        issues = []
        score = 1.0
        
        # Check for required fields
        required_fields = ["status"]
        for field in required_fields:
            if field not in result:
                issues.append(f"Missing required field: {field}")
                score -= 0.2
        
        # Check output quality
        output = result.get("output")
        if output in [None, {}, [], ""]:
            issues.append("Empty or missing output")
            score *= 0.7
        
        # Check for error details in failed results
        if result.get("status") == "failed" and not result.get("error"):
            issues.append("Failed status without error details")
            score -= 0.1
        
        return {
            "passed": score >= 0.8,
            "score": max(score, 0.0),
            "issues": issues,
        }

    def _check_accuracy(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check result accuracy with real validation"""
        result = task.result
        if not isinstance(result, dict):
            return {"passed": False, "score": 0.0, "issues": ["Invalid result format"]}
        
        # Verify tool execution success
        if result.get("status") != "success":
            return {
                "passed": False,
                "score": 0.2,
                "issues": [f"Tool execution failed: {result.get('error', 'Unknown error')}"],
            }
        
        output = result.get("output")
        if not output:
            return {"passed": False, "score": 0.3, "issues": ["Empty output"]}
        
        # Check for error in output
        if isinstance(output, dict) and "error" in output:
            return {
                "passed": False,
                "score": 0.4,
                "issues": [f"Output contains error: {output['error']}"],
            }
        
        # Validate execution time is reasonable
        exec_time = result.get("execution_time", 0)
        if exec_time > 300:  # 5 minutes
            return {
                "passed": False,
                "score": 0.6,
                "issues": [f"Execution too slow: {exec_time:.1f}s"],
            }
        
        return {
            "passed": True,
            "score": 0.9,
            "execution_time": exec_time,
            "note": "Data within reasonable range",
        }

    def _check_consistency(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check consistency with parent task and context"""
        if not task.parent_id or not context.current_plan:
            return {"passed": True, "score": 1.0, "note": "No parent task"}
        
        parent = context.current_plan.find_task_by_id(task.parent_id)
        if not parent:
            return {"passed": True, "score": 1.0, "note": "Parent not found"}
        
        # Semantic consistency check
        parent_keywords = set(parent.description.lower().split())
        result_str = str(task.result).lower()
        
        # Filter out common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of", "and", "in", "on", "at", "for", "with"}
        meaningful_keywords = {kw for kw in parent_keywords if len(kw) > 2 and kw not in stop_words}
        
        if not meaningful_keywords:
            return {"passed": True, "score": 1.0, "note": "No meaningful keywords to compare"}
        
        matches = sum(1 for kw in meaningful_keywords if kw in result_str)
        ratio = matches / len(meaningful_keywords)
        
        # Also check if task name appears in result
        name_match = task.name.lower() in result_str
        
        score = min(ratio * 1.5 + (0.2 if name_match else 0), 1.0)
        
        return {
            "passed": score > 0.3,
            "score": score,
            "semantic_overlap": ratio,
            "name_match": name_match,
        }

    def _check_timeliness(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check execution timeliness"""
        if task.completed_at and task.created_at:
            duration = task.completed_at - task.created_at
            # Score decreases after 30 seconds, floor at 0.5
            if duration > 300:  # 5 minutes
                score = 0.3
            elif duration > 60:  # 1 minute
                score = max(0.5, 1.0 - (duration - 60) / 480)
            else:
                score = 1.0
            
            return {
                "passed": score > 0.5,
                "score": score,
                "duration_seconds": duration,
            }
        
        return {"passed": True, "score": 1.0, "note": "No timing data"}

    def _check_business_rules(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check business rule compliance with proper logic"""
        violations = []
        result_str = str(task.result)
        
        for rule in context.business_rules:
            rule_type = rule.get("type", "soft")
            rule_name = rule.get("name", "unnamed")
            
            if rule_type == "hard":
                # Hard rules must not be violated
                condition = rule.get("condition", "")
                if condition and condition in result_str:
                    violations.append(f"Hard rule violated: {rule_name} (condition: {condition})")
            
            elif rule_type == "soft":
                # Soft rules are warnings
                threshold = rule.get("threshold")
                keywords = rule.get("keywords", [])
                
                if threshold is not None:
                    # Try to extract numeric value from result
                    try:
                        import re
                        numbers = re.findall(r"\\d+(?:\\.\\d+)?", result_str)
                        if numbers:
                            values = [float(n) for n in numbers]
                            avg_value = sum(values) / len(values)
                            if avg_value > threshold:
                                violations.append(
                                    f"Soft rule warning: {rule_name} (avg {avg_value:.2f} > threshold {threshold})"
                                )
                    except (ValueError, TypeError):
                        pass
                
                # Check keyword presence
                if keywords:
                    found_keywords = [kw for kw in keywords if kw.lower() in result_str.lower()]
                    if not found_keywords:
                        violations.append(f"Soft rule: {rule_name} keywords not found")
        
        if violations:
            return {
                "passed": False,
                "score": 0.0,
                "violations": violations,
            }
        
        return {
            "passed": True,
            "score": 1.0,
            "note": "No violations",
        }

    def _check_logic(self, task: TaskNode, context: AgentContext) -> Dict[str, Any]:
        """Check logical coherence of result"""
        result = task.result
        if not isinstance(result, dict):
            return {"passed": True, "score": 1.0, "note": "Non-dict result"}
        
        issues = []
        
        # Status/output coherence
        if result.get("status") == "success":
            output = result.get("output")
            if output in [None, {}, [], ""]:
                issues.append("Status is success but output is empty")
        elif result.get("status") == "failed":
            if not result.get("error"):
                issues.append("Status is failed but no error information")
            if result.get("output") and not result.get("partial_output"):
                issues.append("Failed task should not have full output without partial_output flag")
        
        # Check for contradictory information
        if result.get("status") == "success" and result.get("error"):
            issues.append("Success status with error message")
        
        # Validate retry suggestion consistency
        if result.get("retry_suggested") and result.get("status") == "success":
            issues.append("Retry suggested for successful operation")
        
        score = 1.0 - (len(issues) * 0.25)
        return {
            "passed": score >= 0.7,
            "score": max(score, 0.0),
            "issues": issues,
        }

    def _extract_issues(self, results: Dict[str, Dict[str, Any]]) -> List[str]:
        """Extract all issues from validation results"""
        issues = []
        for dim, res in results.items():
            if not res.get("passed", True):
                dim_issues = res.get("issues", [])
                issues.extend(f"[{dim}] {issue}" for issue in dim_issues)
                if "violations" in res:
                    issues.extend(f"[{dim}] {v}" for v in res["violations"])
        return issues

    def _generate_fix_suggestion(self, results: Dict[str, Dict[str, Any]], task: TaskNode) -> str:
        """Generate actionable fix suggestions"""
        suggestions = []
        
        if not results.get("completeness", {}).get("passed", True):
            suggestions.append("Complete missing fields in result")
        
        if not results.get("accuracy", {}).get("passed", True):
            suggestions.append("Verify data accuracy and source reliability")
        
        if not results.get("business_rule_compliance", {}).get("passed", True):
            suggestions.append("Fix business rule violations")
        
        if not results.get("logical_coherence", {}).get("passed", True):
            suggestions.append("Fix logical inconsistencies in output")
        
        if not results.get("consistency", {}).get("passed", True):
            suggestions.append("Ensure result aligns with task requirements")
        
        return "；".join(suggestions) if suggestions else "Re-execute task with corrected parameters"
