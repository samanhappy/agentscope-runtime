# -*- coding: utf-8 -*-
"""
Parallel Multi-Agent System - Independent Deployment

This example demonstrates deploying multiple agents as independent services
that communicate via HTTP/A2A protocol.

Architecture:
- Analyzer Agent (Port 8091): Analyzes data and provides insights
- Reporter Agent (Port 8092): Generates professional reports

Each agent runs in its own process and can be scaled independently.

Usage:
    # Terminal 1 - Start Analyzer Agent
    python parallel_agent_analyzer.py

    # Terminal 2 - Start Reporter Agent
    python parallel_agent_reporter.py

    # Terminal 3 - Run Orchestrator
    python parallel_orchestrator.py
"""
import os

from agentscope.agent import DialogAgent
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import (
    AgentScopeSessionHistoryMemory,
)
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)

# Note: In production, use RedisSessionHistoryService for distributed deployment
# from agentscope_runtime.engine.services.session_history import (
#     RedisSessionHistoryService,
# )

# Create Analyzer AgentApp
analyzer_app = AgentApp(
    app_name="AnalyzerAgent",
    app_description="Data analysis specialist agent",
)


@analyzer_app.init
async def init_func(self):
    """Initialize session history service"""
    # For production: Use Redis for distributed deployment
    # self.session_service = RedisSessionHistoryService(
    #     host=os.getenv("REDIS_HOST", "localhost"),
    #     port=int(os.getenv("REDIS_PORT", 6379)),
    #     db=0,
    # )

    self.session_service = InMemorySessionHistoryService()
    await self.session_service.start()
    print("✅ Analyzer Agent: Session service initialized")


@analyzer_app.shutdown
async def shutdown_func(self):
    """Cleanup session history service"""
    await self.session_service.stop()
    print("✅ Analyzer Agent: Session service stopped")


@analyzer_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    Analyze data and provide insights

    Args:
        msgs: User messages with data to analyze
        request: Agent request containing session_id and user_id
    """
    session_id = request.session_id
    user_id = request.user_id

    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )

    agent = DialogAgent(
        name="Analyzer",
        sys_prompt="""You are a professional data analyst.

Your responsibilities:
1. Analyze the provided data or question carefully
2. Identify patterns, trends, and key insights
3. Provide structured analysis with clear findings
4. Use data-driven reasoning
5. Highlight important metrics and statistics

Be thorough but concise. Focus on actionable insights.""",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=session_id,
            user_id=user_id,
        ),
    )
    agent.set_console_output_enabled(False)

    print(f"🔍 Analyzing data for session: {session_id}")

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last


if __name__ == "__main__":
    print("=" * 60)
    print("Analyzer Agent Service")
    print("=" * 60)
    print("\nStarting Analyzer Agent on http://0.0.0.0:8091/process")
    print("\nThis agent specializes in:")
    print("  - Data analysis")
    print("  - Pattern recognition")
    print("  - Insight generation")
    print("\nTest with:")
    print('  curl -N -X POST "http://localhost:8091/process" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"input": [{"role": "user", ')
    print('      "content": [{"type": "text", ')
    print('      "text": "Analyze Q4 2024 sales data"}]}], ')
    print('      "session_id": "test-123"}\'')
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    analyzer_app.run(host="0.0.0.0", port=8091)
