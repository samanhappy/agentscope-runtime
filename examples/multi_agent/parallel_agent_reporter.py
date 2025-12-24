# -*- coding: utf-8 -*-
"""
Reporter Agent - Part of Parallel Multi-Agent System

This agent generates professional reports based on analysis or data.
Runs independently on port 8092.

Usage:
    python parallel_agent_reporter.py

Test with:
    curl -N -X POST "http://localhost:8092/process" \
      -H "Content-Type: application/json" \
      -d '{
        "input": [{
          "role": "user",
          "content": [{"type": "text", "text": "Generate a report on cloud computing trends"}]
        }],
        "session_id": "test-123"
      }'
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

# Create Reporter AgentApp
reporter_app = AgentApp(
    app_name="ReportAgent",
    app_description="Professional report generation agent",
)


@reporter_app.init
async def init_func(self):
    """Initialize session history service"""
    # For production: Use Redis with different db for isolation
    # self.session_service = RedisSessionHistoryService(
    #     host=os.getenv("REDIS_HOST", "localhost"),
    #     port=int(os.getenv("REDIS_PORT", 6379)),
    #     db=1,  # Different db from Analyzer
    # )

    self.session_service = InMemorySessionHistoryService()
    await self.session_service.start()
    print("✅ Reporter Agent: Session service initialized")


@reporter_app.shutdown
async def shutdown_func(self):
    """Cleanup session history service"""
    await self.session_service.stop()
    print("✅ Reporter Agent: Session service stopped")


@reporter_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    Generate professional reports

    Args:
        msgs: User messages with content to report on
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
        name="Reporter",
        sys_prompt="""You are a professional report writer.

Your responsibilities:
1. Create well-structured, professional reports
2. Use clear headings and sections
3. Present information logically
4. Include executive summary when appropriate
5. Use professional language and formatting
6. Highlight key findings and recommendations

Write reports that are informative, concise, and easy to understand.""",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=session_id,
            user_id=user_id,
        ),
    )
    agent.set_console_output_enabled(False)

    print(f"📝 Generating report for session: {session_id}")

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last


if __name__ == "__main__":
    print("=" * 60)
    print("Reporter Agent Service")
    print("=" * 60)
    print("\nStarting Reporter Agent on http://0.0.0.0:8092/process")
    print("\nThis agent specializes in:")
    print("  - Report generation")
    print("  - Document structuring")
    print("  - Professional writing")
    print("\nTest with:")
    print('  curl -N -X POST "http://localhost:8092/process" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"input": [{"role": "user", ')
    print('      "content": [{"type": "text", ')
    print('      "text": "Generate executive summary"}]}], ')
    print('      "session_id": "test-123"}\'')
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    reporter_app.run(host="0.0.0.0", port=8092)
