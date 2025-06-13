#!/usr/bin/env python3
"""
Simple test client for MCP Kusto Server
Tests the server functionality without needing a full AI client
Run this to verify your MCP server is working correctly
"""

import asyncio
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Any, Dict, List

class MCPTestClient:
    """Simple test client for MCP server"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the MCP server process"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print("MCP Server started")
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server"""
        if not self.process:
            raise RuntimeError("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        if params:
            request["params"] = params
        
        self.request_id += 1
        
        # Send request
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from server")
        
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            print(f"Failed to parse response: {response_line}")
            raise e
    
    async def initialize(self):
        """Initialize the MCP connection"""
        response = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        print("Initialize response:", json.dumps(response, indent=2))
        return response
    
    async def list_tools(self):
        """List available tools"""
        response = await self.send_request("tools/list")
        print("Available tools:", json.dumps(response, indent=2))
        return response
    
    async def list_resources(self):
        """List available resources"""
        response = await self.send_request("resources/list")
        print("Available resources:", json.dumps(response, indent=2))
        return response
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a specific tool"""
        response = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        print(f"Tool '{name}' response:", json.dumps(response, indent=2))
        return response
    
    async def read_resource(self, uri: str):
        """Read a specific resource"""
        response = await self.send_request("resources/read", {
            "uri": uri
        })
        print(f"Resource '{uri}' content:", json.dumps(response, indent=2))
        return response
    
    async def cleanup(self):
        """Clean up the server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()

async def run_tests():
    """Run a series of tests against the MCP server"""
    print("Starting MCP Kusto Server tests...")
    
    # Initialize test client
    client = MCPTestClient([sys.executable, "local_mcp_server.py"])
    
    try:
        # Start server
        await client.start_server()
        await asyncio.sleep(2)  # Give server time to start
        
        # Test 1: Initialize connection
        print("\n=== Test 1: Initialize ===")
        await client.initialize()
        
        # Test 2: List available tools
        print("\n=== Test 2: List Tools ===")
        tools_response = await client.list_tools()
        
        # Test 3: List available resources
        print("\n=== Test 3: List Resources ===")
        resources_response = await client.list_resources()
        
        # Test 4: Execute a simple KQL query
        print("\n=== Test 4: Execute KQL Query ===")
        await client.call_tool("execute_kql", {
            "cluster": "samples",
            "query": "StormEvents | take 5"
        })
        
        # Test 5: Get table schema
        print("\n=== Test 5: Get Table Schema ===")
        await client.call_tool("get_table_schema", {
            "cluster": "samples",
            "table": "StormEvents"
        })
        
        # Test 6: List databases
        print("\n=== Test 6: List Databases ===")
        await client.call_tool("list_databases", {
            "cluster": "samples"
        })
        
        # Test 7: Read a resource
        print("\n=== Test 7: Read Resource ===")
        await client.read_resource("kusto://samples/tables")
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.cleanup()

# Interactive test function
async def interactive_test():
    """Interactive testing mode"""
    client = MCPTestClient([sys.executable, "local_mcp_server.py"])
    
    try:
        await client.start_server()
        await asyncio.sleep(2)
        
        await client.initialize()
        
        while True:
            print("\nAvailable commands:")
            print("1. List tools")
            print("2. List resources") 
            print("3. Execute KQL query")
            print("4. Get table schema")
            print("5. List databases")
            print("6. Read resource")
            print("7. Exit")
            
            choice = input("\nEnter choice (1-7): ").strip()
            
            if choice == "1":
                await client.list_tools()
            elif choice == "2":
                await client.list_resources()
            elif choice == "3":
                cluster = input("Cluster name (default: samples): ").strip() or "samples"
                query = input("KQL query: ").strip()
                if query:
                    await client.call_tool("execute_kql", {
                        "cluster": cluster,
                        "query": query
                    })
            elif choice == "4":
                cluster = input("Cluster name (default: samples): ").strip() or "samples"
                table = input("Table name: ").strip()
                if table:
                    await client.call_tool("get_table_schema", {
                        "cluster": cluster,
                        "table": table
                    })
            elif choice == "5":
                cluster = input("Cluster name (default: samples): ").strip() or "samples"
                await client.call_tool("list_databases", {
                    "cluster": cluster
                })
            elif choice == "6":
                uri = input("Resource URI (e.g., kusto://samples/tables): ").strip()
                if uri:
                    await client.read_resource(uri)
            elif choice == "7":
                break
            else:
                print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(run_tests())