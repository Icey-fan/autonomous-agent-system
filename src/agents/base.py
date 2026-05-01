"""
Autonomous Agent System - Core Base Classes
"""

import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = auto()
    ANALYZING = auto()
    DECOMPOSING = auto()
    EXECUTING = auto()
    VALIDATING = auto()
    COMPLETED = auto()
    FAILED = auto()
    RETRYING = auto()


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    REASONER = "reasoner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    DECISION = "decision"


@dataclass
class TaskNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    sub_tasks: List['TaskNode'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    validation_result: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "role": self.role.value,
            "status": self.status.name,
            "parent_id": self.parent_id,
            "dependencies": self.dependencies,
            "result": self.result,
            "validation": self.validation_result,
            "retry_count": self.retry_count,
            "sub_task_count": len(self.sub_tasks)
        }


@dataclass
class AgentContext:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_task: str = ""
    current_plan: Optional[TaskNode] = None
    knowledge_base: Dict[str, Any] = field(default_factory=dict)
    external_data: Dict[str, Any] = field(default_factory=dict)
    business_rules: List[Dict] = field(default_factory=list)
    execution_history: List[Dict] = field(default_factory=list)
    final_decision: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.capabilities: List[str] = []
        self.performance_metrics = {"calls": 0, "success": 0, "avg_time": 0.0}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def execute(self, task: TaskNode, context: AgentContext) -> Any:
        pass

    def log_execution(self, task_id: str, result: Any, duration: float, success: bool):
        self.performance_metrics["calls"] += 1
        if success:
            self.performance_metrics["success"] += 1
        total = self.performance_metrics["avg_time"] * (self.performance_metrics["calls"] - 1) + duration
        self.performance_metrics["avg_time"] = total / self.performance_metrics["calls"]
        self.logger.info(f"Task {task_id} executed in {duration:.2f}s, success={success}")"""
Autonomous Agent System - Core Base Classes
"""

import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = auto()
    ANALYZING = auto()
    DECOMPOSING = auto()
    EXECUTING = auto()
    VALIDATING = auto()
    COMPLETED = auto()
    FAILED = auto()
    RETRYING = auto()


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    REASONER = "reasoner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    DECISION = "decision"


@dataclass
class TaskNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    sub_tasks: List['TaskNode'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    validation_result: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "role": self.role.value,
            "status": self.status.name,
            "parent_id": self.parent_id,
            "dependencies": self.dependencies,
            "result": self.result,
            "validation": self.validation_result,
            "retry_count": self.retry_count,
            "sub_task_count": len(self.sub_tasks)
        }


@dataclass
class AgentContext:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_task: str = ""
    current_plan: Optional[TaskNode] = None
    knowledge_base: Dict[str, Any] = field(default_factory=dict)
    external_data: Dict[str, Any] = field(default_factory=dict)
    business_rules: List[Dict] = field(default_factory=list)
    execution_history: List[Dict] = field(default_factory=list)
    final_decision: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.capabilities: List[str] = []
        self.performance_metrics = {"calls": 0, "success": 0, "avg_time": 0.0}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def execute(self, task: TaskNode, context: AgentContext) -> Any:
        pass

    def log_execution(self, task_id: str, result: Any, duration: float, success: bool):
        self.performance_metrics["calls"] += 1
        if success:
            self.performance_metrics["success"] += 1
        total = self.performance_metrics["avg_time"] * (self.performance_metrics["calls"] - 1) + duration
        self.performance_metrics["avg_time"] = total / self.performance_metrics["calls"]
        self.logger.info(f"Task {task_id} executed in {duration:.2f}s, success={success}")
