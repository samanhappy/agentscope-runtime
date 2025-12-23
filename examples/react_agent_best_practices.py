#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ReActAgent Best Practices Example

This example demonstrates the recommended pattern for using ReActAgent 
in agentscope-runtime: creating a new agent instance for each request
while reusing service instances.

Key Concepts:
1. ✅ Create new ReActAgent instance per request
2. ✅ Reuse service instances (StateService, SessionHistoryService, SandboxService)
3. ✅ Persist and restore agent state across requests
4. ❌ Do NOT reuse the same ReActAgent instance across requests
"""

import os

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import Toolkit, execute_python_code

from agentscope_runtime.adapters.agentscope.memory import (
    AgentScopeSessionHistoryMemory,
)
from agentscope_runtime.engine.app import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.engine.services.agent_state import (
    InMemoryStateService,
)
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)

# Initialize AgentApp
agent_app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant demonstrating best practices",
)


@agent_app.init
async def init_func(self):
    """
    Initialize long-lived service instances.
    
    Best Practice: Initialize and reuse service instances in @agent_app.init
    These services are shared across all requests and provide:
    - State management (StateService)
    - Session history management (SessionHistoryService)
    
    ✅ DO: Initialize services here for reuse
    ❌ DON'T: Create these services in query_func for each request
    """
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()

    await self.state_service.start()
    await self.session_service.start()
    
    print("✅ Services initialized and ready for reuse across requests")


@agent_app.shutdown
async def shutdown_func(self):
    """
    Clean up service resources.
    
    Best Practice: Properly shut down services in @agent_app.shutdown
    """
    await self.state_service.stop()
    await self.session_service.stop()
    
    print("✅ Services shut down successfully")


@agent_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    Process user queries with a new ReActAgent instance.
    
    Best Practice Pattern:
    1. Load previous state from StateService
    2. Create NEW ReActAgent instance for this request
    3. Restore state to the new instance
    4. Process the request
    5. Save updated state back to StateService
    
    ✅ DO: Create new agent instance per request
    ❌ DON'T: Reuse the same agent instance across requests
    
    Why create new instances?
    - Session isolation: Different users/sessions don't interfere
    - State safety: No race conditions in concurrent scenarios
    - Memory management: Automatic cleanup after request
    - Flexibility: Each request can have different tools/config
    """
    session_id = request.session_id
    user_id = request.user_id

    # Step 1: Load previous state (if any)
    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )

    # Step 2: Prepare tools (can be created fresh or reused if read-only)
    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)

    # Step 3: Create NEW ReActAgent instance for THIS request
    # This is the recommended pattern - create fresh instance per request
    agent = ReActAgent(
        name="Friday",
        model=DashScopeChatModel(
            "qwen-turbo",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            enable_thinking=True,
            stream=True,
        ),
        sys_prompt="You're a helpful assistant named Friday.",
        toolkit=toolkit,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=session_id,
            user_id=user_id,
        ),
        formatter=DashScopeChatFormatter(),
    )
    agent.set_console_output_enabled(False)

    # Step 4: Restore previous state to the new instance
    if state:
        agent.load_state_dict(state)

    # Step 5: Process the request with streaming output
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    # Step 6: Save updated state for next request
    # The agent instance will be garbage collected after this function returns
    state = agent.state_dict()

    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=state,
    )


if __name__ == "__main__":
    """
    Run the agent app with recommended best practices:
    - Services are initialized once in @agent_app.init
    - Each request creates a new ReActAgent instance
    - State is persisted and restored via StateService
    - Services are properly shut down in @agent_app.shutdown
    """
    print("=" * 80)
    print("ReActAgent Best Practices Example")
    print("=" * 80)
    print("Starting AgentApp with the following best practices:")
    print("  ✅ Reusable service instances (StateService, SessionHistoryService)")
    print("  ✅ New ReActAgent instance per request")
    print("  ✅ State persistence across requests")
    print("  ✅ Proper session isolation")
    print("=" * 80)
    
    agent_app.run(host="127.0.0.1", port=8090)
