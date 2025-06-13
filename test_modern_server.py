#!/usr/bin/env python3
"""
Test the working MCP server
"""

import asyncio
import json
import subprocess
import sys

async def test_working_server():
    """Test the working MCP server"""
    print("🧪 Testing Working MCP Server...")
    print("="*40)
    
    # Start the server
    process = await asyncio.create_subprocess_exec(
        sys.executable, "working_mcp_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        print("✅ Server process started")
        
        # Wait a moment for startup
        await asyncio.sleep(2)
        
        # Check if process is still running
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            print(f"❌ Process exited with code: {process.returncode}")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
        
        print("✅ Server is running")
        
        # Test sequence
        tests = [
            {
                "name": "Initialize",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"}
                    }
                }
            },
            {
                "name": "List Tools",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
            },
            {
                "name": "Echo Tool",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "echo",
                        "arguments": {"text": "Hello MCP World!"}
                    }
                }
            }
        ]
        
        for test in tests:
            print(f"\n📤 Running test: {test['name']}")
            
            # Send message
            msg_json = json.dumps(test['message']) + '\n'
            process.stdin.write(msg_json.encode())
            await process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(), 
                    timeout=10.0
                )
                
                if response_line:
                    response_text = response_line.decode().strip()
                    print(f"✅ Got response ({len(response_text)} chars)")
                    
                    # Parse JSON
                    try:
                        response_data = json.loads(response_text)
                        
                        if "result" in response_data:
                            result = response_data["result"]
                            if test['name'] == "Initialize":
                                server_info = result.get("serverInfo", {})
                                print(f"   Server: {server_info.get('name', 'Unknown')}")
                            elif test['name'] == "List Tools":
                                tools = result.get("tools", [])
                                print(f"   Found {len(tools)} tools: {[t['name'] for t in tools]}")
                            elif test['name'] == "Echo Tool":
                                content = result.get("content", [])
                                if content:
                                    print(f"   Echo result: {content[0].get('text', 'No text')}")
                        else:
                            print(f"   Unexpected response: {response_data}")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Invalid JSON: {e}")
                        print(f"   Raw: {response_text[:100]}")
                else:
                    print("❌ No response received")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ Response timeout")
                return False
        
        print("\n🎉 All tests passed! MCP server is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5)
            print("✅ Server terminated cleanly")
        except:
            process.kill()
            print("⚠️ Server killed forcefully")

if __name__ == "__main__":
    success = asyncio.run(test_working_server())
    if success:
        print("\n🎉 Working MCP server test passed!")
        print("Now we can adapt this pattern for the Kusto server!")
    else:
        print("\n❌ Working MCP server test failed!")
        sys.exit(1)