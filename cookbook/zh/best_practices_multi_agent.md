# 多智能体部署最佳实践

本文档基于 AgentScope Runtime 源码，提供在生产环境中部署多个智能体的最佳实践指南和示例代码。

## 目录

- [核心概念](#核心概念)
- [部署模式](#部署模式)
- [最佳实践](#最佳实践)
- [示例代码](#示例代码)

## 核心概念

### AgentApp 架构

AgentScope Runtime 通过 `AgentApp` 提供了统一的智能体应用部署框架。每个 `AgentApp` 可以：

1. **封装单个或多个智能体**：在 `@agent_app.query()` 中编排多个智能体
2. **共享基础服务**：状态管理、会话历史、长期记忆等服务可在多个智能体间共享
3. **独立部署**：每个 `AgentApp` 可以独立部署为微服务
4. **协议支持**：自动支持 A2A (Agent-to-Agent)、Response API 等协议

### 关键组件

```python
from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory
```

## 部署模式

### 模式一：单个 AgentApp 内多智能体编排

**适用场景**：
- 智能体之间需要紧密协作
- 共享相同的服务实例（内存、状态等）
- 编排逻辑在单个应用内完成

**优点**：
- 部署简单，资源占用少
- 智能体间通信延迟低
- 易于调试和维护

**缺点**：
- 所有智能体在同一进程，故障会相互影响
- 扩展性受限于单个进程

**适用案例**：
- 主从式智能体协作（如 Manager-Worker）
- 顺序处理的智能体流水线
- 小规模多智能体系统（2-5个智能体）

### 模式二：多个 AgentApp 独立部署

**适用场景**：
- 智能体功能独立，需要隔离部署
- 需要独立扩展不同智能体
- 不同智能体有不同的资源需求

**优点**：
- 故障隔离性好
- 可独立扩展和更新
- 资源分配灵活

**缺点**：
- 部署复杂度增加
- 智能体间通信需要网络调用
- 需要额外的服务发现和负载均衡

**适用案例**：
- 大规模多智能体系统
- 不同团队维护的智能体
- 需要高可用性的生产系统

### 模式三：混合部署

**适用场景**：
- 部分智能体需要紧密协作，部分需要独立部署
- 有核心智能体和辅助智能体的分层架构

**优点**：
- 结合两种模式的优点
- 灵活性最高

**缺点**：
- 架构设计复杂
- 运维难度较高

## 最佳实践

### 1. 服务共享策略

#### 内存型服务（开发/测试环境）

```python
# 适用于单机部署、快速开发
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService

state_service = InMemoryStateService()
session_service = InMemorySessionHistoryService()
```

#### 分布式服务（生产环境）

```python
# 适用于多实例部署、高可用场景
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

### 2. 状态管理

**关键原则**：
- 每个智能体应有独立的 `session_id` 和 `user_id`
- 状态持久化应在请求结束时进行
- 加载状态应在智能体初始化后进行

```python
# 正确的状态管理模式
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    # 1. 加载状态
    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )
    
    # 2. 创建智能体
    agent = create_agent(state=state)
    
    # 3. 执行任务
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
    
    # 4. 保存状态
    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=agent.state_dict(),
    )
```

### 3. 内存管理

**使用会话历史记忆**：

```python
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory

memory = AgentScopeSessionHistoryMemory(
    service=session_service,
    session_id=session_id,
    user_id=user_id,
)
```

**优势**：
- 自动持久化会话历史
- 跨请求共享上下文
- 支持分布式部署

### 4. 沙箱集成

**在多智能体场景中使用沙箱**：

```python
from agentscope_runtime.sandbox import BrowserSandbox
from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter

# 在 init 阶段创建沙箱
@agent_app.init
async def init_func(self):
    self.sandbox = BrowserSandbox()
    self.sandbox.__enter__()  # 启动沙箱
    
    # 包装沙箱工具
    self.browser_navigate = sandbox_tool_adapter(self.sandbox.browser_navigate)

@agent_app.shutdown
async def shutdown_func(self):
    self.sandbox.__exit__(None, None, None)  # 关闭沙箱
```

### 5. 部署模式选择

#### 本地开发模式

```python
# 使用 run() 方法快速启动
agent_app.run(host="127.0.0.1", port=8090)
```

#### 守护进程模式

```python
from agentscope_runtime.engine.deployers import LocalDeployManager

deployer = LocalDeployManager(host="0.0.0.0", port=8090)
await agent_app.deploy(deployer=deployer)
```

#### 分离进程模式

```python
from agentscope_runtime.engine.deployers import LocalDeployManager
from agentscope_runtime.engine.deployers.utils.deployment_modes import DeploymentMode

deployer = LocalDeployManager(host="0.0.0.0", port=8090)
await agent_app.deploy(
    deployer=deployer,
    mode=DeploymentMode.DETACHED_PROCESS
)
```

### 6. 多智能体通信

#### 内部通信（同一 AgentApp）

```python
# 智能体之间直接调用
result1 = await agent1(message)
result2 = await agent2(result1)
```

#### 跨 AgentApp 通信（A2A 协议）

```python
# 使用 A2A 协议进行跨服务通信
from a2a import A2AClient

client = A2AClient(base_url="http://other-agent-service:8090")
response = await client.create_task(
    agent_id="agent2",
    task_input={"message": "Hello from Agent1"}
)
```

### 7. 监控与可观测性

```python
# 启用 tracing
from agentscope_runtime.engine.tracing import setup_tracing

setup_tracing(
    service_name="multi-agent-app",
    endpoint="http://jaeger:14268/api/traces"
)
```

### 8. 错误处理

```python
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    try:
        # 智能体处理逻辑
        pass
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        # 发送错误消息
        yield {"error": str(e)}, True
    finally:
        # 确保状态保存
        await self.state_service.save_state(...)
```

## 示例代码

### 示例 1：简单多智能体编排

在单个 AgentApp 中管理多个智能体的简单示例。

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
    
    # 创建模型
    model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    
    # 创建多个智能体
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
    
    # 顺序执行
    analysis_result = analyst(msgs)
    final_result = writer(analysis_result)
    
    yield final_result, True

if __name__ == "__main__":
    agent_app.run(host="127.0.0.1", port=8090)
```

### 示例 2：协作型多智能体（Manager-Worker）

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
    
    # Manager Agent: 负责任务分解和协调
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
    
    # Worker Agents: 各自负责专门任务
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
    
    # Manager 分析任务
    manager_response = await manager(msgs)
    
    # 根据 Manager 的决策，调用相应的 Worker
    # 这里简化为同时调用两个 Worker
    research_result = await researcher(manager_response)
    code_result = await coder(manager_response)
    
    # Manager 综合结果
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

### 示例 3：独立部署的多个 AgentApp

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
    
    # 使用 Redis 以支持分布式部署
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
    """调用单个智能体服务"""
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
    """编排多个独立部署的智能体"""
    session_id = "demo-session-123"
    
    # 1. 调用分析智能体
    print("Calling Analyzer Agent...")
    analysis = await call_agent(
        "http://localhost:8091",
        "Analyze the sales data for Q4 2024",
        session_id
    )
    print(f"Analysis: {analysis}\n")
    
    # 2. 调用报告智能体
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

## 性能优化建议

### 1. 资源分配

- **CPU**: 每个 AgentApp 建议分配 2-4 个 CPU 核心
- **内存**: 根据模型大小和会话数量，建议 4-8GB
- **并发**: 使用 uvicorn workers 增加并发处理能力

```python
# 启动多个 worker
uvicorn main:agent_app.app --host 0.0.0.0 --port 8090 --workers 4
```

### 2. 缓存策略

```python
# 缓存模型实例
@agent_app.init
async def init_func(self):
    self.model = DashScopeChatModel(
        "qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    # 预热模型
    await self.model.warmup()
```

### 3. 连接池管理

```python
# Redis 连接池配置
from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService

session_service = RedisSessionHistoryService(
    host="redis-host",
    port=6379,
    db=0,
    max_connections=50,  # 连接池大小
    socket_timeout=5,
    socket_connect_timeout=5,
)
```

## 安全建议

### 1. API 密钥管理

```python
# 使用环境变量
import os

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("DASHSCOPE_API_KEY not set")
```

### 2. 请求验证

```python
from fastapi import HTTPException

@agent_app.endpoint("/secure-process")
async def secure_handler(request: AgentRequest):
    # 验证 API 密钥
    api_key = request.headers.get("X-API-Key")
    if not validate_api_key(api_key):
        raise HTTPException(status_code=401, message="Invalid API key")
    
    # 处理请求
    ...
```

### 3. 速率限制

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@agent_app.endpoint("/rate-limited")
@limiter.limit("10/minute")
async def rate_limited_handler(request: AgentRequest):
    ...
```

## 故障排查

### 常见问题

1. **智能体状态丢失**
   - 检查 StateService 是否正确初始化和启动
   - 确认 session_id 在请求间保持一致

2. **内存泄漏**
   - 确保在 shutdown 中正确关闭所有服务
   - 检查沙箱是否正确释放

3. **并发问题**
   - 使用分布式服务（Redis）替代内存服务
   - 检查数据库连接池配置

4. **性能瓶颈**
   - 使用异步 I/O
   - 启用流式响应减少等待时间
   - 考虑使用消息队列处理长时间任务

## 总结

选择合适的部署模式取决于具体的业务需求：

- **小规模系统（2-5个智能体）**: 使用模式一（单 AgentApp）
- **中大规模系统（5+个智能体）**: 使用模式二（多 AgentApp）
- **复杂系统**: 使用模式三（混合部署）

关键要点：
1. 合理使用状态和会话管理服务
2. 选择合适的服务实现（内存 vs 分布式）
3. 做好监控和日志记录
4. 注意资源隔离和错误处理

## 参考资源

- [AgentScope Runtime 文档](https://runtime.agentscope.io)
- [部署指南](deployment.md)
- [服务文档](service/service.md)
- [示例代码](../../examples/multi_agent/)
