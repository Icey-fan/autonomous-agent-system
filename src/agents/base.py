"""
Autonomous Agent System - Core Base Classes (Fixed)
Fixes: circular imports, type safety, thread safety, global logging pollution
"""

from __future__ import annotations

import uuid
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Any, Optional
import threading
import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    """Task status enum with strict state machine"""
    PENDING = auto()
    ANALYZING = auto()
    DECOMPOSING = auto()
    EXECUTING = auto()
    VALIDATING = auto()
    COMPLETED = auto()
    FAILED = auto()
    RETRYING = auto()
    CANCELLED = auto()

    _valid_transitions = {
        PENDING: {ANALYZING, DECOMPOSING, EXECUTING, CANCELLED},
        ANALYZING: {DECOMPOSING, FAILED, CANCELLED},
        DECOMPOSING: {EXECUTING, FAILED, CANCELLED},
        EXECUTING: {VALIDATING, FAILED, RETRYING, CANCELLED},
        VALIDATING: {COMPLETED, FAILED, RETRYING},
        RETRYING: {EXECUTING, FAILED, CANCELLED},
        FAILED: set(),
        COMPLETED: set(),
        CANCELLED: set(),
    }

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in self._valid_transitions.get(self, set())


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    REASONER = "reasoner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    DECISION = "decision"


@dataclass
class TaskNode:
    """Thread-safe task tree node"""
    name: str
    description: str
    role: AgentRole = AgentRole.EXECUTOR
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    sub_tasks: List[TaskNode] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    validation_result: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def transition_status(self, new_status: TaskStatus) -> bool:
        with self._lock:
            if self.status.can_transition_to(new_status):
                old_status = self.status
                self.status = new_status
                if new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    self.completed_at = time.time()
                logger.debug(
                    "status_transition",
                    task_id=self.id,
                    task_name=self.name,
                    old=old_status.name,
                    new=new_status.name,
                )
                return True
            logger.warning(
                "invalid_status_transition",
                task_id=self.id,
                current=self.status.name,
                attempted=new_status.name,
            )
            return False

    def add_sub_task(self, task: TaskNode) -> None:
        with self._lock:
            task.parent_id = self.id
            self.sub_tasks.append(task)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "role": self.role.value,
                "status": self.status.name,
                "parent_id": self.parent_id,
                "dependencies": self.dependencies.copy(),
                "result": self.result,
                "validation": self.validation_result,
                "retry_count": self.retry_count,
                "sub_task_count": len(self.sub_tasks),
                "created_at": self.created_at,
                "completed_at": self.completed_at,
            }

    def get_all_sub_tasks(self) -> List[TaskNode]:
        with self._lock:
            result = []
            for sub in self.sub_tasks:
                result.append(sub)
                result.extend(sub.get_all_sub_tasks())
            return result

    def find_task_by_id(self, task_id: str) -> Optional[TaskNode]:
        if self.id == task_id:
            return self
        for sub in self.sub_tasks:
            found = sub.find_task_by_id(task_id)
            if found:
                return found
        return None


@dataclass
class AgentContext:
    """Thread-safe agent context"""
    original_task: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_plan: Optional[TaskNode] = None
    knowledge_base: Dict[str, Any] = field(default_factory=dict)
    external_data: Dict[str, Any] = field(default_factory=dict)
    business_rules: List[Dict[str, Any]] = field(default_factory=list)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    final_decision: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _data_lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def add_external_data(self, key: str, value: Any) -> None:
        with self._data_lock:
            self.external_data[key] = value

    def get_external_data(self, key: str, default: Any = None) -> Any:
        with self._data_lock:
            return self.external_data.get(key, default)

    def append_history(self, record: Dict[str, Any]) -> None:
        with self._lock:
            self.execution_history.append(record)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock, self._data_lock:
            return {
                "session_id": self.session_id,
                "original_task": self.original_task,
                "knowledge_base_keys": list(self.knowledge_base.keys()),
                "external_data_keys": list(self.external_data.keys()),
                "business_rules_count": len(self.business_rules),
                "execution_history_count": len(self.execution_history),
                "metadata": self.metadata.copy(),
            }


class BaseAgent(ABC):
    """Agent base class with abstract interface"""

    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.capabilities: List[str] = []
        self.performance_metrics = {"calls": 0, "success": 0, "avg_time": 0.0, "errors": 0}
        self._metrics_lock = threading.Lock()
        self.logger = structlog.get_logger(f"agent.{role.value}")

    @abstractmethod
    async def execute(self, task: TaskNode, context: AgentContext) -> Any:
        """Execute task - async method"""
        pass

    def log_execution(self, task_id: str, result: Any, duration: float, success: bool) -> None:
        with self._metrics_lock:
            self.performance_metrics["calls"] += 1
            if success:
                self.performance_metrics["success"] += 1
            else:
                self.performance_metrics["errors"] += 1
            total = self.performance_metrics["avg_time"] * (self.performance_metrics["calls"] - 1) + duration
            self.performance_metrics["avg_time"] = total / self.performance_metrics["calls"]
        
        self.logger.info(
            "task_executed",
            task_id=task_id,
            agent=self.name,
            duration=duration,
            success=success,
        )

    def get_metrics(self) -> Dict[str, Any]:
        with self._metrics_lock:
            return self.performance_metrics.copy()
