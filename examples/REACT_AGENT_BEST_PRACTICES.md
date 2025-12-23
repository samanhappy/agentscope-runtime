# ReActAgent 复用最佳实践 / ReActAgent Reuse Best Practices

[中文](#中文) | [English](#english)

---

## 中文

### 问题

在使用 AgentScope Runtime 时，开发者经常会问：

> **ReActAgent 需要在每次 `@agent_app.query(framework="agentscope")` 方法中都创建吗，还是可以复用？**

### 答案

**推荐每次请求都创建新的 ReActAgent 实例**，而不是复用同一个实例。

### 为什么？

1. **会话隔离性**：确保不同用户和会话之间的状态完全隔离
2. **状态管理安全**：避免多并发场景下的状态竞争
3. **内存管理清晰**：自动垃圾回收，避免内存泄漏
4. **配置灵活性**：每个请求可以有不同的工具集和配置

### 最佳实践

#### ✅ 推荐模式：每次请求创建新实例

```python
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    # 1. 加载之前的状态
    state = await self.state_service.export_state(
        session_id=request.session_id,
        user_id=request.user_id,
    )
    
    # 2. 创建新的 Agent 实例
    agent = ReActAgent(...)
    
    # 3. 恢复状态
    if state:
        agent.load_state_dict(state)
    
    # 4. 处理请求
    async for msg, last in stream_printing_messages(...):
        yield msg, last
    
    # 5. 保存状态
    await self.state_service.save_state(...)
```

#### ✅ 应该复用的组件

在 `@agent_app.init` 中初始化并复用：

- `StateService`：状态管理服务
- `SessionHistoryService`：会话历史服务  
- `SandboxService`：沙箱服务
- 数据库连接池
- Redis 连接
- 外部 API 客户端

```python
@agent_app.init
async def init_func(self):
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    self.sandbox_service = SandboxService()
    
    await self.state_service.start()
    await self.session_service.start()
    await self.sandbox_service.start()
```

#### ❌ 不推荐模式：复用 Agent 实例

```python
# ❌ 不要这样做！
class BadExample:
    def __init__(self):
        self.agent = ReActAgent(...)  # 不要在类级别创建
    
    @agent_app.query(framework="agentscope")
    async def query_func(self, msgs, request, **kwargs):
        # ❌ 复用同一个实例会导致会话混淆
        return await self.agent(msgs)
```

### 示例代码

查看 [`examples/react_agent_best_practices.py`](./react_agent_best_practices.py) 获取完整示例。

### 详细文档

- [中文文档](../cookbook/zh/react_agent.md#reactagent-复用最佳实践)
- [English Documentation](../cookbook/en/react_agent.md#reactagent-reuse-best-practices)

---

## English

### The Question

When using AgentScope Runtime, developers often ask:

> **Should I create a new ReActAgent for every `@agent_app.query(framework="agentscope")` call, or can I reuse it?**

### The Answer

**It is recommended to create a new ReActAgent instance for each request** rather than reusing the same instance.

### Why?

1. **Session Isolation**: Ensures complete state isolation between different users and sessions
2. **State Management Safety**: Avoids state races in concurrent scenarios
3. **Clear Memory Management**: Automatic garbage collection prevents memory leaks
4. **Configuration Flexibility**: Each request can have different toolsets and configurations

### Best Practices

#### ✅ Recommended Pattern: Create New Instance Per Request

```python
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    # 1. Load previous state
    state = await self.state_service.export_state(
        session_id=request.session_id,
        user_id=request.user_id,
    )
    
    # 2. Create new Agent instance
    agent = ReActAgent(...)
    
    # 3. Restore state
    if state:
        agent.load_state_dict(state)
    
    # 4. Process request
    async for msg, last in stream_printing_messages(...):
        yield msg, last
    
    # 5. Save state
    await self.state_service.save_state(...)
```

#### ✅ Components That Should Be Reused

Initialize and reuse in `@agent_app.init`:

- `StateService`: State management service
- `SessionHistoryService`: Session history service
- `SandboxService`: Sandbox service
- Database connection pools
- Redis connections
- External API clients

```python
@agent_app.init
async def init_func(self):
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    self.sandbox_service = SandboxService()
    
    await self.state_service.start()
    await self.session_service.start()
    await self.sandbox_service.start()
```

#### ❌ Not Recommended: Reusing Agent Instances

```python
# ❌ Don't do this!
class BadExample:
    def __init__(self):
        self.agent = ReActAgent(...)  # Don't create at class level
    
    @agent_app.query(framework="agentscope")
    async def query_func(self, msgs, request, **kwargs):
        # ❌ Reusing the same instance leads to session confusion
        return await self.agent(msgs)
```

### Example Code

See [`examples/react_agent_best_practices.py`](./react_agent_best_practices.py) for a complete example.

### Detailed Documentation

- [中文文档](../cookbook/zh/react_agent.md#reactagent-复用最佳实践)
- [English Documentation](../cookbook/en/react_agent.md#reactagent-reuse-best-practices)

---

## Key Takeaways / 核心要点

| Pattern / 模式 | Recommendation / 建议 | Reason / 原因 |
|---|---|---|
| ReActAgent instance<br/>ReActAgent 实例 | ✅ Create per request<br/>✅ 每次请求创建 | Session isolation, state safety<br/>会话隔离、状态安全 |
| StateService<br/>状态服务 | ✅ Reuse in @agent_app.init<br/>✅ 在 @agent_app.init 中复用 | Long-lived resource<br/>长生命周期资源 |
| SessionHistoryService<br/>会话历史服务 | ✅ Reuse in @agent_app.init<br/>✅ 在 @agent_app.init 中复用 | Long-lived resource<br/>长生命周期资源 |
| SandboxService<br/>沙箱服务 | ✅ Reuse in @agent_app.init<br/>✅ 在 @agent_app.init 中复用 | Long-lived resource<br/>长生命周期资源 |
| Sharing agent across sessions<br/>跨会话共享 agent | ❌ Avoid<br/>❌ 避免 | State confusion, race conditions<br/>状态混淆、竞态条件 |

---

## Testing / 测试

You can test the best practices example by running:

```bash
# Set your API key
export DASHSCOPE_API_KEY="your_api_key_here"

# Run the example
python examples/react_agent_best_practices.py

# In another terminal, test the endpoint
curl -N -X POST "http://127.0.0.1:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [
          { "type": "text", "text": "What is the capital of France?" }
        ]
      }
    ]
  }'
```

For multi-turn conversation testing (to verify state persistence):

```bash
# First turn - introduce yourself
curl -N -X POST "http://127.0.0.1:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [{ "type": "text", "text": "My name is Alice." }]
      }
    ],
    "session_id": "test-session-123"
  }'

# Second turn - ask agent to recall your name
curl -N -X POST "http://127.0.0.1:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [{ "type": "text", "text": "What is my name?" }]
      }
    ],
    "session_id": "test-session-123"
  }'
```

If the agent correctly recalls "Alice", it confirms that:
1. State is properly persisted across requests
2. A new agent instance is created for each request
3. The state is successfully restored to the new instance

如果 agent 正确回忆起 "Alice"，则证明：
1. 状态在请求间正确持久化
2. 每次请求都创建了新的 agent 实例
3. 状态成功恢复到新实例中
