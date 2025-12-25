# Stream Parameter Support in /process Endpoint

## Summary

This implementation adds support for the `stream` parameter in the `/process` endpoint, allowing clients to request non-streaming JSON responses by setting `stream: false` in their requests.

## Problem Statement

Previously, the `/process` endpoint only supported Server-Sent Events (SSE) streaming responses. The question was: **"When using the http://localhost:8090/process endpoint, can stream: false be used to set non-streaming responses?"**

**Answer:** Yes! This implementation adds that capability.

## Implementation Details

### 1. Code Changes

**File:** `src/agentscope_runtime/engine/deployers/utils/service_utils/fastapi_factory.py`

#### Modified `_add_routes()` method:
- The `agent_api` endpoint handler now checks the `stream` parameter from the request
- Returns `StreamingResponse` when `stream=true` or when not specified (default)
- Returns `JSONResponse` when `stream=false`

#### Added `_collect_agent_response()` method:
- Collects all streaming events from `runner.stream_query()`
- Returns the final event as a complete JSON response
- Handles both custom functions and runner-based queries
- Includes proper error handling

### 2. Request/Response Behavior

#### Streaming Response (default)
```json
// Request
{
  "input": [...],
  "stream": true  // Optional, this is the default
}

// Response: Server-Sent Events (SSE)
// Content-Type: text/event-stream
data: {"status": "in_progress", ...}
data: {"status": "completed", "output": [...]}
data: [DONE]
```

#### Non-Streaming Response (new feature)
```json
// Request
{
  "input": [...],
  "stream": false  // Request non-streaming
}

// Response: Single JSON object
// Content-Type: application/json
{
  "status": "completed",
  "output": [
    {
      "role": "assistant",
      "content": [{"type": "text", "text": "..."}]
    }
  ],
  "session_id": "...",
  "usage": {...}
}
```

### 3. Backward Compatibility

- **Default behavior unchanged**: When `stream` is not specified, the endpoint defaults to `true` (streaming)
- **Existing clients**: All existing clients that don't specify `stream` will continue to work as before
- **New capability**: Clients can now opt-in to non-streaming by setting `stream: false`

## Testing

### Unit Tests
Added comprehensive tests in `tests/integrated/test_stream_parameter.py`:

1. **test_process_endpoint_stream_true**: Verifies streaming works with `stream=true`
2. **test_process_endpoint_stream_false**: Verifies non-streaming works with `stream=false`
3. **test_process_endpoint_default_stream**: Verifies default is streaming when `stream` is not specified

### Demo Script
Created `examples/stream_parameter_demo.py` to demonstrate usage.

## Documentation Updates

Updated both English and Chinese documentation:

### English (`cookbook/en/call.md`)
- Added "Controlling Response Streaming" section
- Explained the `stream` parameter
- Provided examples for both streaming and non-streaming requests

### Chinese (`cookbook/zh/call.md`)
- Added "控制响应流式输出" section
- Explained the `stream` parameter in Chinese
- Provided examples for both streaming and non-streaming requests

## Security Analysis

✅ **CodeQL scan completed**: No security vulnerabilities found

## Code Review

Addressed all code review feedback:
- Added clarifying comments about request parameter extraction
- Added explanation for event collection in non-streaming mode
- Fixed code style issues

## Usage Examples

### Python with aiohttp
```python
import aiohttp

# Non-streaming request
payload = {
    "input": [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Hello"}],
        },
    ],
    "stream": False,
}

async with aiohttp.ClientSession() as session:
    async with session.post(url, json=payload) as resp:
        data = await resp.json()
        print(data)
```

### curl
```bash
# Streaming (default)
curl -X POST http://localhost:8090/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello"}]
      }
    ]
  }'

# Non-streaming
curl -X POST http://localhost:8090/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello"}]
      }
    ],
    "stream": false
  }'
```

## Benefits

1. **Flexibility**: Users can choose between streaming and non-streaming based on their needs
2. **Simplicity**: Non-streaming responses are easier to parse for simple use cases
3. **Compatibility**: Matches the behavior of similar APIs (e.g., OpenAI's Response API)
4. **No Breaking Changes**: Existing code continues to work without modifications

## Related Files

### Modified Files
- `src/agentscope_runtime/engine/deployers/utils/service_utils/fastapi_factory.py`
- `cookbook/en/call.md`
- `cookbook/zh/call.md`

### New Files
- `tests/integrated/test_stream_parameter.py`
- `examples/stream_parameter_demo.py`
- `STREAM_PARAMETER_IMPLEMENTATION.md` (this file)

## Conclusion

This implementation successfully adds support for `stream: false` in the `/process` endpoint while maintaining full backward compatibility. The feature is well-tested, documented, and ready for production use.
