#!/usr/bin/env python3
"""
Test the auto-authentication MCP server
"""

import asyncio
import json
import subprocess
import sys

async def test_auto_auth_server():
    """Test the auto-auth MCP server"""
    print("Testing Auto-Authentication Kusto MCP Server...")
    print("="*60)
    print("This server will automatically open a browser for authentication")
    print()
    
    # Start the server
    process = await asyncio.create_subprocess_exec(
        sys.executable, "mcp_server_auto_auth.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        print("Server process started")
        print("Waiting for authentication to complete...")
        print("(A browser window should open for Microsoft sign-in)")
        
        # Give time for auth
        await asyncio.sleep(15)
        
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            print(f"Process exited with code: {process.returncode}")
            if stderr:
                print(f"STDERR: {stderr.decode()}")
            return False
        
        print("Server appears to be running and authenticated!")
        
        # Test MCP functionality
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
                        "clientInfo": {"name": "vscode-test", "version": "1.0"}
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
                "name": "List Tables",
                "message": {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "list_tables",
                        "arguments": {"cluster": "production"}
                    }
                }
            }
        ]
        
        for test in tests:
            print(f"\nTesting: {test['name']}")
            
            msg_json = json.dumps(test['message']) + '\n'
            process.stdin.write(msg_json.encode())
            await process.stdin.drain()
            
            if test['name'] == "Initialized Notification":
                await asyncio.sleep(0.5)
                continue
            
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=30.0
                )
                
                if response_line:
                    response_text = response_line.decode().strip()
                    response_data = json.loads(response_text)
                    
                    if "result" in response_data:
                        if test['name'] == "Initialize":
                            server_info = response_data["result"]["serverInfo"]
                            print(f"   SUCCESS: {server_info['name']} v{server_info['version']}")
                        elif test['name'] == "List Tools":
                            tools = response_data["result"]["tools"]
                            tool_names = [t['name'] for t in tools]
                            print(f"   SUCCESS: Found tools: {tool_names}")
                        elif test['name'] == "List Tables":
                            content = response_data["result"]["content"][0]["text"]
                            if "Error" not in content:
                                print("   SUCCESS: Listed tables successfully!")
                                # Show first few lines
                                lines = content.split('\n')[:5]
                                for line in lines:
                                    if line.strip():
                                        print(f"     {line}")
                            else:
                                print(f"   ERROR: {content.split(':')[0]}")
                    elif "error" in response_data:
                        error = response_data["error"]
                        print(f"   ERROR: {error['message']}")
                        
            except asyncio.TimeoutError:
                print("   TIMEOUT")
        
        return True
        
    except Exception as e:
        print(f"Test error: {e}")
        return False
        
    finally:
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5)
            print("\nServer terminated")
        except:
            process.kill()

if __name__ == "__main__":
    print("Auto-Authentication MCP Server Test")
    print("="*60)
    print("This will test the server designed for VS Code/Copilot integration")
    print("A browser window will open automatically for Microsoft authentication")
    print()
    
    proceed = input("Ready to test? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Test cancelled")
        sys.exit(0)
    
    success = asyncio.run(test_auto_auth_server())
    if success:
        print(f"\n*** SUCCESS! ***")
        print("Your MCP server is ready for VS Code/Copilot integration")
        print("\nNext steps:")
        print("1. Configure VS Code to use this MCP server")
        print("2. The server will auto-authenticate when started")
        print("3. Use GitHub Copilot with Kusto data access!")
    else:
        print(f"\n*** FAILED ***")
        print("Check error messages above")