"""
Agent orchestrator (Fixed)
Fixes: ThreadPoolExecutor replaced with asyncio, added dependency cycle detection,
       proper retry with state reset, graceful error handling
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Set
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, TaskStatus, logger
from .planner import PlannerAgent
from .researcher import ResearcherAgent
from .reasoner import ReasonerAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .decision import DecisionAgent


class DependencyCycleError(Exception):
    """Raised when circular dependencies are detected"""
    pass


class AgentOrchestrator:
    """Async agent orchestrator with proper concurrency and error handling"""

    def __init__(
        self,
        max_workers: int = 5,
        llm_client: Optional[Any] = None,
        api_keys: Optional[Dict[str, str]] = None,
    ):
        self.agents: Dict[AgentRole, BaseAgent] = {
            AgentRole.PLANNER: PlannerAgent(llm_client=llm_client),
            AgentRole.RESEARCHER: ResearcherAgent(api_keys=api_keys),
            AgentRole.REASONER: ReasonerAgent(llm_client=llm_client),
            AgentRole.EXECUTOR: ExecutorAgent(),
            AgentRole.VALIDATOR: ValidatorAgent(),
            AgentRole.DECISION: DecisionAgent(),
        }
        self.max_workers = max_workers
        self.active_sessions: Dict[str, AgentContext] = {}
        self._semaphore = asyncio.Semaphore(max_workers)

    async def process_task(
        self,
        task_description: str,
        business_rules: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a task through the full agent pipeline"""
        context = AgentContext(
            original_task=task_description,
            business_rules=business_rules or [],
            metadata=metadata or {},
        )
        context.metadata["start_time"] = time.time()
        self.active_sessions[context.session_id] = context
        
        logger.info(
            "orchestrator_start",
            session_id=context.session_id,
            task=task_description[:50],
        )

        try:
            # Phase 1: Planning
            root_task = TaskNode(name="Root Task", description=task_description, role=AgentRole.PLANNER)
            context.current_plan = root_task
            root_task = await self.agents[AgentRole.PLANNER].execute(root_task, context)
            root_task.transition_status(TaskStatus.DECOMPOSING)

            # Phase 2: Execute task tree
            await self._execute_task_tree(root_task, context)

            # Phase 3: Decision synthesis
            if self._is_task_tree_successful(root_task):
                final_decision = await self.agents[AgentRole.DECISION].execute(root_task, context)
                return {
                    "session_id": context.session_id,
                    "status": "success",
                    "task_tree": self._serialize_tree(root_task),
                    "final_decision": final_decision,
                    "execution_summary": self._generate_summary(context),
                    "performance_metrics": self._collect_metrics(),
                }
            else:
                failed_tasks = self._get_failed_tasks(root_task)
                return {
                    "session_id": context.session_id,
                    "status": "partial_failure",
                    "error": f"{len(failed_tasks)} sub-tasks failed",
                    "failed_tasks": [{"id": t.id, "name": t.name, "error": str(t.result)} for t in failed_tasks],
                    "task_tree": self._serialize_tree(root_task),
                    "execution_summary": self._generate_summary(context),
                }

        except Exception as e:
            logger.error("orchestrator_error", session_id=context.session_id, error=str(e), exc_info=True)
            return {
                "session_id": context.session_id,
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_summary": self._generate_summary(context),
            }

    async def _execute_task_tree(self, task: TaskNode, context: AgentContext) -> None:
        """Execute task tree with dependency resolution"""
        if not task.sub_tasks:
            await self._execute_single_task(task, context)
            return

        # Detect circular dependencies
        self._detect_cycles(task.sub_tasks)

        executed: Set[str] = set()
        remaining: Dict[str, TaskNode] = {t.id: t for t in task.sub_tasks}
        failed_tasks: Set[str] = set()

        while remaining:
            # Find ready tasks (all dependencies satisfied)
            ready = [
                t for t in remaining.values()
                if all(dep in executed for dep in t.dependencies)
                and t.id not in failed_tasks
            ]

            if not ready:
                pending = [t for t in remaining.values() if t.id not in failed_tasks]
                if not pending:
                    break
                
                # Check for impossible dependencies (depend on failed tasks)
                impossible = [
                    t for t in pending
                    if any(dep in failed_tasks for dep in t.dependencies)
                ]
                for t in impossible:
                    t.transition_status(TaskStatus.FAILED)
                    t.result = {"error": f"Dependency task failed"}
                    failed_tasks.add(t.id)
                    remaining.pop(t.id, None)
                    self._cascade_failure(t, remaining)
                
                if not remaining:
                    break
                
                # If still pending but no ready tasks, there's a real problem
                still_pending = [t for t in remaining.values() if t.id not in failed_tasks]
                if still_pending and not ready:
                    raise DependencyCycleError(
                        f"Unresolved dependencies for tasks: {[t.id for t in still_pending]}"
                    )

            # Execute ready tasks concurrently with semaphore
            async with self._semaphore:
                tasks = [self._execute_single_task(t, context) for t in ready]
                await asyncio.gather(*tasks, return_exceptions=True)

            # Update executed/failed sets
            for t in ready:
                if t.status == TaskStatus.COMPLETED:
                    executed.add(t.id)
                    remaining.pop(t.id, None)
                elif t.status == TaskStatus.FAILED:
                    failed_tasks.add(t.id)
                    remaining.pop(t.id, None)
                    self._cascade_failure(t, remaining)

        # Set root task status
        if failed_tasks and len(failed_tasks) == len(task.sub_tasks):
            task.transition_status(TaskStatus.FAILED)
        elif failed_tasks:
            task.transition_status(TaskStatus.COMPLETED)  # Partial success
        else:
            task.transition_status(TaskStatus.COMPLETED)

    def _detect_cycles(self, tasks: List[TaskNode]) -> None:
        """Detect circular dependencies using DFS"""
        graph: Dict[str, Set[str]] = {t.id: set(t.dependencies) for t in tasks}
        
        # Add all task IDs to graph
        for t in tasks:
            if t.id not in graph:
                graph[t.id] = set()
        
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    raise DependencyCycleError(f"Circular dependency detected involving task {node}")

    async def _execute_single_task(self, task: TaskNode, context: AgentContext) -> None:
        """Execute a single task with validation and retry"""
        agent = self.agents.get(task.role)
        if not agent:
            task.transition_status(TaskStatus.FAILED)
            task.result = {"error": f"No agent found for role {task.role.value}"}
            return

        task.transition_status(TaskStatus.EXECUTING)
        start_time = time.time()

        try:
            result = await agent.execute(task, context)
            task.result = result
            duration = time.time() - start_time

            # Validation
            validation = await self.agents[AgentRole.VALIDATOR].execute(task, context)
            task.validation_result = validation

            if validation["passed"]:
                task.transition_status(TaskStatus.COMPLETED)
                agent.log_execution(task.id, result, duration, True)
                context.append_history({
                    "task_id": task.id,
                    "task_name": task.name,
                    "status": "success",
                    "duration": duration,
                    "timestamp": time.time(),
                })
            else:
                await self._handle_retry(task, context, agent, result, duration)

        except Exception as e:
            duration = time.time() - start_time
            task.result = {"error": str(e), "error_type": type(e).__name__}
            logger.error("task_execution_failed", task_id=task.id, error=str(e))
            await self._handle_retry(task, context, agent, task.result, duration)

    async def _handle_retry(
        self,
        task: TaskNode,
        context: AgentContext,
        agent: BaseAgent,
        result: Any,
        duration: float,
    ) -> None:
        """Handle task retry with exponential backoff and max wait"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.transition_status(TaskStatus.RETRYING)
            
            # Exponential backoff with max 60 seconds
            wait_time = min(2 ** task.retry_count, 60)
            logger.warning(
                "task_retry",
                task_id=task.id,
                task_name=task.name,
                attempt=f"{task.retry_count}/{task.max_retries}",
                wait_seconds=wait_time,
            )
            
            await asyncio.sleep(wait_time)
            
            # Reset task state for retry
            task.result = None
            task.validation_result = None
            task.transition_status(TaskStatus.PENDING)
            
            # Recursive retry
            await self._execute_single_task(task, context)
        else:
            task.transition_status(TaskStatus.FAILED)
            agent.log_execution(task.id, result, duration, False)
            context.append_history({
                "task_id": task.id,
                "task_name": task.name,
                "status": "failed",
                "duration": duration,
                "timestamp": time.time(),
                "error": str(result) if isinstance(result, dict) else "Unknown error",
            })

    def _cascade_failure(self, failed_task: TaskNode, remaining: Dict[str, TaskNode]) -> None:
        """Cascade failure to dependent tasks"""
        for task in list(remaining.values()):
            if failed_task.id in task.dependencies:
                task.transition_status(TaskStatus.FAILED)
                task.result = {"error": f"Dependency task '{failed_task.name}' failed"}

    def _is_task_tree_successful(self, root: TaskNode) -> bool:
        """Check if task tree has any successful completion"""
        if root.status == TaskStatus.COMPLETED:
            return True
        return any(t.status == TaskStatus.COMPLETED for t in root.get_all_sub_tasks())

    def _get_failed_tasks(self, root: TaskNode) -> List[TaskNode]:
        """Get all failed tasks in tree"""
        return [t for t in root.get_all_sub_tasks() if t.status == TaskStatus.FAILED]

    def _serialize_tree(self, task: TaskNode) -> Dict[str, Any]:
        """Serialize task tree to dict"""
        result = task.to_dict()
        if task.sub_tasks:
            result["sub_tasks"] = [self._serialize_tree(t) for t in task.sub_tasks]
        return result

    def _generate_summary(self, context: AgentContext) -> Dict[str, Any]:
        """Generate execution summary"""
        duration = time.time() - context.metadata.get("start_time", time.time())
        history = context.execution_history
        
        return {
            "total_tasks": len(history),
            "successful": sum(1 for h in history if h.get("status") == "success"),
            "failed": sum(1 for h in history if h.get("status") == "failed"),
            "retried": sum(1 for h in history if "retry" in str(h.get("task_name", "")).lower()),
            "data_sources": list(context.external_data.keys()),
            "duration_seconds": round(duration, 2),
            "session_id": context.session_id,
        }

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from all agents"""
        return {role.value: agent.get_metrics() for role, agent in self.agents.items()}

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("orchestrator_shutdown")
        # Cancel any pending tasks if needed
