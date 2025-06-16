#!/usr/bin/env python3
"""
Simple MCP Server for testing - minimal implementation
This should definitely work to verify the MCP setup
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import mcp.types as types

# Configure logging to file only (not stdout)
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'simple-mcp-server.log')
    ]
)
logger = logging.getLogger(__name__)

class SimpleMCPServer:
    """Simple MCP server for testing"""
    
    def __init__(self):
        self.server = Server("simple-test-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup basic MCP handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="test://sample",
                    name="Sample Resource",
                    description="A sample resource for testing",
                    mimeType="text/plain"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "test://sample":
                return "This is sample resource content from the MCP server!"
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="echo",
                    description="Echo back the input text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to echo back"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="add_numbers",
                    description="Add two numbers together",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number",
                                "description": "First number"
                            },
                            "b": {
                                "type": "number", 
                                "description": "Second number"
                            }
                        },
                        "required": ["a", "b"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "echo":
                    text = arguments.get("text", "")
                    return [types.TextContent(
                        type="text",
                        text=f"Echo: {text}"
                    )]
                elif name == "add_numbers":
                    a = arguments.get("a", 0)
                    b = arguments.get("b", 0)
                    result = a + b
                    return [types.TextContent(
                        type="text",
                        text=f"Result: {a} + {b} = {result}"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Simple MCP Server")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="simple-test-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities=None
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        server = SimpleMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()