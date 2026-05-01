"""多源信息整合智能体"""

from .base import BaseAgent, AgentRole, TaskNode, AgentContext, logger


class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__("Researcher", AgentRole.RESEARCHER)
        self.capabilities = ["web_search", "data_retrieval", "knowledge_fusion"]

    def execute(self, task: TaskNode, context: AgentContext) -> dict:
        logger.info(f"[Researcher] 收集信息: {task.description}")
        sources = self._determine_sources(task, context)
        collected = {"sources": [], "data": {}, "raw_results": [], "confidence": 0.0, "timestamp": time.time()}
        for source in sources:
            result = self._fetch_from_source(source, task, context)
            collected["sources"].append(source)
            collected["raw_results"].append(result)
            collected["data"].update(result.get("data", {}))
        collected["confidence"] = self._calculate_confidence(collected["raw_results"])
        context.external_data[task.name] = collected
        logger.info(f"[Researcher] 完成，来源: {len(sources)}, 置信度: {collected['confidence']:.2f}")
        return collected

    def _determine_sources(self, task: TaskNode, context: AgentContext) -> list:
        desc = task.description.lower()
        if any(kw in desc for kw in ["市场", "行业", "market"]):
            return ["external_api", "web_search", "document_store"]
        elif any(kw in desc for kw in ["用户", "客户", "user"]):
            return ["internal_db", "external_api", "knowledge_graph"]
        return ["internal_db", "knowledge_graph"]

    def _fetch_from_source(self, source: str, task: TaskNode, context: AgentContext) -> dict:
        mock_data = {
            "external_api": {"source": "external_api", "data": {"market_size": "100B", "growth_rate": "15%"}, "reliability": 0.9},
            "web_search": {"source": "web_search", "data": {"trends": ["AI", "Cloud"], "news_count": 150}, "reliability": 0.7},
            "internal_db": {"source": "internal_db", "data": {"active_users": 50000, "revenue": "10M"}, "reliability": 0.95},
            "document_store": {"source": "document_store", "data": {"reports": 5}, "reliability": 0.85},
            "knowledge_graph": {"source": "knowledge_graph", "data": {"entities": 200}, "reliability": 0.8}
        }
        return mock_data.get(source, {"source": source, "data": {}, "reliability": 0.5})

    def _calculate_confidence(self, results: list) -> float:
        if not results:
            return 0.0
        reliabilities = [r.get("reliability", 0.5) for r in results]
        base = sum(reliabilities) / len(reliabilities)
        bonus = min(0.1 * len(results), 0.2)
        return min(base + bonus, 1.0)
