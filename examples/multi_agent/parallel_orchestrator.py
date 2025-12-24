# -*- coding: utf-8 -*-
"""
Orchestrator for Parallel Multi-Agent System

This script demonstrates how to orchestrate multiple independently deployed
agents by making HTTP calls to their endpoints.

Prerequisites:
    1. Start Analyzer Agent: python parallel_agent_analyzer.py
    2. Start Reporter Agent: python parallel_agent_reporter.py
    3. Run this orchestrator: python parallel_orchestrator.py

The orchestrator:
    1. Calls Analyzer Agent to analyze data
    2. Calls Reporter Agent to generate a report based on the analysis
    3. Prints the results
"""
import asyncio
import httpx
import json


async def call_agent(url: str, message: str, session_id: str) -> dict:
    """
    Call a single agent service via HTTP

    Args:
        url: Base URL of the agent service
        message: Message to send to the agent
        session_id: Session identifier for context persistence

    Returns:
        Response from the agent
    """
    request_payload = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": message}],
            }
        ],
        "session_id": session_id,
    }

    print(f"\n📤 Calling {url}")
    print(f"   Message: {message[:100]}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{url}/process",
                json=request_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                timeout=120.0,
            )

            if response.status_code == 200:
                # Parse SSE response
                result_text = ""
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("object") == "content":
                                result_text += data.get("text", "")
                        except json.JSONDecodeError:
                            continue

                print(f"✅ Received response ({len(result_text)} chars)")
                return {"success": True, "content": result_text}
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }

    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
        return {"success": False, "error": f"Connection failed: {e}"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"success": False, "error": str(e)}


async def orchestrate_data_analysis_workflow():
    """
    Orchestrate a complete workflow:
    1. Analyzer analyzes the data
    2. Reporter generates a report based on the analysis
    """
    print("=" * 70)
    print("Multi-Agent Orchestration - Data Analysis Workflow")
    print("=" * 70)

    session_id = "demo-workflow-123"
    user_query = "Analyze the trends in artificial intelligence adoption in 2024"

    # Phase 1: Call Analyzer Agent
    print("\n🔍 Phase 1: Data Analysis")
    print("-" * 70)

    analysis_response = await call_agent(
        url="http://localhost:8091",
        message=user_query,
        session_id=session_id,
    )

    if not analysis_response.get("success"):
        print("\n❌ Analysis failed. Ensure Analyzer Agent is running on port 8091")
        return

    analysis_content = analysis_response.get("content", "")
    print(f"\n📊 Analysis Result:")
    print("-" * 70)
    print(analysis_content[:500])
    if len(analysis_content) > 500:
        print(f"... ({len(analysis_content) - 500} more characters)")

    # Phase 2: Call Reporter Agent
    print("\n\n📝 Phase 2: Report Generation")
    print("-" * 70)

    report_instruction = f"""Based on the following analysis, generate a professional report:

Analysis:
{analysis_content}

Please create a comprehensive report with:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Conclusions and Recommendations
"""

    report_response = await call_agent(
        url="http://localhost:8092",
        message=report_instruction,
        session_id=session_id,
    )

    if not report_response.get("success"):
        print("\n❌ Report generation failed. Ensure Reporter Agent is running on port 8092")
        return

    report_content = report_response.get("content", "")
    print(f"\n📄 Generated Report:")
    print("=" * 70)
    print(report_content)
    print("=" * 70)

    # Summary
    print("\n\n✅ Workflow Completed Successfully!")
    print("-" * 70)
    print(f"Session ID: {session_id}")
    print(f"Analysis length: {len(analysis_content)} characters")
    print(f"Report length: {len(report_content)} characters")
    print("-" * 70)


async def orchestrate_parallel_queries():
    """
    Demonstrate parallel execution of multiple agents simultaneously
    """
    print("=" * 70)
    print("Multi-Agent Orchestration - Parallel Queries")
    print("=" * 70)

    session_id = "demo-parallel-123"

    # Execute both agents in parallel
    print("\n⚡ Executing parallel queries...")

    results = await asyncio.gather(
        call_agent(
            url="http://localhost:8091",
            message="Analyze the benefits of microservices architecture",
            session_id=f"{session_id}_analysis",
        ),
        call_agent(
            url="http://localhost:8092",
            message="Generate a brief report on cloud-native technologies",
            session_id=f"{session_id}_report",
        ),
    )

    analyzer_result, reporter_result = results

    print("\n\n📊 Results:")
    print("-" * 70)
    print("\n1️⃣  Analyzer Response:")
    print(analyzer_result.get("content", "Error")[:300])
    print("\n2️⃣  Reporter Response:")
    print(reporter_result.get("content", "Error")[:300])
    print("-" * 70)


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("Parallel Multi-Agent System Orchestrator")
    print("=" * 70)
    print("\nMake sure both agents are running:")
    print("  ✓ Analyzer Agent on http://localhost:8091")
    print("  ✓ Reporter Agent on http://localhost:8092")
    print("\nChoose a demonstration:")
    print("  1. Sequential Workflow (Analysis → Report)")
    print("  2. Parallel Queries (Both agents simultaneously)")
    print("  3. Both demonstrations")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        asyncio.run(orchestrate_data_analysis_workflow())
    elif choice == "2":
        asyncio.run(orchestrate_parallel_queries())
    elif choice == "3":
        asyncio.run(orchestrate_data_analysis_workflow())
        print("\n\n")
        asyncio.run(orchestrate_parallel_queries())
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
