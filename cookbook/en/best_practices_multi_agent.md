# Multi-Agent Deployment Best Practices

This document provides best practices and example code for deploying multiple agents in production environments using AgentScope Runtime, based on the source code analysis.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Deployment Patterns](#deployment-patterns)
- [Best Practices](#best-practices)
- [Example Code](#example-code)

## Core Concepts

### AgentApp Architecture

AgentScope Runtime provides a unified agent application deployment framework through `AgentApp`. Each `AgentApp` can:

1. **Encapsulate single or multiple agents**: Orchestrate multiple agents within `@agent_app.query()`
2. **Share infrastructure services**: State management, session history, long-term memory, etc. can be shared across agents
3. **Independent deployment**: Each `AgentApp` can be deployed as a microservice
4. **Protocol support**: Automatically supports A2A (Agent-to-Agent), Response API, and other protocols

### Key Components

```python
from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory
```

## Deployment Patterns

### Pattern 1: Multi-Agent Orchestration within Single AgentApp

**Use Cases**:
- Agents need tight collaboration
- Share the same service instances (memory, state, etc.)
- Orchestration logic completed within a single application

**Pros**:
- Simple deployment, low resource usage
- Low latency between agents
- Easy to debug and maintain

**Cons**:
- All agents in same process, failures affect each other
- Scalability limited to single process

**Suitable For**:
- Master-worker agent collaboration (e.g., Manager-Worker)
- Sequential agent pipelines
- Small-scale multi-agent systems (2-5 agents)

### Pattern 2: Multiple Independent AgentApps

**Use Cases**:
- Agents are functionally independent and need isolated deployment
- Need to scale different agents independently
- Different agents have different resource requirements

**Pros**:
- Good fault isolation
- Independent scaling and updates
- Flexible resource allocation

**Cons**:
- Increased deployment complexity
- Inter-agent communication requires network calls
- Need additional service discovery and load balancing

**Suitable For**:
- Large-scale multi-agent systems
- Agents maintained by different teams
- Production systems requiring high availability

### Pattern 3: Hybrid Deployment

**Use Cases**:
- Some agents need tight collaboration, others need independent deployment
- Layered architecture with core and auxiliary agents

**Pros**:
- Combines advantages of both patterns
- Maximum flexibility

**Cons**:
- Complex architectural design
- Higher operational difficulty

## Best Practices

### 1. Service Sharing Strategy

#### In-Memory Services (Development/Testing)

```python
# Suitable for single-machine deployment, rapid development
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService

state_service = InMemoryStateService()
session_service = InMemorySessionHistoryService()
```

#### Distributed Services (Production)

```python
# Suitable for multi-instance deployment, high availability scenarios
from agentscope_runtime.engine.services.agent_state import RedisStateService
from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService

state_service = RedisStateService(
    host="redis-host",
    port=6379,
    db=0
)
session_service = RedisSessionHistoryService(
    host="redis-host",
    port=6379,
    db=1
)
```

### 2. State Management

**Key Principles**:
- Each agent should have independent `session_id` and `user_id`
- State persistence should occur at request end
- State loading should happen after agent initialization

```python
# Correct state management pattern
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    # 1. Load state
    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )
    
    # 2. Create agent
    agent = create_agent(state=state)
    
    # 3. Execute task
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
    
    # 4. Save state
    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=agent.state_dict(),
    )
```

### 3. Memory Management

**Using Session History Memory**:

```python
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

memory = AgentScopeSessionHistoryMemory(
    service=session_service,
    session_id=session_id,
    user_id=user_id,
)
```

**Advantages**:
- Automatic session history persistence
- Cross-request context sharing
- Supports distributed deployment

### 4. Sandbox Integration

**Using Sandbox in Multi-Agent Scenarios**:

```python
from agentscope_runtime.sandbox import BrowserSandbox
from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter

# Create sandbox in init phase
@agent_app.init
async def init_func(self):
    self.sandbox = BrowserSandbox()
    self.sandbox.__enter__()  # Start sandbox
    
    # Wrap sandbox tools
    self.browser_navigate = sandbox_tool_adapter(self.sandbox.browser_navigate)

@agent_app.shutdown
async def shutdown_func(self):
    self.sandbox.__exit__(None, None, None)  # Close sandbox
```

### 5. Deployment Mode Selection

#### Local Development Mode

```python
# Quick start using run() method
agent_app.run(host="127.0.0.1", port=8090)
```

#### Daemon Mode

```python
from agentscope_runtime.engine.deployers import LocalDeployManager

deployer = LocalDeployManager(host="0.0.0.0", port=8090)
await agent_app.deploy(deployer=deployer)
```

#### Detached Process Mode

```python
from agentscope_runtime.engine.deployers import LocalDeployManager
from agentscope_runtime.engine.deployers.utils.deployment_modes import DeploymentMode

deployer = LocalDeployManager(host="0.0.0.0", port=8090)
await agent_app.deploy(
    deployer=deployer,
    mode=DeploymentMode.DETACHED_PROCESS
)
```

### 6. Multi-Agent Communication

#### Internal Communication (Same AgentApp)

```python
# Direct calls between agents
result1 = await agent1(message)
result2 = await agent2(result1)
```

#### Cross-AgentApp Communication (A2A Protocol)

```python
# Use A2A protocol for cross-service communication
from a2a import A2AClient

client = A2AClient(base_url="http://other-agent-service:8090")
response = await client.create_task(
    agent_id="agent2",
    task_input={"message": "Hello from Agent1"}
)
```

### 7. Monitoring and Observability

```python
# Enable tracing
from agentscope_runtime.engine.tracing import setup_tracing

setup_tracing(
    service_name="multi-agent-app",
    endpoint="http://jaeger:14268/api/traces"
)
```

### 8. Error Handling

```python
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    try:
        # Agent processing logic
        pass
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        # Send error message
        yield {"error": str(e)}, True
    finally:
        # Ensure state is saved
        await self.state_service.save_state(...)
```

## Example Code

### Example 1: Simple Multi-Agent Orchestration

Simple example of managing multiple agents within a single AgentApp.

```python
import os
from agentscope.agent import DialogAgent, UserAgent
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import sequentialpipeline

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

agent_app = AgentApp(
    app_name="SimpleMultiAgent",
    app_description="Simple multi-agent orchestration",
)

@agent_app.init
async def init_func(self):
    from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService
    self.session_service = InMemorySessionHistoryService()
    await self.session_service.start()

@agent_app.shutdown
async def shutdown_func(self):
    await self.session_service.stop()

@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    # Create model
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    
    # Create multiple agents
    analyst = DialogAgent(
        name="Analyst",
        sys_prompt="You are a data analyst. Analyze the user's question.",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_analyst",
            user_id=user_id,
        ),
    )
    
    writer = DialogAgent(
        name="Writer",
        sys_prompt="You are a technical writer. Write a clear response based on the analysis.",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_writer",
            user_id=user_id,
        ),
    )
    
    # Sequential execution
    analysis_result = analyst(msgs)
    final_result = writer(analysis_result)
    
    yield final_result, True

if __name__ == "__main__":
    agent_app.run(host="127.0.0.1", port=8090)
```

### Example 2: Collaborative Multi-Agent (Manager-Worker)

```python
import os
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

agent_app = AgentApp(
    app_name="ManagerWorkerSystem",
    app_description="Manager-Worker multi-agent system",
)

@agent_app.init
async def init_func(self):
    from agentscope_runtime.engine.services.agent_state import InMemoryStateService
    from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService
    
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    
    await self.state_service.start()
    await self.session_service.start()

@agent_app.shutdown
async def shutdown_func(self):
    await self.state_service.stop()
    await self.session_service.stop()

@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )
    
    # Manager Agent: Responsible for task decomposition and coordination
    manager = ReActAgent(
        name="Manager",
        model=model,
        sys_prompt="""You are a project manager. 
        Your role is to:
        1. Understand the user's request
        2. Break it down into sub-tasks
        3. Coordinate the work of specialist agents
        4. Synthesize the results
        """,
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_manager",
            user_id=user_id,
        ),
    )
    manager.set_console_output_enabled(False)
    
    # Worker Agents: Each responsible for specialized tasks
    researcher = ReActAgent(
        name="Researcher",
        model=model,
        sys_prompt="You are a researcher. Gather and analyze information.",
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_researcher",
            user_id=user_id,
        ),
    )
    researcher.set_console_output_enabled(False)
    
    coder = ReActAgent(
        name="Coder",
        model=model,
        sys_prompt="You are a programmer. Write and debug code.",
        toolkit=Toolkit(),
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=f"{session_id}_coder",
            user_id=user_id,
        ),
    )
    coder.set_console_output_enabled(False)
    
    # Manager analyzes task
    manager_response = await manager(msgs)
    
    # Based on Manager's decision, call appropriate Workers
    # Simplified here to call both Workers simultaneously
    research_result = await researcher(manager_response)
    code_result = await coder(manager_response)
    
    # Manager synthesizes results
    final_instruction = f"""
    Research findings: {research_result}
    Code implementation: {code_result}
    Please synthesize these results into a final response.
    """
    
    async for msg, last in stream_printing_messages(
        agents=[manager],
        coroutine_task=manager(final_instruction),
    ):
        yield msg, last

if __name__ == "__main__":
    agent_app.run(host="127.0.0.1", port=8090)
```

### Example 3: Multiple Independently Deployed AgentApps

**Agent Service 1 (agent1.py)**:

```python
import os
from agentscope.agent import DialogAgent
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

agent_app = AgentApp(
    app_name="AnalyzerAgent",
    app_description="Data analysis agent",
)

@agent_app.init
async def init_func(self):
    from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService
    
    # Use Redis to support distributed deployment
    self.session_service = RedisSessionHistoryService(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
    )
    await self.session_service.start()

@agent_app.shutdown
async def shutdown_func(self):
    await self.session_service.stop()

@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )
    
    agent = DialogAgent(
        name="Analyzer",
        sys_prompt="You are a data analyzer. Analyze data and provide insights.",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=session_id,
            user_id=user_id,
        ),
    )
    agent.set_console_output_enabled(False)
    
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

if __name__ == "__main__":
    agent_app.run(host="0.0.0.0", port=8091)
```

**Agent Service 2 (agent2.py)**:

```python
import os
from agentscope.agent import DialogAgent
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

agent_app = AgentApp(
    app_name="ReportAgent",
    app_description="Report generation agent",
)

@agent_app.init
async def init_func(self):
    from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService
    
    self.session_service = RedisSessionHistoryService(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=1,
    )
    await self.session_service.start()

@agent_app.shutdown
async def shutdown_func(self):
    await self.session_service.stop()

@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        stream=True,
    )
    
    agent = DialogAgent(
        name="Reporter",
        sys_prompt="You are a report writer. Create professional reports.",
        model=model,
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,
            session_id=session_id,
            user_id=user_id,
        ),
    )
    agent.set_console_output_enabled(False)
    
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

if __name__ == "__main__":
    agent_app.run(host="0.0.0.0", port=8092)
```

**Orchestrator (orchestrator.py)**:

```python
import asyncio
import httpx

async def call_agent(url: str, message: str, session_id: str):
    """Call a single agent service"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{url}/process",
            json={
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": message}]
                    }
                ],
                "session_id": session_id,
            },
            timeout=60.0,
        )
        return response.text

async def orchestrate_agents():
    """Orchestrate multiple independently deployed agents"""
    session_id = "demo-session-123"
    
    # 1. Call analyzer agent
    print("Calling Analyzer Agent...")
    analysis = await call_agent(
        "http://localhost:8091",
        "Analyze the sales data for Q4 2024",
        session_id
    )
    print(f"Analysis: {analysis}\n")
    
    # 2. Call report agent
    print("Calling Report Agent...")
    report = await call_agent(
        "http://localhost:8092",
        f"Generate a report based on: {analysis}",
        session_id
    )
    print(f"Report: {report}\n")

if __name__ == "__main__":
    asyncio.run(orchestrate_agents())
```

## Performance Optimization

### 1. Resource Allocation

- **CPU**: Recommended 2-4 CPU cores per AgentApp
- **Memory**: 4-8GB based on model size and session count
- **Concurrency**: Use uvicorn workers to increase concurrent processing

```python
# Start with multiple workers
uvicorn main:agent_app.app --host 0.0.0.0 --port 8090 --workers 4
```

### 2. Caching Strategy

```python
# Cache model instances
@agent_app.init
async def init_func(self):
    self.model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    # Warm up model
    await self.model.warmup()
```

### 3. Connection Pool Management

```python
# Redis connection pool configuration
from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService

session_service = RedisSessionHistoryService(
    host="redis-host",
    port=6379,
    db=0,
    max_connections=50,  # Connection pool size
    socket_timeout=5,
    socket_connect_timeout=5,
)
```

## Security Recommendations

### 1. API Key Management

```python
# Use environment variables
import os

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("DASHSCOPE_API_KEY not set")
```

### 2. Request Validation

```python
from fastapi import HTTPException

@agent_app.endpoint("/secure-process")
async def secure_handler(request: AgentRequest):
    # Validate API key
    api_key = request.headers.get("X-API-Key")
    if not validate_api_key(api_key):
        raise HTTPException(status_code=401, message="Invalid API key")
    
    # Process request
    ...
```

### 3. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@agent_app.endpoint("/rate-limited")
@limiter.limit("10/minute")
async def rate_limited_handler(request: AgentRequest):
    ...
```

## Troubleshooting

### Common Issues

1. **Agent State Loss**
   - Check if StateService is properly initialized and started
   - Ensure session_id remains consistent across requests

2. **Memory Leaks**
   - Ensure all services are properly closed in shutdown
   - Check if sandboxes are properly released

3. **Concurrency Issues**
   - Use distributed services (Redis) instead of in-memory services
   - Check database connection pool configuration

4. **Performance Bottlenecks**
   - Use async I/O
   - Enable streaming responses to reduce wait time
   - Consider using message queues for long-running tasks

## Summary

Choosing the right deployment pattern depends on specific business requirements:

- **Small-scale systems (2-5 agents)**: Use Pattern 1 (Single AgentApp)
- **Medium-large systems (5+ agents)**: Use Pattern 2 (Multiple AgentApps)
- **Complex systems**: Use Pattern 3 (Hybrid deployment)

Key Points:
1. Properly use state and session management services
2. Choose appropriate service implementations (in-memory vs distributed)
3. Implement monitoring and logging
4. Pay attention to resource isolation and error handling

## References

- [AgentScope Runtime Documentation](https://runtime.agentscope.io)
- [Deployment Guide](deployment.md)
- [Service Documentation](service/service.md)
- [Example Code](../../examples/multi_agent/)
