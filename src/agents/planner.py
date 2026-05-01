"""任务规划与拆解智能体"""

from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Planner", AgentRole.PLANNER)
        self.capabilities = ["task_decomposition", "dependency_analysis", "resource_allocation"]

    def execute(self, task: TaskNode, context: AgentContext) -> TaskNode:
        logger.info(f"[Planner] 拆解任务: {task.description}")
        sub_tasks = self._analyze_and_decompose(task, context)
        for sub in sub_tasks:
            sub.parent_id = task.id
        task.sub_tasks = sub_tasks
        logger.info(f"[Planner] 生成 {len(sub_tasks)} 个子任务")
        return task

    def _analyze_and_decompose(self, task: TaskNode, context: AgentContext) -> list:
        desc = task.description.lower()
        if any(kw in desc for kw in ["数据分析", "data analysis", "统计", "报表"]):
            return self._decompose_data_analysis(task)
        elif any(kw in desc for kw in ["决策", "decision", "策略", "方案"]):
            return self._decompose_decision(task)
        elif any(kw in desc for kw in ["研究", "调研", "调查", "research"]):
            return self._decompose_research(task)
        else:
            return self._decompose_generic(task)

    def _decompose_data_analysis(self, task: TaskNode) -> list:
        tasks = [
            TaskNode(name="数据收集", description="从多源获取原始数据", role=AgentRole.RESEARCHER),
            TaskNode(name="数据清洗", description="处理缺失值与异常值", role=AgentRole.EXECUTOR),
            TaskNode(name="探索性分析", description="描述统计与可视化", role=AgentRole.REASONER),
            TaskNode(name="深度建模", description="算法模型预测", role=AgentRole.REASONER),
            TaskNode(name="报告生成", description="生成分析报告", role=AgentRole.EXECUTOR)
        ]
        tasks[1].dependencies = [tasks[0].id]
        tasks[2].dependencies = [tasks[1].id]
        tasks[3].dependencies = [tasks[2].id]
        tasks[4].dependencies = [tasks[3].id]
        return tasks

    def _decompose_decision(self, task: TaskNode) -> list:
        tasks = [
            TaskNode(name="信息收集", description="收集决策所需信息", role=AgentRole.RESEARCHER),
            TaskNode(name="约束分析", description="识别业务约束", role=AgentRole.REASONER),
            TaskNode(name="方案生成", description="生成候选方案", role=AgentRole.REASONER),
            TaskNode(name="方案评估", description="多维度评估", role=AgentRole.REASONER),
            TaskNode(name="风险评估", description="识别潜在风险", role=AgentRole.REASONER),
            TaskNode(name="最终决策", description="输出决策建议", role=AgentRole.DECISION)
        ]
        tasks[1].dependencies = [tasks[0].id]
        tasks[2].dependencies = [tasks[0].id, tasks[1].id]
        tasks[3].dependencies = [tasks[2].id]
        tasks[4].dependencies = [tasks[2].id]
        tasks[5].dependencies = [tasks[3].id, tasks[4].id]
        return tasks

    def _decompose_research(self, task: TaskNode) -> list:
        tasks = [
            TaskNode(name="文献检索", description="检索相关文献", role=AgentRole.RESEARCHER),
            TaskNode(name="数据调研", description="收集市场数据", role=AgentRole.RESEARCHER),
            TaskNode(name="信息整合", description="多源信息融合", role=AgentRole.REASONER),
            TaskNode(name="洞察提炼", description="提取关键洞察", role=AgentRole.REASONER),
            TaskNode(name="结论输出", description="形成研究结论", role=AgentRole.DECISION)
        ]
        tasks[2].dependencies = [tasks[0].id, tasks[1].id]
        tasks[3].dependencies = [tasks[2].id]
        tasks[4].dependencies = [tasks[3].id]
        return tasks

    def _decompose_generic(self, task: TaskNode) -> list:
        tasks = [
            TaskNode(name="需求分析", description="分析任务需求", role=AgentRole.REASONER),
            TaskNode(name="任务执行", description="执行核心操作", role=AgentRole.EXECUTOR),
            TaskNode(name="结果校验", description="验证执行结果", role=AgentRole.VALIDATOR)
        ]
        tasks[1].dependencies = [tasks[0].id]
        tasks[2].dependencies = [tasks[1].id]
        return tasks
