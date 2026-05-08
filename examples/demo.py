#!/usr/bin/env python3
"""
Autonomous Agent System - Demo Script (Fixed)
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents import AgentOrchestrator


def print_banner(text: str) -> None:
    print(f"\n{'='*70}\n {text}\n{'='*70}\n")


def print_json(data: dict, title: str = "") -> None:
    if title:
        print(f"\n📋 {title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


async def demo_churn_analysis():
    print_banner("Scenario 1: User Churn Risk Analysis & Recall Strategy")
    orchestrator = AgentOrchestrator(max_workers=4)

    business_rules = [
        {"name": "High Risk Alert", "type": "hard", "keywords": ["churn", "流失"], "condition": "critical"},
        {"name": "Privacy Compliance", "type": "hard", "keywords": ["user", "用户", "privacy"], "condition": "personal_data"},
        {"name": "Cost Control", "type": "soft", "keywords": ["budget", "成本"], "threshold": 100000},
    ]

    result = await orchestrator.process_task(
        "Analyze current user churn risk and develop recall strategy, considering cost control and data privacy compliance",
        business_rules=business_rules,
        metadata={"project": "user_retention_q2", "priority": "high"},
    )

    print_json(result.get("execution_summary"), "Execution Summary")
    if "final_decision" in result:
        print_json(result["final_decision"].get("risk_assessment"), "Risk Assessment")
        print_json(result["final_decision"].get("primary_plan"), "Primary Plan")
    
    await orchestrator.shutdown()
    return result


async def demo_market_entry():
    print_banner("Scenario 2: Southeast Asia E-commerce Market Entry Feasibility")
    orchestrator = AgentOrchestrator(max_workers=5)

    business_rules = [
        {"name": "Market Access Compliance", "type": "hard", "keywords": ["compliance", "合规", "license"], "condition": "non_compliant"},
        {"name": "ROI Threshold", "type": "soft", "keywords": ["ROI", "return"], "threshold": 0.15},
    ]

    result = await orchestrator.process_task(
        "Evaluate feasibility of entering Southeast Asia e-commerce market, including market size, competition, compliance requirements, and profit forecast",
        business_rules=business_rules,
        metadata={"project": "market_expansion_2024", "region": "SEA"},
    )

    print_json(result.get("execution_summary"), "Execution Summary")
    if "final_decision" in result:
        print_json(result["final_decision"].get("confidence"), "Confidence Analysis")
        print_json(result["final_decision"].get("impact_assessment"), "Impact Assessment")
    
    await orchestrator.shutdown()
    return result


async def main():
    print_banner("Autonomous Agent System v2.0 - Demo")
    
    try:
        await demo_churn_analysis()
        await demo_market_entry()
    except Exception as e:
        print(f"Demo error: {e}")
        raise
    
    print_banner("Demo Complete")
    print("✅ Demonstrated: Task decomposition, multi-agent collaboration, long-chain reasoning, closed-loop validation, decision output")


if __name__ == "__main__":
    asyncio.run(main())
