"""
Tests for orchestrator module
"""

import pytest
import asyncio
from agents.orchestrator import AgentOrchestrator, DependencyCycleError
from agents.base import TaskNode, AgentRole, TaskStatus


class TestAgentOrchestrator:
    @pytest.fixture
    async def orchestrator(self):
        orch = AgentOrchestrator(max_workers=2)
        yield orch
        await orch.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_simple_task(self):
        orch = AgentOrchestrator(max_workers=2)
        result = await orch.process_task(
            "Analyze user data and generate report",
            metadata={"test": True},
        )
        
        assert "session_id" in result
        assert result["status"] in ["success", "partial_failure"]
        assert "execution_summary" in result
        await orch.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_with_business_rules(self):
        orch = AgentOrchestrator(max_workers=2)
        rules = [
            {"name": "Test Rule", "type": "soft", "keywords": ["test"], "threshold": 100},
        ]
        result = await orch.process_task(
            "Test task with rules",
            business_rules=rules,
        )
        
        assert result["status"] in ["success", "partial_failure", "error"]
        await orch.shutdown()
    
    def test_detect_cycles(self):
        orch = AgentOrchestrator(max_workers=2)
        
        # Create cyclic dependencies: A -> B -> C -> A
        a = TaskNode(name="A", description="Task A")
        b = TaskNode(name="B", description="Task B")
        c = TaskNode(name="C", description="Task C")
        
        b.dependencies = [a.id]
        c.dependencies = [b.id]
        a.dependencies = [c.id]  # Cycle!
        
        with pytest.raises(DependencyCycleError):
            orch._detect_cycles([a, b, c])
    
    def test_detect_no_cycles(self):
        orch = AgentOrchestrator(max_workers=2)
        
        a = TaskNode(name="A", description="Task A")
        b = TaskNode(name="B", description="Task B", dependencies=[a.id])
        c = TaskNode(name="C", description="Task C", dependencies=[b.id])
        
        # Should not raise
        orch._detect_cycles([a, b, c])
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        orch = AgentOrchestrator(max_workers=2)
        await orch.process_task("Simple test task")
        
        metrics = orch._collect_metrics()
        assert "planner" in metrics
        assert "executor" in metrics
        assert all("calls" in m for m in metrics.values())
        await orch.shutdown()
