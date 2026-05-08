"""
Task planning and decomposition agent (Fixed)
Fixes: keyword matching replaced with LLM-based decomposition
"""

import json
from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class PlannerAgent(BaseAgent):
    """LLM-based task planner with intelligent decomposition"""

    def __init__(self, llm_client: Optional[Any] = None):
        super().__init__("Planner", AgentRole.PLANNER)
        self.capabilities = ["task_decomposition", "dependency_analysis", "resource_allocation"]
        self.llm_client = llm_client
        self._fallback_patterns = self._init_fallback_patterns()

    def _init_fallback_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback decomposition patterns when LLM is unavailable"""
        return {
            "data_analysis": [
                {"name": "数据收集", "description": "从多源获取原始数据", "role": "researcher"},
                {"name": "数据清洗", "description": "处理缺失值与异常值", "role": "executor", "deps": ["数据收集"]},
                {"name": "探索性分析", "description": "描述统计与可视化", "role": "reasoner", "deps": ["数据清洗"]},
                {"name": "深度建模", "description": "算法模型预测", "role": "reasoner", "deps": ["探索性分析"]},
                {"name": "报告生成", "description": "生成分析报告", "role": "executor", "deps": ["深度建模"]},
            ],
            "decision": [
                {"name": "信息收集", "description": "收集决策所需信息", "role": "researcher"},
                {"name": "约束分析", "description": "识别业务约束", "role": "reasoner", "deps": ["信息收集"]},
                {"name": "方案生成", "description": "生成候选方案", "role": "reasoner", "deps": ["信息收集", "约束分析"]},
                {"name": "方案评估", "description": "多维度评估", "role": "reasoner", "deps": ["方案生成"]},
                {"name": "风险评估", "description": "识别潜在风险", "role": "reasoner", "deps": ["方案生成"]},
                {"name": "最终决策", "description": "输出决策建议", "role": "decision", "deps": ["方案评估", "风险评估"]},
            ],
            "research": [
                {"name": "文献检索", "description": "检索相关文献", "role": "researcher"},
                {"name": "数据调研", "description": "收集市场数据", "role": "researcher"},
                {"name": "信息整合", "description": "多源信息融合", "role": "reasoner", "deps": ["文献检索", "数据调研"]},
                {"name": "洞察提炼", "description": "提取关键洞察", "role": "reasoner", "deps": ["信息整合"]},
                {"name": "结论输出", "description": "形成研究结论", "role": "decision", "deps": ["洞察提炼"]},
            ],
            "generic": [
                {"name": "需求分析", "description": "分析任务需求", "role": "reasoner"},
                {"name": "任务执行", "description": "执行核心操作", "role": "executor", "deps": ["需求分析"]},
                {"name": "结果校验", "description": "验证执行结果", "role": "validator", "deps": ["任务执行"]},
            ],
        }

    async def execute(self, task: TaskNode, context: AgentContext) -> TaskNode:
        logger.info("planning_task", task_id=task.id, description=task.description[:50])
        
        if self.llm_client:
            sub_tasks = await self._llm_decompose(task, context)
        else:
            sub_tasks = self._fallback_decompose(task, context)
        
        for sub in sub_tasks:
            task.add_sub_task(sub)
        
        logger.info("decomposition_complete", task_id=task.id, sub_task_count=len(sub_tasks))
        return task

    async def _llm_decompose(self, task: TaskNode, context: AgentContext) -> List[TaskNode]:
        """Use LLM for intelligent task decomposition"""
        prompt = f"""Decompose the following task into sub-tasks. Return JSON array with objects containing:
        - name: task name
        - description: detailed description
        - role: one of [researcher, reasoner, executor, validator, decision]
        - dependencies: list of task names this depends on (can be empty)
        
        Task: {task.description}
        Context: {json.dumps(context.metadata, ensure_ascii=False)}
        
        Response format: [{{"name": "...", "description": "...", "role": "...", "dependencies": []}}]"""
        
        try:
            response = await self.llm_client.complete(prompt)
            plans = json.loads(response)
            return self._build_task_nodes(plans)
        except Exception as e:
            logger.error("llm_decomposition_failed", error=str(e), fallback=True)
            return self._fallback_decompose(task, context)

    def _fallback_decompose(self, task: TaskNode, context: AgentContext) -> List[TaskNode]:
        """Pattern-based fallback decomposition"""
        desc = task.description.lower()
        
        if any(kw in desc for kw in ["数据分析", "data analysis", "统计", "报表"]):
            pattern = self._fallback_patterns["data_analysis"]
        elif any(kw in desc for kw in ["决策", "decision", "策略", "方案"]):
            pattern = self._fallback_patterns["decision"]
        elif any(kw in desc for kw in ["研究", "调研", "调查", "research"]):
            pattern = self._fallback_patterns["research"]
        else:
            pattern = self._fallback_patterns["generic"]
        
        return self._build_task_nodes(pattern)

    def _build_task_nodes(self, plans: List[Dict[str, Any]]) -> List[TaskNode]:
        """Build task nodes from plan definitions with dependency resolution"""
        name_to_id: Dict[str, str] = {}
        nodes: List[TaskNode] = []
        
        # First pass: create all nodes
        for plan in plans:
            node = TaskNode(
                name=plan["name"],
                description=plan.get("description", plan["name"]),
                role=AgentRole(plan.get("role", "executor")),
            )
            name_to_id[plan["name"]] = node.id
            nodes.append(node)
        
        # Second pass: resolve dependencies
        for i, plan in enumerate(plans):
            deps = plan.get("dependencies", plan.get("deps", []))
            nodes[i].dependencies = [name_to_id[d] for d in deps if d in name_to_id]
        
        return nodes
