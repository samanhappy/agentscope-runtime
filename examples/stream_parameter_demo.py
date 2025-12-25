#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration script showing how to use stream=false with the /process endpoint.

This script demonstrates:
1. Creating a simple AgentApp
2. Making a request with stream=true (default, SSE streaming)
3. Making a request with stream=false (non-streaming JSON response)

Note: This is a demonstration of the API, not a runnable example without
proper dependencies and API keys.
"""

import aiohttp
import asyncio
import json


async def test_streaming_response():
    """Test with stream=true (default behavior)."""
    url = "http://localhost:8090/process"
    
    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello, how are you?"}
                ],
            },
        ],
        "stream": True,  # Optional - this is the default
    }
    
    print("=" * 60)
    print("Testing STREAMING response (stream=true):")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            print(f"Status: {resp.status}")
            print(f"Content-Type: {resp.headers.get('Content-Type')}")
            print("\nStreaming events:")
            
            async for chunk, _ in resp.content.iter_chunks():
                if not chunk:
                    continue
                
                line = chunk.decode("utf-8").strip()
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        print("Stream completed: [DONE]")
                        break
                    
                    try:
                        event = json.loads(data_str)
                        print(f"Event: {json.dumps(event, indent=2)}")
                    except json.JSONDecodeError:
                        continue


async def test_non_streaming_response():
    """Test with stream=false (new feature)."""
    url = "http://localhost:8090/process"
    
    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello, how are you?"}
                ],
            },
        ],
        "stream": False,  # Request non-streaming response
    }
    
    print("\n" + "=" * 60)
    print("Testing NON-STREAMING response (stream=false):")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            print(f"Status: {resp.status}")
            print(f"Content-Type: {resp.headers.get('Content-Type')}")
            
            # Parse the complete JSON response
            data = await resp.json()
            print("\nComplete response:")
            print(json.dumps(data, indent=2))


async def main():
    """Run both tests."""
    print("\nDemonstration: stream parameter in /process endpoint")
    print("=" * 60)
    print("\nThis script demonstrates how to use the stream parameter:")
    print("- stream=true (default): Server-Sent Events (SSE)")
    print("- stream=false (new): Single JSON response")
    print("\nNote: Requires a running AgentApp on localhost:8090")
    print("=" * 60)
    
    try:
        # Test streaming
        await test_streaming_response()
        
        # Test non-streaming
        await test_non_streaming_response()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        
    except aiohttp.ClientConnectorError:
        print("\n❌ Error: Cannot connect to http://localhost:8090")
        print("Please make sure an AgentApp is running on port 8090")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   AgentScope Runtime - stream Parameter Demo           ║
    ║                                                          ║
    ║   This demonstrates the new stream=false feature        ║
    ║   for the /process endpoint                             ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())
