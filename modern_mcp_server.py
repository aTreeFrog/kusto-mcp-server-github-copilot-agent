#!/usr/bin/env python3
"""
Modern MCP Server compatible with mcp==1.9.4
Updated to use the latest MCP library API
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

# MCP imports for version 1.9.4
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging to file only
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'modern-mcp-server.log')
    ]
)
logger = logging.getLogger(__name__)

class ModernMCPServer:
    """Modern MCP server using latest API"""
    
    def __init__(self):
        self.server = Server("modern-test-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP handlers using modern API"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources"""
            return [
                types.Resource(
                    uri="test://sample",
                    name="Sample Resource",
                    description="A sample resource for testing",
                    mimeType="text/plain"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            logger.info(f"Reading resource: {uri}")
            if uri == "test://sample":
                return "This is sample resource content from the modern MCP server!"
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools"""
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
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any]
        ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls with modern return type"""
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
        """Run the MCP server using modern API"""
        logger.info("Starting Modern MCP Server")
        
        try:
            # Use the modern stdio_server context manager
            async with stdio_server() as streams:
                await self.server.run(*streams)
                
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        server = ModernMCPServer()
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