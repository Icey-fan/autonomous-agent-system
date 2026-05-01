"""智能体编排器"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, TaskStatus, logger
from .planner import PlannerAgent
from .researcher import ResearcherAgent
from .reasoner import ReasonerAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .decision import DecisionAgent


class AgentOrchestrator:
    def __init__(self, max_workers: int = 5):
        self.agents: Dict[AgentRole, BaseAgent] = {
            AgentRole.PLANNER: PlannerAgent(),
            AgentRole.RESEARCHER: ResearcherAgent(),
            AgentRole.REASONER: ReasonerAgent(),
            AgentRole.EXECUTOR: ExecutorAgent(),
            AgentRole.VALIDATOR: ValidatorAgent(),
            AgentRole.DECISION: DecisionAgent()
        }
        self.executor_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.active_sessions: Dict[str, AgentContext] = {}
        self.max_workers = max_workers

    def process_task(self, task_description: str, business_rules: Optional[List[Dict]] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        context = AgentContext(original_task=task_description, business_rules=business_rules or [], metadata=metadata or {})
        context.metadata["start_time"] = time.time()
        self.active_sessions[context.session_id] = context
        logger.info(f"\n{'='*60}\n[Orchestrator] 开始处理: {task_description[:50]}...\n{'='*60}")

        try:
            root_task = TaskNode(name="根任务", description=task_description, role=AgentRole.PLANNER)
            context.current_plan = root_task
            root_task = self.agents[AgentRole.PLANNER].execute(root_task, context)
            root_task.status = TaskStatus.DECOMPOSING

            self._execute_task_tree(root_task, context)

            if root_task.status == TaskStatus.COMPLETED or all(t.status == TaskStatus.COMPLETED for t in root_task.sub_tasks):
                final_decision = self.agents[AgentRole.DECISION].execute(root_task, context)
                return {
                    "session_id": context.session_id,
                    "status": "success",
                    "task_tree": self._serialize_tree(root_task),
                    "final_decision": final_decision,
                    "execution_summary": self._generate_summary(context),
                    "performance_metrics": self._collect_metrics()
                }
            else:
                failed_tasks = [t for t in self._flatten_tree(root_task) if t.status == TaskStatus.FAILED]
                return {
                    "session_id": context.session_id,
                    "status": "partial_failure",
                    "error": f"{len(failed_tasks)} 个子任务失败",
                    "failed_tasks": [{"id": t.id, "name": t.name} for t in failed_tasks],
                    "task_tree": self._serialize_tree(root_task)
                }
        except Exception as e:
            logger.error(f"[Orchestrator] 异常: {e}", exc_info=True)
            return {"session_id": context.session_id, "status": "error", "error": str(e)}

    def _execute_task_tree(self, task: TaskNode, context: AgentContext):
        if not task.sub_tasks:
            self._execute_single_task(task, context)
            return

        executed = set()
        remaining = {t.id: t for t in task.sub_tasks}
        failed_tasks = set()

        while remaining:
            ready = [t for t in remaining.values() if all(dep in executed for dep in t.dependencies) and t.id not in failed_tasks]
            if not ready:
                pending = [t for t in remaining.values() if t.id not in failed_tasks]
                if not pending:
                    break
                raise ValueError(f"无法解析的依赖: {[t.id for t in pending]}")

            futures = {}
            for t in ready:
                futures[self.executor_pool.submit(self._execute_single_task, t, context)] = t

            for future in as_completed(futures):
                sub_task = futures[future]
                try:
                    future.result()
                    if sub_task.status == TaskStatus.COMPLETED:
                        executed.add(sub_task.id)
                        remaining.pop(sub_task.id, None)
                    elif sub_task.status == TaskStatus.FAILED:
                        failed_tasks.add(sub_task.id)
                        self._cascade_failure(sub_task, remaining)
                except Exception as e:
                    logger.error(f"[Orchestrator] 异常: {e}")
                    sub_task.status = TaskStatus.FAILED
                    failed_tasks.add(sub_task.id)

        task.status = TaskStatus.FAILED if (failed_tasks and len(failed_tasks) == len(task.sub_tasks)) else TaskStatus.COMPLETED
        task.completed_at = time.time()

    def _execute_single_task(self, task: TaskNode, context: AgentContext):
        agent = self.agents.get(task.role)
        if not agent:
            raise ValueError(f"未找到角色 {task.role} 对应的智能体")

        task.status = TaskStatus.EXECUTING
        start_time = time.time()

        try:
            result = agent.execute(task, context)
            task.result = result
            duration = time.time() - start_time

            validation = self.agents[AgentRole.VALIDATOR].execute(task, context)
            task.validation_result = validation

            if validation["passed"]:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                agent.log_execution(task.id, result, duration, True)
                context.execution_history.append({"task_id": task.id, "task_name": task.name, "status": "success", "duration": duration, "timestamp": time.time()})
            else:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    logger.warning(f"[Orchestrator] 重试 {task.name} ({task.retry_count}/{task.max_retries})")
                    time.sleep(2 ** task.retry_count)
                    self._execute_single_task(task, context)
                else:
                    task.status = TaskStatus.FAILED
                    agent.log_execution(task.id, result, duration, False)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e)}
            logger.error(f"[Orchestrator] 失败: {e}")

    def _cascade_failure(self, failed_task: TaskNode, remaining: Dict[str, TaskNode]):
        for task in list(remaining.values()):
            if failed_task.id in task.dependencies:
                task.status = TaskStatus.FAILED
                task.result = {"error": f"依赖任务 {failed_task.name} 失败"}

    def _flatten_tree(self, root: TaskNode) -> List[TaskNode]:
        result = [root]
        for sub in root.sub_tasks:
            result.extend(self._flatten_tree(sub))
        return result

    def _serialize_tree(self, task: TaskNode) -> Dict:
        result = task.to_dict()
        if task.sub_tasks:
            result["sub_tasks"] = [self._serialize_tree(t) for t in task.sub_tasks]
        return result

    def _generate_summary(self, context: AgentContext) -> Dict:
        duration = time.time() - context.metadata.get("start_time", time.time())
        return {
            "total_tasks": len(context.execution_history),
            "successful": sum(1 for h in context.execution_history if h["status"] == "success"),
            "failed": sum(1 for h in context.execution_history if h["status"] == "failed"),
            "data_sources": list(context.external_data.keys()),
            "duration_seconds": round(duration, 2)
        }

    def _collect_metrics(self) -> Dict:
        return {role.value: agent.performance_metrics for role, agent in self.agents.items()}

    def shutdown(self):
        self.executor_pool.shutdown(wait=True)
        logger.info("[Orchestrator] 已关闭")
