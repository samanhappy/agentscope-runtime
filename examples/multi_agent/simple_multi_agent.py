# -*- coding: utf-8 -*-
"""
Simple Multi-Agent Example

This example demonstrates how to orchestrate multiple agents within a single
AgentApp. Two agents (Analyst and Writer) work sequentially to process user queries.

Usage:
    python simple_multi_agent.py

Test with:
    curl -N -X POST "http://localhost:8090/process" \
      -H "Content-Type: application/json" \
      -d '{
        "input": [{
          "role": "user",
          "content": [{"type": "text", "text": "What are the benefits of cloud computing?"}]
        }],
        "session_id": "demo-123"
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

# Create AgentApp
agent_app = AgentApp(
    app_name="SimpleMultiAgent",
    app_description="Simple multi-agent orchestration with Analyst and Writer",
)


@agent_app.init
async def init_func(self):
    """Initialize session history service"""
    self.session_service = InMemorySessionHistoryService()
    await self.session_service.start()
    print("✅ Session service initialized")


@agent_app.shutdown
async def shutdown_func(self):
    """Cleanup session history service"""
    await self.session_service.stop()
    print("✅ Session service stopped")


@agent_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    Process user query through Analyst -> Writer pipeline

    Args:
        msgs: User messages
        request: Agent request containing session_id and user_id
    """
    session_id = request.session_id
    user_id = request.user_id

    # Create shared model
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )

    # Create Analyst Agent
    analyst = DialogAgent(
        name="Analyst",
        sys_prompt="""You are a data analyst. Your role is to:
        1. Analyze the user's question carefully
        2. Identify key points and data requirements
        3. Provide structured analysis
        Keep your analysis concise and focused.""",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_analyst",
            user_id=user_id,
        ),
    )
    analyst.set_console_output_enabled(False)

    # Create Writer Agent
    writer = DialogAgent(
        name="Writer",
        sys_prompt="""You are a technical writer. Your role is to:
        1. Take the analyst's findings
        2. Write a clear, well-structured response
        3. Make complex concepts easy to understand
        Use simple language and good formatting.""",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_writer",
            user_id=user_id,
        ),
    )
    writer.set_console_output_enabled(False)

    # Step 1: Analyst processes the query
    print(f"🔍 Analyst is analyzing the query...")
    analysis_result = await analyst(msgs)

    # Step 2: Writer creates final response based on analysis
    print(f"✍️  Writer is crafting the response...")
    writer_instruction = f"""Based on this analysis:
    {analysis_result}

    Please write a clear, comprehensive response to the user's original question.
    """

    async for msg, last in stream_printing_messages(
        agents=[writer],
        coroutine_task=writer(writer_instruction),
    ):
        yield msg, last


if __name__ == "__main__":
    print("=" * 60)
    print("Simple Multi-Agent System")
    print("=" * 60)
    print("\nStarting AgentApp on http://127.0.0.1:8090/process")
    print("\nThis example demonstrates:")
    print("  - Sequential agent orchestration")
    print("  - Agent memory management")
    print("  - Streaming responses")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    agent_app.run(host="127.0.0.1", port=8090)
