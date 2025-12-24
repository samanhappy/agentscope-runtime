# -*- coding: utf-8 -*-
"""
Collaborative Multi-Agent System (Manager-Worker Pattern)

This example demonstrates a Manager-Worker collaboration pattern where:
- Manager: Coordinates tasks and synthesizes results
- Researcher: Gathers and analyzes information
- Coder: Writes and debugs code

The Manager decomposes tasks, delegates to workers, and combines results.

Usage:
    python collaborative_agents.py

Test with:
    curl -N -X POST "http://localhost:8090/process" \
      -H "Content-Type: application/json" \
      -d '{
        "input": [{
          "role": "user",
          "content": [{"type": "text", "text": "Create a Python function to calculate fibonacci numbers"}]
        }],
        "session_id": "collab-123"
      }'
"""
import os

from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import (
    AgentScopeSessionHistoryMemory,
)
from agentscope_runtime.engine.services.agent_state import (
    InMemoryStateService,
)
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)

# Create AgentApp
agent_app = AgentApp(
    app_name="ManagerWorkerSystem",
    app_description="Collaborative multi-agent system with Manager-Worker pattern",
)


@agent_app.init
async def init_func(self):
    """Initialize state and session services"""
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()

    await self.state_service.start()
    await self.session_service.start()
    print("✅ State and Session services initialized")


@agent_app.shutdown
async def shutdown_func(self):
    """Cleanup services"""
    await self.state_service.stop()
    await self.session_service.stop()
    print("✅ Services stopped")


@agent_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    Process user query through Manager-Worker collaboration

    Workflow:
        1. Manager analyzes the task
        2. Workers (Researcher, Coder) execute sub-tasks
        3. Manager synthesizes the results

    Args:
        msgs: User messages
        request: Agent request containing session_id and user_id
    """
    session_id = request.session_id
    user_id = request.user_id

    # Create shared model with streaming
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )

    # Manager Agent: Coordinates and synthesizes
    manager = ReActAgent(
        name="Manager",
        model=model,
        sys_prompt="""You are a project manager coordinating a team of specialists.

Your responsibilities:
1. Understand the user's request thoroughly
2. Break down complex tasks into manageable sub-tasks
3. Identify which specialist (Researcher or Coder) is needed
4. Coordinate the work of specialists
5. Synthesize results into a coherent final response

Be concise in your coordination and clear in your final synthesis.""",
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_manager",
            user_id=user_id,
        ),
    )
    manager.set_console_output_enabled(False)

    # Researcher Agent: Gathers and analyzes information
    researcher = ReActAgent(
        name="Researcher",
        model=model,
        sys_prompt="""You are a research specialist.

Your responsibilities:
1. Gather relevant information and context
2. Analyze data and find patterns
3. Provide evidence-based insights
4. Cite sources when applicable

Be thorough but concise in your research.""",
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_researcher",
            user_id=user_id,
        ),
    )
    researcher.set_console_output_enabled(False)

    # Coder Agent: Writes and debugs code
    coder = ReActAgent(
        name="Coder",
        model=model,
        sys_prompt="""You are a programming specialist.

Your responsibilities:
1. Write clean, well-documented code
2. Follow best practices and coding standards
3. Include error handling
4. Provide usage examples

Write code that is efficient, readable, and maintainable.""",
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_coder",
            user_id=user_id,
        ),
    )
    coder.set_console_output_enabled(False)

    # Phase 1: Manager analyzes the task
    print("👔 Manager is analyzing the task...")
    manager_analysis = await manager(msgs)

    # Phase 2: Delegate to workers
    # In a real scenario, manager would decide which workers to use
    # Here we demonstrate both workers for completeness

    print("🔬 Researcher is gathering information...")
    research_task = f"""Based on the manager's analysis: {manager_analysis}

Please research and provide relevant context, best practices, or 
background information needed to complete this task."""
    research_result = await researcher(research_task)

    print("💻 Coder is implementing the solution...")
    coding_task = f"""Based on the manager's analysis: {manager_analysis}
And the research findings: {research_result}

Please implement the requested functionality with clean code and examples."""
    code_result = await coder(coding_task)

    # Phase 3: Manager synthesizes results
    print("👔 Manager is synthesizing the final response...")
    synthesis_instruction = f"""You coordinated a team to complete the user's request.

Research findings:
{research_result}

Code implementation:
{code_result}

Please synthesize these results into a comprehensive final response that:
1. Addresses the user's original question
2. Integrates the research and code appropriately
3. Provides clear guidance on next steps if needed

Keep it well-organized and user-friendly."""

    async for msg, last in stream_printing_messages(
        agents=[manager],
        coroutine_task=manager(synthesis_instruction),
    ):
        yield msg, last


if __name__ == "__main__":
    print("=" * 60)
    print("Manager-Worker Collaborative System")
    print("=" * 60)
    print("\nStarting AgentApp on http://127.0.0.1:8090/process")
    print("\nThis example demonstrates:")
    print("  - Manager-Worker collaboration pattern")
    print("  - Task decomposition and delegation")
    print("  - Result synthesis")
    print("  - State management across multiple agents")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    agent_app.run(host="127.0.0.1", port=8090)
