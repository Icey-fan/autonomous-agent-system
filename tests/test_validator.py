"""
Tests for validator module
"""

import pytest
from agents.validator import ValidatorAgent, ValidationRule
from agents.base import TaskNode, AgentRole, AgentContext, TaskStatus


class TestValidatorAgent:
    @pytest.fixture
    def validator(self):
        return ValidatorAgent()
    
    @pytest.fixture
    def context(self):
        return AgentContext(
            original_task="Test",
            business_rules=[
                {"name": "Hard Rule", "type": "hard", "condition": "violation"},
                {"name": "Soft Rule", "type": "soft", "keywords": ["test"], "threshold": 100},
            ],
        )
    
    @pytest.mark.asyncio
    async def test_validate_successful_result(self, validator, context):
        task = TaskNode(name="Test", description="Test task")
        task.result = {
            "status": "success",
            "output": {"data": [1, 2, 3]},
            "execution_time": 1.5,
        }
        
        result = await validator.execute(task, context)
        assert isinstance(result, dict)
        assert "passed" in result
        assert "score" in result
    
    @pytest.mark.asyncio
    async def test_validate_empty_result(self, validator, context):
        task = TaskNode(name="Test", description="Test task")
        task.result = None
        
        result = await validator.execute(task, context)
        assert result["passed"] == False
        assert result["score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_validate_failed_status(self, validator, context):
        task = TaskNode(name="Test", description="Test task")
        task.result = {
            "status": "failed",
            "error": "Something went wrong",
        }
        
        result = await validator.execute(task, context)
        # Should fail accuracy check
        assert result["passed"] == False or result["dimension_results"]["accuracy"]["passed"] == False
    
    @pytest.mark.asyncio
    async def test_business_rule_violation(self, validator, context):
        task = TaskNode(name="Test", description="Test task")
        task.result = {
            "status": "success",
            "output": "This contains violation",
        }
        
        result = await validator.execute(task, context)
        # Should detect hard rule violation
        br_result = result["dimension_results"]["business_rule_compliance"]
        assert br_result["passed"] == False
    
    def test_custom_validation_rule(self):
        def custom_check(task, context):
            return {"passed": True, "score": 1.0, "note": "Custom"}
        
        rule = ValidationRule("custom", custom_check, weight=0.5)
        assert rule.name == "custom"
        assert rule.weight == 0.5
