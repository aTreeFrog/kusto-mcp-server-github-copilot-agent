#!/usr/bin/env python3
"""
Working MCP Server for version 1.9.4
Uses the correct API signatures discovered through exploration
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

# MCP imports for version 1.9.4
from mcp.server import Server, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging to file only (not stdout - critical for MCP)
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'working-mcp-server.log')
    ]
)
logger = logging.getLogger(__name__)

class WorkingMCPServer:
    """Working MCP server using correct v1.9.4 API"""
    
    def __init__(self):
        self.server = Server("working-test-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP handlers using correct API"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources"""
            logger.info("Listing resources")
            return [
                types.Resource(
                    uri="test://sample",
                    name="Sample Resource",
                    description="A sample resource for testing",
                    mimeType="text/plain"
                ),
                types.Resource(
                    uri="test://data",
                    name="Sample Data",
                    description="Sample data resource",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            logger.info(f"Reading resource: {uri}")
            if uri == "test://sample":
                return "This is sample resource content from the working MCP server!"
            elif uri == "test://data":
                return json.dumps({"message": "Sample JSON data", "timestamp": "2024-01-01"})
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools"""
            logger.info("Listing tools")
            return [
                types.Tool(
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
                types.Tool(
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
                ),
                types.Tool(
                    name="get_time",
                    description="Get the current time",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any]
        ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            logger.info(f"Tool called: {name} with args: {arguments}")
            
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
                elif name == "get_time":
                    import datetime
                    current_time = datetime.datetime.now().isoformat()
                    return [types.TextContent(
                        type="text",
                        text=f"Current time: {current_time}"
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
        """Run the MCP server using correct v1.9.4 API"""
        logger.info("Starting Working MCP Server v1.9.4")
        
        try:
            # Use stdio_server with correct unpacking for v1.9.4
            async with stdio_server() as (read_stream, write_stream):
                # Use correct server.run signature with proper parameters
                await self.server.run(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    initialization_options=InitializationOptions(
                        server_name="working-test-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )
                
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        server = WorkingMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()