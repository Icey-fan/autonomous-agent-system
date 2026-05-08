"""
Tests for base module
"""

import pytest
import threading
import time
from agents.base import TaskStatus, TaskNode, AgentContext, AgentRole, BaseAgent


class TestTaskStatus:
    def test_valid_transitions(self):
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.EXECUTING)
        assert TaskStatus.EXECUTING.can_transition_to(TaskStatus.VALIDATING)
        assert TaskStatus.VALIDATING.can_transition_to(TaskStatus.COMPLETED)
    
    def test_invalid_transitions(self):
        assert not TaskStatus.COMPLETED.can_transition_to(TaskStatus.EXECUTING)
        assert not TaskStatus.FAILED.can_transition_to(TaskStatus.COMPLETED)
    
    def test_terminal_states(self):
        assert TaskStatus.COMPLETED._valid_transitions[TaskStatus.COMPLETED] == set()
        assert TaskStatus.FAILED._valid_transitions[TaskStatus.FAILED] == set()


class TestTaskNode:
    def test_creation(self):
        task = TaskNode(name="Test", description="Test task")
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert len(task.id) == 8
    
    def test_status_transition(self):
        task = TaskNode(name="Test", description="Test task")
        assert task.transition_status(TaskStatus.EXECUTING)
        assert task.status == TaskStatus.EXECUTING
        assert not task.transition_status(TaskStatus.PENDING)  # Invalid reverse
    
    def test_add_sub_task(self):
        parent = TaskNode(name="Parent", description="Parent task")
        child = TaskNode(name="Child", description="Child task")
        parent.add_sub_task(child)
        assert child.parent_id == parent.id
        assert len(parent.sub_tasks) == 1
    
    def test_thread_safety(self):
        task = TaskNode(name="Concurrent", description="Concurrent access")
        results = []
        
        def transition():
            success = task.transition_status(TaskStatus.EXECUTING)
            results.append(success)
        
        threads = [threading.Thread(target=transition) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Only one should succeed (PENDING -> EXECUTING)
        assert sum(results) == 1
    
    def test_find_task_by_id(self):
        root = TaskNode(name="Root", description="Root")
        child = TaskNode(name="Child", description="Child")
        grandchild = TaskNode(name="Grandchild", description="Grandchild")
        root.add_sub_task(child)
        child.add_sub_task(grandchild)
        
        found = root.find_task_by_id(grandchild.id)
        assert found == grandchild


class TestAgentContext:
    def test_thread_safe_data_access(self):
        ctx = AgentContext(original_task="Test")
        ctx.add_external_data("key1", "value1")
        assert ctx.get_external_data("key1") == "value1"
        assert ctx.get_external_data("missing", "default") == "default"
    
    def test_concurrent_access(self):
        ctx = AgentContext(original_task="Concurrent")
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    ctx.add_external_data(f"key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(ctx.external_data) == 500
