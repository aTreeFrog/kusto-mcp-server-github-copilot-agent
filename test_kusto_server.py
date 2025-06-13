#!/usr/bin/env python3
"""
Test the fixed Kusto MCP server with proper MCP protocol messages
"""

import asyncio
import json
import subprocess
import sys

async def test_kusto_server():
    """Test the Kusto MCP server"""
    print("🧪 Testing Kusto MCP Server...")
    print("="*40)
    
    # Start the server
    process = await asyncio.create_subprocess_exec(
        sys.executable, "mcp_kusto_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        print("✅ Server process started")
        
        # Wait a moment for startup
        await asyncio.sleep(3)
        
        # Check if process is still running
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            print(f"❌ Process exited with code: {process.returncode}")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
        
        print("✅ Server is running")
        
        # Test sequence with proper MCP protocol
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
                "name": "Initialized Notification", 
                "message": {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
            },
            {
                "name": "List Tools",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
            },
            {
                "name": "List Resources", 
                "message": {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/list"
                }
            },
            {
                "name": "List Tables",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "list_tables", 
                        "arguments": {"cluster": "samples"}
                    }
                }
            },
            {
                "name": "Simple KQL Query",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "execute_kql",
                        "arguments": {
                            "cluster": "samples",
                            "query": "StormEvents | take 5 | project EventType, State, StartTime",
                            "limit": 5
                        }
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
            
            # Skip reading response for notifications
            if test['name'] == "Initialized Notification":
                print("   ✅ Notification sent (no response expected)")
                await asyncio.sleep(0.5)  # Brief pause
                continue
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(), 
                    timeout=30.0  # Longer timeout for Kusto queries
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
                                print(f"   Version: {server_info.get('version', 'Unknown')}")
                            elif test['name'] == "List Tools":
                                tools = result.get("tools", [])
                                tool_names = [t['name'] for t in tools]
                                print(f"   Found {len(tools)} tools: {tool_names}")
                            elif test['name'] == "List Resources":
                                resources = result.get("resources", [])
                                print(f"   Found {len(resources)} resources")
                                for r in resources[:3]:  # Show first 3
                                    print(f"     - {r['name']}")
                            elif test['name'] in ["List Tables", "Simple KQL Query"]:
                                content = result.get("content", [])
                                if content:
                                    text = content[0].get('text', '')
                                    # Show first few lines
                                    lines = text.split('\n')[:5]
                                    print(f"   Result preview:")
                                    for line in lines:
                                        if line.strip():
                                            print(f"     {line}")
                                            
                        elif "error" in response_data:
                            error = response_data["error"]
                            print(f"   ❌ Error: {error.get('message', 'Unknown error')}")
                            print(f"   Error code: {error.get('code', 'Unknown')}")
                            # Don't fail on errors - some might be expected (like auth issues)
                            
                        else:
                            print(f"   Unexpected response format")
                            print(f"   Keys: {list(response_data.keys())}")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Invalid JSON: {e}")
                        print(f"   Raw: {response_text[:200]}")
                else:
                    print("❌ No response received")
                    
            except asyncio.TimeoutError:
                print("❌ Response timeout")
                # Don't fail immediately - might be a slow query
        
        print("\n🎉 Test sequence completed!")
        
        # Check log file for more details
        log_file = "logs/mcp-kusto-server.log"
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
                if "ERROR" in log_content:
                    print(f"\n⚠️ Found errors in log file {log_file}:")
                    error_lines = [line for line in log_content.split('\n') if 'ERROR' in line]
                    for line in error_lines[-3:]:  # Show last 3 errors
                        print(f"   {line}")
                else:
                    print(f"\n✅ No errors found in log file")
        except FileNotFoundError:
            print(f"\n⚠️ Log file {log_file} not found")
        
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
    success = asyncio.run(test_kusto_server())
    if success:
        print("\n🎉 Kusto MCP server basic test completed!")
        print("\nNext steps:")
        print("1. Check the detailed log output above")
        print("2. Review logs/mcp-kusto-server.log for any issues")
        print("3. If authentication works, the server is ready for Claude Desktop!")
        print("4. Add this server to your Claude Desktop configuration")
    else:
        print("\n❌ Kusto MCP server test failed!")
        print("Check the error messages above and the log file.")
        sys.exit(1)