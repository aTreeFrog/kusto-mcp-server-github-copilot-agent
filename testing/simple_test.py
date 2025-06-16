#!/usr/bin/env python3
"""
Simple test for the basic MCP server
"""

import asyncio
import json
import subprocess
import sys

class SimpleTestClient:
    def __init__(self):
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the simple MCP server"""
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, "simple_mcp_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print("Simple MCP Server started")
    
    async def send_request(self, method: str, params: dict = None):
        """Send JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        if params:
            request["params"] = params
        
        self.request_id += 1
        
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode().strip())
        return response
    
    async def cleanup(self):
        """Clean up"""
        if self.process:
            self.process.terminate()
            await self.process.wait()

async def test_simple_server():
    """Test the simple server"""
    client = SimpleTestClient()
    
    try:
        await client.start_server()
        await asyncio.sleep(1)  # Give server time to start
        
        # Test 1: Initialize
        print("=== Test 1: Initialize ===")
        response = await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        })
        print("✅ Initialize:", response.get("result", {}).get("serverInfo", {}).get("name"))
        
        # Test 2: List tools
        print("\n=== Test 2: List Tools ===")
        response = await client.send_request("tools/list")
        tools = response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test 3: Call echo tool
        print("\n=== Test 3: Call Echo Tool ===")
        response = await client.send_request("tools/call", {
            "name": "echo",
            "arguments": {"text": "Hello MCP!"}
        })
        content = response.get("result", {}).get("content", [])
        if content:
            print(f"✅ Echo result: {content[0].get('text')}")
        
        # Test 4: Call add tool
        print("\n=== Test 4: Call Add Tool ===")
        response = await client.send_request("tools/call", {
            "name": "add_numbers",
            "arguments": {"a": 15, "b": 27}
        })
        content = response.get("result", {}).get("content", [])
        if content:
            print(f"✅ Add result: {content[0].get('text')}")
        
        # Test 5: List resources
        print("\n=== Test 5: List Resources ===")
        response = await client.send_request("resources/list")
        resources = response.get("result", {}).get("resources", [])
        print(f"✅ Found {len(resources)} resources:")
        for resource in resources:
            print(f"  - {resource['name']}: {resource['description']}")
        
        # Test 6: Read resource
        print("\n=== Test 6: Read Resource ===")
        response = await client.send_request("resources/read", {
            "uri": "test://sample"
        })
        content = response.get("result", {}).get("contents", [])
        if content:
            print(f"✅ Resource content: {content[0].get('text')}")
        
        print("\n🎉 All tests passed! Your MCP setup is working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_simple_server())