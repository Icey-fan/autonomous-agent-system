"""工具执行与操作智能体"""

import time
import uuid
from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Executor", AgentRole.EXECUTOR)
        self.capabilities = ["tool_call", "api_invocation", "code_execution"]
        self.available_tools = {
            "calculate": self._tool_calculate,
            "query_db": self._tool_query,
            "send_notification": self._tool_notify,
            "generate_report": self._tool_report,
            "data_transform": self._tool_transform,
            "api_call": self._tool_api
        }

    def execute(self, task: TaskNode, context: AgentContext) -> dict:
        logger.info(f"[Executor] 执行: {task.description}")
        tool_name = self._select_tool(task, context)
        tool_func = self.available_tools.get(tool_name, self._default_tool)
        start_time = time.time()
        try:
            params = self._build_params(tool_name, task, context)
            result = tool_func(**params)
            duration = time.time() - start_time
            logger.info(f"[Executor] 成功，工具: {tool_name}, 耗时: {duration:.2f}s")
            return {"status": "success", "tool": tool_name, "output": result, "execution_time": duration, "params": params}
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[Executor] 失败: {e}")
            return {"status": "failed", "tool": tool_name, "error": str(e), "execution_time": duration, "retry_suggested": True}

    def _select_tool(self, task: TaskNode, context: AgentContext) -> str:
        desc = task.description.lower()
        mapping = {"计算": "calculate", "统计": "calculate", "查询": "query_db", "数据库": "query_db", "通知": "send_notification", "报告": "generate_report", "转换": "data_transform", "接口": "api_call", "api": "api_call"}
        for keyword, tool in mapping.items():
            if keyword in desc:
                return tool
        return "generate_report"

    def _build_params(self, tool_name: str, task: TaskNode, context: AgentContext) -> dict:
        base = {"task_description": task.description, "context": context.external_data}
        if tool_name == "calculate":
            return {**base, "expression": task.context.get("expression", "1+1")}
        elif tool_name == "query_db":
            return {**base, "query": task.context.get("query", "SELECT * FROM data"), "source": "primary_db"}
        elif tool_name == "send_notification":
            return {**base, "channel": task.context.get("channel", "email"), "message": task.description}
        elif tool_name == "generate_report":
            return {**base, "template": task.context.get("template", "standard"), "data": context.external_data}
        elif tool_name == "data_transform":
            return {**base, "input_data": task.context.get("input", {}), "transform_type": "standardize"}
        elif tool_name == "api_call":
            return {**base, "endpoint": task.context.get("endpoint", "/api/v1/data"), "method": "GET", "payload": {}}
        return base

    def _tool_calculate(self, **kwargs):
        return {"result": 42, "operation": "complex_calculation"}

    def _tool_query(self, **kwargs):
        return {"records": 150, "fields": ["id", "name", "value"]}

    def _tool_notify(self, **kwargs):
        return {"sent": True, "channel": kwargs.get("channel", "email")}

    def _tool_report(self, **kwargs):
        return {"report_id": f"RPT-{uuid.uuid4().hex[:8].upper()}", "pages": 5, "format": "PDF"}

    def _tool_transform(self, **kwargs):
        return {"transformed_records": 1000, "operations": ["normalize"]}

    def _tool_api(self, **kwargs):
        return {"status_code": 200, "response_size": 2048, "latency_ms": 150}

    def _default_tool(self, **kwargs):
        return {"message": "default_execution"}
