---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3.10
  language: python
  name: python3
---

# 参考: 完整部署样例

本教程演示了如何使用AgentScope Runtime与[**AgentScope框架**](https://github.com/agentscope-ai/agentscope)创建和部署 *“推理与行动”(ReAct)* 智能体。

```{note}
ReAct（推理与行动）范式使智能体能够将推理轨迹与特定任务的行动交织在一起，使其在工具交互任务中特别有效。通过将AgentScope的`ReActAgent`与AgentScope Runtime的基础设施相结合，您可以同时获得智能决策和安全的工具执行。
```

## 前置要求

### 安装依赖

```bash
pip install agentscope-runtime
```

### 沙箱

```{note}
确保您的浏览器沙箱环境已准备好使用，详细信息请参见{doc}`sandbox/sandbox`。
```

确保浏览器沙箱镜像可用：

```bash
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest agentscope/runtime-sandbox-browser:latest
```

### API密钥配置

您需要为您选择的LLM提供商准备API密钥。此示例使用DashScope（Qwen），但您可以将其适配到其他提供商：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

## 分步实现

### 步骤 1：导入依赖

```{code-cell}
import os

from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit, execute_python_code
from agentscope.pipeline import stream_printing_messages

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import InMemorySessionHistoryService
from agentscope_runtime.engine.services.sandbox import SandboxService
from agentscope_runtime.sandbox import BrowserSandbox
```

### 步骤 2：准备浏览器沙箱工具

与 `tests/sandbox/test_sandbox.py` 相同，我们可以直接通过上下文管理器验证浏览器沙箱是否可用：

```{code-cell}
with BrowserSandbox() as box:
    print(box.list_tools())
    print(box.browser_navigate("https://www.example.com/"))
    print(box.browser_snapshot())
```

当需要在服务内长期复用沙箱时，参考 `tests/sandbox/test_sandbox_service.py` 使用 `SandboxService` 管理生命周期：

```{code-cell}
import asyncio

async def bootstrap_browser_sandbox():
    sandbox_service = SandboxService()
    await sandbox_service.start()

    session_id = "demo_session"
    user_id = "demo_user"

    sandboxes = sandbox_service.connect(
        session_id=session_id,
        user_id=user_id,
        sandbox_types=["browser"],
    )
    browser_box = sandboxes[0]
    browser_box.browser_navigate("https://www.example.com/")
    browser_box.browser_snapshot()

    await sandbox_service.stop()

asyncio.run(bootstrap_browser_sandbox())
```
这里的 `sandbox_types=["browser"]` 与 `tests/sandbox/test_sandbox_service.py` 保持一致，可确保同一 `session_id` / `user_id` 复用同一个浏览器沙箱实例。

### 步骤 3：构建 AgentApp

```{important}
⚠️ **提示**

此处的 Agent 构建（模型、工具、会话记忆、格式化器等）只是一个示例配置，
您需要根据实际需求替换为自己的模块实现。
关于可用的服务类型、适配器用法以及如何替换，请参考 {doc}`service/service`。
```

下面的逻辑与测试用例 `run_app()` 完全一致，包含状态服务初始化、会话记忆以及流式响应：

```{code-cell}
PORT = 8090

agent_app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant",
)


@agent_app.init
async def init_func(self):
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    self.sandbox_service = SandboxService()

    await self.state_service.start()
    await self.session_service.start()
    await self.sandbox_service.start()


@agent_app.shutdown
async def shutdown_func(self):
    await self.state_service.stop()
    await self.session_service.stop()
    await self.sandbox_service.stop()


@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id

    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )

    sandboxes = self.sandbox_service.connect(
        session_id=session_id,
        user_id=user_id,
        sandbox_types=["browser"],
    )
    browser_box = sandboxes[0]

    toolkit = Toolkit()
    for tool in (
        browser_box.browser_navigate,
        browser_box.browser_snapshot,
        browser_box.browser_take_screenshot,
        browser_box.browser_click,
        browser_box.browser_type,
    ):
        toolkit.register_tool_function(tool)
    toolkit.register_tool_function(execute_python_code)

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
    agent.set_console_output_enabled(enabled=False)

    if state:
        agent.load_state_dict(state)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=agent.state_dict(),
    )
```

上述 `query_func` 会将 Agent 的输出通过 SSE 逐条返回，同时把最新 state 写回内存服务，实现多轮记忆。

借助 `SandboxService`（`sandbox_types=["browser"]`） ，浏览器沙箱会根据同一个 `session_id`、`user_id` 在多轮对话中复用，避免重复启动容器。

### 步骤 4：启动服务

```{code-cell}
if __name__ == "__main__":
    agent_app.run(host="127.0.0.1", port=PORT)
```

运行脚本后即可在 `http://127.0.0.1:8090/process` 收到流式响应。

### 步骤 5：测试 SSE 输出

```bash
curl -N \
  -X POST "http://127.0.0.1:8090/process" \
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

你将看到多条 `data: {...}` 事件以及最终的 `data: [DONE]`。如果消息体中包含 “Paris” 即表示回答正确。

### 步骤 6：多轮记忆验证

要验证 `AgentScopeSessionHistoryMemory` 是否生效，可以复用测试中「两轮对话」的交互流程：第一次提交 “My name is Alice.” 并携带固定 `session_id`，第二次询问 “What is my name?”，若返回文本包含 “Alice” 即表示记忆成功。

### 步骤 7：OpenAI 兼容模式

AgentApp 同时暴露了 `compatible-mode/v1` 路径，可使用官方 `openai` SDK 验证：

```{code-cell}
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8090/compatible-mode/v1")
resp = client.responses.create(
    model="any_name",
    input="Who are you?",
)

print(resp.response["output"][0]["content"][0]["text"])
```

正常情况下你会得到 “I’m Friday ...” 之类的回答。

## 总结

通过本章节的内容，你可以快速获得一个带有流式响应、会话记忆以及 OpenAI 兼容接口的 ReAct 智能体服务。若需部署到远端或扩展更多工具，只需替换 `DashScopeChatModel`、状态服务或工具注册逻辑即可。

## ReActAgent 复用最佳实践

### 问题：每次请求都需要创建新的 ReActAgent 吗？

在 `@agent_app.query(framework="agentscope")` 方法中，**建议每次请求都创建新的 ReActAgent 实例**，而不是复用同一个实例。这是当前推荐的最佳实践，原因如下：

### 为什么要每次创建新实例？

1. **会话隔离性**：每个请求可能来自不同的用户和会话，创建新实例确保不同请求之间的状态完全隔离，避免会话混淆。

2. **状态管理安全**：虽然 AgentScope 提供了 `state_dict()` 和 `load_state_dict()` 来管理状态，但在多并发场景下，复用同一实例可能导致状态竞争和不一致。

3. **内存管理清晰**：每次请求结束后，Python 的垃圾回收机制会自动清理未引用的 Agent 实例，避免内存泄漏。

4. **工具和配置灵活**：不同请求可能需要不同的工具集、提示词或模型配置，创建新实例提供了最大的灵活性。

### 推荐模式：每次请求创建新实例

```python
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id
    
    # 1. 从状态服务加载之前的状态
    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )
    
    # 2. 每次请求创建新的 Agent 实例
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
    
    # 3. 如果存在之前的状态，恢复到新实例中
    if state:
        agent.load_state_dict(state)
    
    # 4. 处理请求
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
    
    # 5. 保存状态供下次使用
    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=agent.state_dict(),
    )
```

### 什么可以复用？

虽然 ReActAgent 实例不应复用，但以下组件**可以且应该**在 `@agent_app.init` 中初始化并复用：

1. **服务实例**：
   - `StateService`：状态管理服务
   - `SessionHistoryService`：会话历史服务
   - `SandboxService`：沙箱服务

2. **长生命周期资源**：
   - 数据库连接池
   - Redis 连接
   - 外部 API 客户端

```python
@agent_app.init
async def init_func(self):
    # ✅ 这些服务应该在初始化时创建并复用
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    self.sandbox_service = SandboxService()
    
    await self.state_service.start()
    await self.session_service.start()
    await self.sandbox_service.start()
```

### 高级场景：Agent 实例池（不推荐）

在某些极端性能优化场景下，你可能考虑实现 Agent 实例池来复用实例。但这需要：

- 实现完善的状态重置机制
- 处理并发安全问题
- 实现实例锁定和释放逻辑
- 额外的复杂度管理

**对于绝大多数应用场景，每次创建新实例的开销是可以接受的**，且能获得更好的代码可维护性和稳定性。

### 性能优化建议

如果担心创建 Agent 实例的性能开销，可以优化：

1. **延迟加载模型**：某些模型 SDK 支持连接池或缓存机制
2. **优化工具初始化**：工具实例可以预先创建并在多个 Agent 间共享（只读工具）
3. **使用更快的状态序列化**：优化 `state_dict()` 和 `load_state_dict()` 的性能
4. **异步初始化**：利用异步特性并行初始化多个组件

### 总结

- ✅ **推荐**：每次 `@agent_app.query()` 调用都创建新的 ReActAgent 实例
- ✅ **推荐**：在 `@agent_app.init` 中初始化并复用服务实例（StateService、SessionHistoryService、SandboxService）
- ✅ **推荐**：通过 StateService 在请求间持久化和恢复 Agent 状态
- ⚠️ **不推荐**：在多个请求间复用同一个 ReActAgent 实例
- ❌ **避免**：在没有适当状态隔离的情况下跨会话共享 Agent 实例

这种模式确保了会话隔离、状态一致性和代码的可维护性，是 AgentScope Runtime 的推荐实践。
