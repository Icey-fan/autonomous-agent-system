#!/usr/bin/env python3
"""
Autonomous Agent System - 演示脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from agents import AgentOrchestrator


def print_banner(text: str):
    print(f"\n{'='*70}\n  {text}\n{'='*70}\n")


def print_json(data: dict, title: str = ""):
    if title:
        print(f"\n📋 {title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def demo_churn_analysis():
    print_banner("场景一：用户流失风险分析与召回策略")
    orchestrator = AgentOrchestrator(max_workers=4)

    business_rules = [
        {"name": "高风险预警", "type": "hard", "keywords": ["流失", "churn"], "condition": "critical"},
        {"name": "隐私合规", "type": "hard", "keywords": ["用户", "隐私"], "condition": "personal_data"},
        {"name": "成本控制", "type": "soft", "keywords": ["预算", "成本"], "threshold": 100000}
    ]

    result = orchestrator.process_task(
        "分析当前用户流失风险并制定召回策略，要求考虑成本控制和数据隐私合规",
        business_rules=business_rules,
        metadata={"project": "user_retention_q2", "priority": "high"}
    )

    print_json(result["execution_summary"], "执行摘要")
    print_json(result["final_decision"]["risk_assessment"], "风险评估")
    print_json(result["final_decision"]["primary_plan"], "主方案")
    orchestrator.shutdown()
    return result


def demo_market_entry():
    print_banner("场景二：东南亚电商市场进入可行性分析")
    orchestrator = AgentOrchestrator(max_workers=5)

    business_rules = [
        {"name": "市场准入合规", "type": "hard", "keywords": ["合规", "license"], "condition": "non_compliant"},
        {"name": "投资回报率", "type": "soft", "keywords": ["ROI", "回报"], "threshold": 0.15}
    ]

    result = orchestrator.process_task(
        "评估进入东南亚电商市场的可行性，包括市场规模、竞争格局、合规要求和盈利预测",
        business_rules=business_rules,
        metadata={"project": "market_expansion_2024", "region": "SEA"}
    )

    print_json(result["execution_summary"], "执行摘要")
    print_json(result["final_decision"]["confidence"], "置信度分析")
    print_json(result["final_decision"]["impact_assessment"], "影响评估")
    orchestrator.shutdown()
    return result


if __name__ == "__main__":
    print_banner("Autonomous Agent System - 自主智能体系统演示")
    demo_churn_analysis()
    demo_market_entry()
    print_banner("演示完成")
    print("✅ 展示了：任务拆解、多智能体协同、长链推理、闭环校验、决策输出")
