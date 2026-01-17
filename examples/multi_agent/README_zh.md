# 多智能体部署示例

本目录包含使用 AgentScope Runtime 部署多个智能体的最佳实践示例。

## 📚 概述

这些示例展示了三种常见的部署模式:

1. **简单多智能体**: 在单个 AgentApp 中顺序编排
2. **协作型智能体**: Manager-Worker 模式的任务分解
3. **并行智能体**: 多个 AgentApp 的独立部署

## 📋 前提条件

- Python 3.10+
- 已安装 AgentScope Runtime (`pip install agentscope-runtime`)
- DashScope API 密钥 (设置为 `DASHSCOPE_API_KEY` 环境变量)

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

## 🚀 示例

### 示例 1: 简单多智能体编排

**文件**: `simple_multi_agent.py`

演示顺序智能体编排，其中分析师和写作智能体协同处理查询。

**架构**:
```
用户查询 → 分析师智能体 → 写作智能体 → 响应
```

**运行**:
```bash
python simple_multi_agent.py
```

**测试**:
```bash
curl -N -X POST "http://localhost:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "云计算有哪些好处?"}]
    }],
    "session_id": "demo-123"
  }'
```

**主要特性**:
- 单个 AgentApp 包含多个智能体
- 顺序处理流水线
- 共享会话历史
- 每个智能体的记忆持久化

---

### 示例 2: 协作型多智能体系统

**文件**: `collaborative_agents.py`

实现 Manager-Worker 模式，其中 Manager 协调 Researcher 和 Coder 智能体。

**架构**:
```
                    Manager
                   /   |   \
                  /    |    \
           Researcher  |   Coder
                  \    |    /
                   \   |   /
                   综合结果
```

**运行**:
```bash
python collaborative_agents.py
```

**测试**:
```bash
curl -N -X POST "http://localhost:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "创建一个计算斐波那契数的 Python 函数"}]
    }],
    "session_id": "collab-123"
  }'
```

**主要特性**:
- Manager 进行任务分解
- 专业化的 Worker 智能体
- 结果综合
- 所有智能体的状态管理

---

### 示例 3: 并行多智能体系统

**文件**:
- `parallel_agent_analyzer.py` - 数据分析服务 (端口 8091)
- `parallel_agent_reporter.py` - 报告生成服务 (端口 8092)
- `parallel_orchestrator.py` - 编排客户端

演示多个智能体作为微服务的独立部署。

**架构**:
```
编排器 → 分析智能体 (8091) ─┐
      → 报告智能体 (8092) ─┼→ 综合结果
```

**运行**:
```bash
# 终端 1: 启动分析智能体
python parallel_agent_analyzer.py

# 终端 2: 启动报告智能体
python parallel_agent_reporter.py

# 终端 3: 运行编排器
python parallel_orchestrator.py
```

**测试单个服务**:
```bash
# 测试分析智能体
curl -N -X POST "http://localhost:8091/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "分析 2024 年第四季度销售数据"}]
    }],
    "session_id": "test-123"
  }'

# 测试报告智能体
curl -N -X POST "http://localhost:8092/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "生成云技术趋势报告"}]
    }],
    "session_id": "test-123"
  }'
```

**主要特性**:
- 独立的智能体部署
- 基于 HTTP 的通信
- 故障隔离
- 独立扩展
- 并行和顺序工作流

---

## 📊 对比

| 模式 | 使用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **简单** | 2-5个智能体，紧密协作 | 简单，低延迟 | 扩展性有限 |
| **协作型** | 任务分解，专业化角色 | 有组织，可维护 | 单点故障 |
| **并行** | 大规模，独立智能体 | 故障隔离，可扩展 | 复杂，网络延迟 |

## 🔧 自定义

### 使用 Redis 进行分布式部署

对于生产部署，将 `InMemorySessionHistoryService` 替换为 `RedisSessionHistoryService`:

```python
from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService

session_service = RedisSessionHistoryService(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
)
```

### 添加自定义工具

```python
from agentscope.tool import Toolkit

toolkit = Toolkit()
toolkit.register_tool_function(your_custom_tool)

agent = ReActAgent(
    name="Agent",
    model=model,
    toolkit=toolkit,
    ...
)
```

### 集成沙箱

```python
from agentscope_runtime.sandbox import BrowserSandbox
from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter

@agent_app.init
async def init_func(self):
    self.sandbox = BrowserSandbox()
    self.sandbox.__enter__()
    
    # 包装和注册沙箱工具
    self.browser_tool = sandbox_tool_adapter(self.sandbox.browser_navigate)
    
@agent_app.shutdown
async def shutdown_func(self):
    self.sandbox.__exit__(None, None, None)
```

## 📈 性能提示

1. **使用 async/await**: 所有示例都使用异步以获得更好的并发性
2. **启用流式传输**: 减少用户感知延迟
3. **连接池**: 适当配置 Redis 连接池
4. **工作进程**: 使用 `uvicorn --workers N` 处理 CPU 密集型任务
5. **缓存**: 缓存模型实例和常用资源

## 🔒 安全注意事项

1. **API 密钥管理**: 使用环境变量，永不硬编码
2. **输入验证**: 验证所有用户输入
3. **速率限制**: 为生产环境实现速率限制
4. **身份验证**: 为生产端点添加 API 密钥或 OAuth

## 📖 其他资源

- [最佳实践文档 (中文)](../../cookbook/zh/best_practices_multi_agent.md)
- [最佳实践文档 (English)](../../cookbook/en/best_practices_multi_agent.md)
- [部署指南](../../cookbook/zh/deployment.md)
- [服务文档](../../cookbook/zh/service/service.md)

## ❓ 故障排查

**问题**: 调用智能体时连接被拒绝

**解决方案**: 确保智能体在预期端口上运行。检查:
```bash
curl http://localhost:8091/health
curl http://localhost:8092/health
```

**问题**: 请求间智能体状态丢失

**解决方案**: 确保请求间 session_id 保持一致，且 StateService 正确初始化。

**问题**: 内存不足错误

**解决方案**: 
- 使用 Redis 替代内存服务
- 在 shutdown 处理器中实现适当的清理
- 监控内存使用并调整资源

## 🤝 贡献

发现问题或有建议？请提交 issue 或 pull request！

## 📄 许可证

这些示例是 AgentScope Runtime 的一部分，遵循相同的 [Apache 2.0 许可证](../../LICENSE)。
