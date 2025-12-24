# Multi-Agent Deployment Examples

This directory contains examples demonstrating best practices for deploying multiple agents using AgentScope Runtime.

## 📚 Overview

These examples showcase three common deployment patterns:

1. **Simple Multi-Agent**: Sequential orchestration within a single AgentApp
2. **Collaborative Agents**: Manager-Worker pattern for task decomposition
3. **Parallel Agents**: Independent deployment of multiple AgentApps

## 📋 Prerequisites

- Python 3.10+
- AgentScope Runtime installed (`pip install agentscope-runtime`)
- DashScope API key (set as `DASHSCOPE_API_KEY` environment variable)

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

## 🚀 Examples

### Example 1: Simple Multi-Agent Orchestration

**File**: `simple_multi_agent.py`

Demonstrates sequential agent orchestration where an Analyst and Writer work together to process queries.

**Architecture**:
```
User Query → Analyst Agent → Writer Agent → Response
```

**Run**:
```bash
python simple_multi_agent.py
```

**Test**:
```bash
curl -N -X POST "http://localhost:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "What are the benefits of cloud computing?"}]
    }],
    "session_id": "demo-123"
  }'
```

**Key Features**:
- Single AgentApp with multiple agents
- Sequential processing pipeline
- Shared session history
- Memory persistence per agent

---

### Example 2: Collaborative Multi-Agent System

**File**: `collaborative_agents.py`

Implements a Manager-Worker pattern where a Manager coordinates Researcher and Coder agents.

**Architecture**:
```
                    Manager
                   /   |   \
                  /    |    \
           Researcher  |   Coder
                  \    |    /
                   \   |   /
                   Synthesis
```

**Run**:
```bash
python collaborative_agents.py
```

**Test**:
```bash
curl -N -X POST "http://localhost:8090/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "Create a Python function to calculate fibonacci numbers"}]
    }],
    "session_id": "collab-123"
  }'
```

**Key Features**:
- Task decomposition by Manager
- Specialized worker agents
- Result synthesis
- State management across all agents

---

### Example 3: Parallel Multi-Agent System

**Files**:
- `parallel_agent_analyzer.py` - Data analysis service (Port 8091)
- `parallel_agent_reporter.py` - Report generation service (Port 8092)
- `parallel_orchestrator.py` - Orchestration client

Demonstrates independent deployment of multiple agents as microservices.

**Architecture**:
```
Orchestrator → Analyzer Agent (8091) ─┐
            → Reporter Agent (8092) ─┼→ Combined Results
```

**Run**:
```bash
# Terminal 1: Start Analyzer
python parallel_agent_analyzer.py

# Terminal 2: Start Reporter
python parallel_agent_reporter.py

# Terminal 3: Run Orchestrator
python parallel_orchestrator.py
```

**Test Individual Services**:
```bash
# Test Analyzer
curl -N -X POST "http://localhost:8091/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "Analyze Q4 2024 sales data"}]
    }],
    "session_id": "test-123"
  }'

# Test Reporter
curl -N -X POST "http://localhost:8092/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{
      "role": "user",
      "content": [{"type": "text", "text": "Generate a report on cloud trends"}]
    }],
    "session_id": "test-123"
  }'
```

**Key Features**:
- Independent agent deployment
- HTTP-based communication
- Fault isolation
- Independent scaling
- Parallel and sequential workflows

---

## 📊 Comparison

| Pattern | Use Case | Pros | Cons |
|---------|----------|------|------|
| **Simple** | 2-5 agents, tight collaboration | Simple, low latency | Limited scalability |
| **Collaborative** | Task decomposition, specialized roles | Organized, maintainable | Single point of failure |
| **Parallel** | Large-scale, independent agents | Fault isolation, scalable | Complex, network latency |

## 🔧 Customization

### Using Redis for Distributed Deployment

For production deployments, replace `InMemorySessionHistoryService` with `RedisSessionHistoryService`:

```python
from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService

session_service = RedisSessionHistoryService(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
)
```

### Adding Custom Tools

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

### Integrating Sandbox

```python
from agentscope_runtime.sandbox import BrowserSandbox
from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter

@agent_app.init
async def init_func(self):
    self.sandbox = BrowserSandbox()
    self.sandbox.__enter__()
    
    # Wrap and register sandbox tools
    self.browser_tool = sandbox_tool_adapter(self.sandbox.browser_navigate)
    
@agent_app.shutdown
async def shutdown_func(self):
    self.sandbox.__exit__(None, None, None)
```

## 📈 Performance Tips

1. **Use async/await**: All examples use async for better concurrency
2. **Enable streaming**: Reduces perceived latency for users
3. **Connection pooling**: Configure Redis connection pools appropriately
4. **Worker processes**: Use `uvicorn --workers N` for CPU-bound tasks
5. **Caching**: Cache model instances and frequently used resources

## 🔒 Security Considerations

1. **API Key Management**: Use environment variables, never hardcode
2. **Input Validation**: Validate all user inputs
3. **Rate Limiting**: Implement rate limiting for production
4. **Authentication**: Add API key or OAuth for production endpoints

## 📖 Additional Resources

- [Best Practices Documentation (中文)](../../cookbook/zh/best_practices_multi_agent.md)
- [Best Practices Documentation (English)](../../cookbook/en/best_practices_multi_agent.md)
- [Deployment Guide](../../cookbook/en/deployment.md)
- [Service Documentation](../../cookbook/en/service/service.md)

## ❓ Troubleshooting

**Problem**: Connection refused when calling agents

**Solution**: Ensure agents are running on the expected ports. Check with:
```bash
curl http://localhost:8091/health
curl http://localhost:8092/health
```

**Problem**: Agent state lost between requests

**Solution**: Ensure session_id remains consistent across requests and StateService is properly initialized.

**Problem**: Out of memory errors

**Solution**: 
- Use Redis instead of in-memory services
- Implement proper cleanup in shutdown handlers
- Monitor memory usage and adjust resources

## 🤝 Contributing

Found an issue or have a suggestion? Please open an issue or submit a pull request!

## 📄 License

These examples are part of AgentScope Runtime and follow the same [Apache 2.0 License](../../LICENSE).
