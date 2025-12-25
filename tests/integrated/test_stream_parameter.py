# -*- coding: utf-8 -*-
"""
Test for stream parameter support in /process endpoint.
This test verifies that stream=false can be used for non-streaming responses.
"""
import os
import multiprocessing
import time
import json
import aiohttp
import pytest

from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit, execute_python_code
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

PORT = 8091


def run_app():
    """Start AgentApp with streaming output enabled."""
    agent_app = AgentApp(
        app_name="TestAgent",
        app_description="A test agent for stream parameter testing",
    )

    @agent_app.init
    async def init_func(self):
        self.state_service = InMemoryStateService()
        self.session_service = InMemorySessionHistoryService()

        await self.state_service.start()
        await self.session_service.start()

    @agent_app.shutdown
    async def shutdown_func(self):
        await self.state_service.stop()
        await self.session_service.stop()

    @agent_app.query(framework="agentscope")
    async def query_func(
        self,
        msgs,
        request: AgentRequest = None,
        **kwargs,
    ):
        session_id = request.session_id
        user_id = request.user_id

        state = await self.state_service.export_state(
            session_id=session_id,
            user_id=user_id,
        )

        toolkit = Toolkit()
        toolkit.register_tool_function(execute_python_code)

        agent = ReActAgent(
            name="TestAgent",
            model=DashScopeChatModel(
                "qwen-turbo",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                enable_thinking=True,
                stream=True,
            ),
            sys_prompt="You're a helpful assistant named TestAgent.",
            toolkit=toolkit,
            memory=AgentScopeSessionHistoryMemory(
                service=self.session_service,
                session_id=session_id,
                user_id=user_id,
            ),
            formatter=DashScopeChatFormatter(),
        )
        agent.set_console_output_enabled(enabled=False)

        if state:
            agent.load_state_dict(state)

        async for msg, last in stream_printing_messages(
            agents=[agent],
            coroutine_task=agent(msgs),
        ):
            yield msg, last

        state = agent.state_dict()

        await self.state_service.save_state(
            user_id=user_id,
            session_id=session_id,
            state=state,
        )

    agent_app.run(host="127.0.0.1", port=PORT)


@pytest.fixture(scope="module")
def start_app():
    """Launch AgentApp in a separate process before the async tests."""
    proc = multiprocessing.Process(target=run_app)
    proc.start()
    import socket

    for _ in range(50):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("localhost", PORT))
            s.close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("Server did not start within timeout")

    yield
    proc.terminate()
    proc.join()


@pytest.mark.asyncio
async def test_process_endpoint_stream_true(start_app):
    """
    Test that stream=true (default) returns SSE streaming response.
    """
    url = f"http://localhost:{PORT}/process"
    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Say hello"},
                ],
            },
        ],
        "stream": True,  # Explicitly set to true
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            assert resp.status == 200
            # Should be text/event-stream for streaming
            assert resp.headers.get("Content-Type", "").startswith(
                "text/event-stream",
            )

            found_response = False
            async for chunk, _ in resp.content.iter_chunks():
                if not chunk:
                    continue

                line = chunk.decode("utf-8").strip()
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                        if "output" in event or "status" in event:
                            found_response = True
                    except json.JSONDecodeError:
                        continue

            assert found_response, "Did not receive any valid streaming response"


@pytest.mark.asyncio
async def test_process_endpoint_stream_false(start_app):
    """
    Test that stream=false returns a non-streaming JSON response.
    """
    url = f"http://localhost:{PORT}/process"
    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Say hello"},
                ],
            },
        ],
        "stream": False,  # Disable streaming
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            assert resp.status == 200
            # Should be application/json for non-streaming
            assert resp.headers.get("Content-Type", "").startswith(
                "application/json",
            )

            # Should be able to parse as a single JSON response
            data = await resp.json()
            
            # Verify response structure
            assert isinstance(data, dict)
            # Should have either an output field or error field
            assert "output" in data or "error" in data or "status" in data
            
            # If output exists, verify it's a complete response
            if "output" in data:
                assert isinstance(data["output"], list)


@pytest.mark.asyncio
async def test_process_endpoint_default_stream(start_app):
    """
    Test that default behavior (no stream parameter) is streaming.
    """
    url = f"http://localhost:{PORT}/process"
    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Say hello"},
                ],
            },
        ],
        # No stream parameter - should default to True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            assert resp.status == 200
            # Should default to text/event-stream
            assert resp.headers.get("Content-Type", "").startswith(
                "text/event-stream",
            )
