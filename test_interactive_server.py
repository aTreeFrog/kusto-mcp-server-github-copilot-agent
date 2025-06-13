#!/usr/bin/env python3
"""
MCP Server with interactive authentication for work/corporate Kusto clusters
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

from azure.identity import InteractiveBrowserCredential, DeviceCodeCredential, DefaultAzureCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from mcp.server import Server, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'interactive-mcp-kusto-server.log')
    ]
)
logger = logging.getLogger(__name__)

class InteractiveKustoMCPServer:
    """MCP Server with interactive authentication for corporate Kusto clusters"""
    
    def __init__(self):
        self.server = Server("interactive-kusto-mcp-server")
        self.kusto_clients: Dict[str, KustoClient] = {}
        self.credential = None
        self.cluster_configs = {}
        
        # Load configuration
        self._load_configuration()
        
        # Initialize Azure credentials with interactive auth
        self._initialize_interactive_credentials()
        
        # Setup MCP handlers
        self._setup_handlers()
    
    def _load_configuration(self):
        """Load Kusto cluster configurations"""
        config_file = os.getenv('KUSTO_CONFIG_FILE')
        if not config_file:
            possible_configs = [
                Path.home() / '.mcp-kusto' / 'config.json',
                Path(__file__).parent / 'config' / 'config.json',
                Path(__file__).parent / 'config.json'
            ]
            
            for config_path in possible_configs:
                if config_path.exists():
                    config_file = str(config_path)
                    break
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.cluster_configs = config.get('clusters', {})
                    logger.info(f"Loaded config from: {config_file}")
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
        
        # Environment variable fallback
        cluster_url = os.getenv('KUSTO_CLUSTER_URL')
        if cluster_url:
            cluster_name = os.getenv('KUSTO_CLUSTER_NAME', 'default')
            self.cluster_configs[cluster_name] = {
                'url': cluster_url,
                'database': os.getenv('KUSTO_DATABASE', 'MyDatabase')
            }
            logger.info(f"Added cluster from environment: {cluster_name}")
        
        # Default to samples cluster if nothing configured
        if not self.cluster_configs:
            self.cluster_configs['samples'] = {
                'url': 'https://help.kusto.windows.net',
                'database': 'Samples'
            }
            logger.info("Using default samples cluster configuration")
        
        logger.info(f"Configured clusters: {list(self.cluster_configs.keys())}")
    
    def _initialize_interactive_credentials(self):
        """Initialize Azure credentials with interactive authentication"""
        logger.info("Initializing interactive authentication for corporate Kusto clusters")
        
        # Try different authentication methods in order of preference
        auth_methods = [
            {
                'name': 'Device Code Authentication',
                'credential': lambda: DeviceCodeCredential(
                    authority="https://login.microsoftonline.com/common",
                    # This will prompt user to visit aka.ms/devicelogin
                )
            },
            {
                'name': 'Interactive Browser Authentication', 
                'credential': lambda: InteractiveBrowserCredential(
                    authority="https://login.microsoftonline.com/common",
                    # This opens a browser window
                )
            },
            {
                'name': 'Default Azure Credential',
                'credential': lambda: DefaultAzureCredential()
            }
        ]
        
        for auth_method in auth_methods:
            try:
                logger.info(f"Trying {auth_method['name']}...")
                self.credential = auth_method['credential']()
                
                # Test the credential
                token = self.credential.get_token("https://kusto.kusto.windows.net/.default")
                logger.info(f"✅ Successfully authenticated using {auth_method['name']}")
                logger.info(f"Token expires: {token.expires_on}")
                return
                
            except Exception as e:
                logger.warning(f"{auth_method['name']} failed: {e}")
                continue
        
        # If all methods fail
        logger.error("All authentication methods failed")
        raise RuntimeError(
            "Could not authenticate to Azure. Please ensure you can sign in with your work account."
        )
    
    def _get_kusto_client(self, cluster_name: str = 'default') -> KustoClient:
        """Get or create Kusto client for specified cluster"""
        if cluster_name not in self.kusto_clients:
            if cluster_name not in self.cluster_configs:
                available = list(self.cluster_configs.keys())
                if available:
                    logger.warning(f"Cluster '{cluster_name}' not found, using '{available[0]}'")
                    cluster_name = available[0]
                else:
                    raise ValueError(f"No clusters configured")
            
            config = self.cluster_configs[cluster_name]
            cluster_url = config['url']
            
            try:
                # For corporate clusters, we need authenticated connection
                logger.info(f"Creating authenticated connection to: {cluster_url}")
                
                # Get a fresh token
                token = self.credential.get_token("https://kusto.kusto.windows.net/.default")
                
                # Try different connection methods based on available API
                if hasattr(KustoConnectionStringBuilder, 'with_aad_application_token_authentication'):
                    kcsb = KustoConnectionStringBuilder.with_aad_application_token_authentication(
                        cluster_url,
                        application_token=token.token
                    )
                    logger.info("Using AAD application token authentication")
                    
                elif hasattr(KustoConnectionStringBuilder, 'with_aad_device_authentication'):
                    kcsb = KustoConnectionStringBuilder.with_aad_device_authentication(
                        cluster_url,
                        authority_id="common"
                    )
                    logger.info("Using AAD device authentication")
                    
                elif hasattr(KustoConnectionStringBuilder, 'with_aad_user_authentication'):
                    kcsb = KustoConnectionStringBuilder.with_aad_user_authentication(
                        cluster_url,
                        user_id="", # Let it auto-detect
                        authority_id="common"
                    )
                    logger.info("Using AAD user authentication")
                    
                else:
                    # Fallback - this might work for some clusters
                    kcsb = KustoConnectionStringBuilder(cluster_url)
                    logger.info("Using basic connection string (might require manual auth)")
                
            except Exception as e:
                logger.error(f"Failed to create connection: {e}")
                raise
            
            self.kusto_clients[cluster_name] = KustoClient(kcsb)
            logger.info(f"Created Kusto client for cluster: {cluster_name} ({cluster_url})")
        
        return self.kusto_clients[cluster_name]
    
    def _setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available Kusto resources"""
            resources = []
            
            for cluster_name, config in self.cluster_configs.items():
                resources.extend([
                    types.Resource(
                        uri=f"kusto://{cluster_name}/tables",
                        name=f"Tables in {cluster_name}",
                        description=f"List of tables in Kusto cluster {cluster_name}",
                        mimeType="application/json"
                    ),
                    types.Resource(
                        uri=f"kusto://{cluster_name}/functions",
                        name=f"Functions in {cluster_name}",
                        description=f"List of functions in Kusto cluster {cluster_name}",
                        mimeType="application/json"
                    )
                ])
            
            return resources
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read Kusto resource content"""
            try:
                if not uri.startswith("kusto://"):
                    raise ValueError(f"Unsupported URI scheme: {uri}")
                
                parts = uri.replace("kusto://", "").split("/")
                if len(parts) < 2:
                    raise ValueError(f"Invalid URI format: {uri}")
                
                cluster_name = parts[0]
                resource_type = parts[1]
                
                client = self._get_kusto_client(cluster_name)
                database = self.cluster_configs[cluster_name]['database']
                
                if resource_type == "tables":
                    query = ".show tables | project TableName"
                elif resource_type == "functions":
                    query = ".show functions | project Name, Parameters"
                else:
                    raise ValueError(f"Unsupported resource type: {resource_type}")
                
                response = client.execute(database, query)
                results = []
                
                if response.primary_results and len(response.primary_results) > 0:
                    primary_result = response.primary_results[0]
                    column_names = [col.column_name for col in primary_result.columns]
                    
                    for row in primary_result:
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            if i < len(row):
                                row_dict[col_name] = str(row[i]) if row[i] is not None else None
                        results.append(row_dict)
                
                return json.dumps(results, indent=2)
                
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available Kusto tools"""
            available_clusters = list(self.cluster_configs.keys())
            return [
                types.Tool(
                    name="execute_kql",
                    description="Execute a KQL (Kusto Query Language) query against a corporate Kusto cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "samples"
                            },
                            "database": {
                                "type": "string",
                                "description": "Database name (optional, uses configured default)"
                            },
                            "query": {
                                "type": "string",
                                "description": "KQL query to execute"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of rows to return",
                                "default": 1000
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_table_schema",
                    description="Get the schema of a specific table in Kusto",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "samples"
                            },
                            "database": {
                                "type": "string",
                                "description": "Database name (optional, uses configured default)"
                            },
                            "table": {
                                "type": "string",
                                "description": "Table name to get schema for"
                            }
                        },
                        "required": ["table"]
                    }
                ),
                types.Tool(
                    name="list_tables",
                    description="List all tables in a Kusto database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "samples"
                            },
                            "database": {
                                "type": "string",
                                "description": "Database name (optional, uses configured default)"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any]
        ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            try:
                if name == "execute_kql":
                    return await self._execute_kql_tool(arguments)
                elif name == "get_table_schema":
                    return await self._get_table_schema_tool(arguments)
                elif name == "list_tables":
                    return await self._list_tables_tool(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]
    
    async def _execute_kql_tool(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute KQL query"""
        cluster_name = arguments.get('cluster', list(self.cluster_configs.keys())[0])
        database = arguments.get('database') or self.cluster_configs[cluster_name]['database']
        query = arguments['query']
        limit = arguments.get('limit', 1000)
        
        if 'limit' not in query.lower() and 'take' not in query.lower():
            query = f"{query} | limit {limit}"
        
        client = self._get_kusto_client(cluster_name)
        
        try:
            logger.info(f"Executing query on {cluster_name}/{database}: {query}")
            response = client.execute(database, query)
            results = []
            
            if response.primary_results and len(response.primary_results) > 0:
                primary_result = response.primary_results[0]
                column_names = [col.column_name for col in primary_result.columns]
                
                for row in primary_result:
                    row_dict = {}
                    for i, col_name in enumerate(column_names):
                        if i < len(row):
                            row_dict[col_name] = str(row[i]) if row[i] is not None else None
                    results.append(row_dict)
            
            result_text = f"Query executed successfully on cluster '{cluster_name}', database '{database}'.\n"
            result_text += f"Returned {len(results)} rows.\n\n"
            result_text += f"Query: {query}\n\n"
            result_text += "Results:\n"
            result_text += json.dumps(results, indent=2, default=str)
            
            return [types.TextContent(type="text", text=result_text)]
            
        except KustoServiceError as e:
            error_msg = f"Kusto query error on cluster '{cluster_name}': {e}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    async def _get_table_schema_tool(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get table schema"""
        cluster_name = arguments.get('cluster', list(self.cluster_configs.keys())[0])
        database = arguments.get('database') or self.cluster_configs[cluster_name]['database']
        table = arguments['table']
        
        client = self._get_kusto_client(cluster_name)
        query = f".show table {table} schema as json"
        
        try:
            logger.info(f"Getting schema for table '{table}' on {cluster_name}/{database}")
            response = client.execute(database, query)
            results = []
            
            if response.primary_results and len(response.primary_results) > 0:
                primary_result = response.primary_results[0]
                column_names = [col.column_name for col in primary_result.columns]
                
                for row in primary_result:
                    row_dict = {}
                    for i, col_name in enumerate(column_names):
                        if i < len(row):
                            row_dict[col_name] = str(row[i]) if row[i] is not None else None
                    results.append(row_dict)
            
            result_text = f"Schema for table '{table}' in cluster '{cluster_name}', database '{database}':\n\n"
            result_text += json.dumps(results, indent=2, default=str)
            
            return [types.TextContent(type="text", text=result_text)]
            
        except KustoServiceError as e:
            error_msg = f"Error getting table schema: {e}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    async def _list_tables_tool(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List tables"""
        cluster_name = arguments.get('cluster', list(self.cluster_configs.keys())[0])
        database = arguments.get('database') or self.cluster_configs[cluster_name]['database']
        
        client = self._get_kusto_client(cluster_name)
        query = ".show tables | project TableName"
        
        try:
            logger.info(f"Listing tables in {cluster_name}/{database}")
            response = client.execute(database, query)
            results = []
            
            if response.primary_results and len(response.primary_results) > 0:
                primary_result = response.primary_results[0]
                column_names = [col.column_name for col in primary_result.columns]
                
                for row in primary_result:
                    row_dict = {}
                    for i, col_name in enumerate(column_names):
                        if i < len(row):
                            row_dict[col_name] = str(row[i]) if row[i] is not None else None
                    results.append(row_dict)
            
            result_text = f"Tables in cluster '{cluster_name}', database '{database}':\n\n"
            result_text += json.dumps(results, indent=2, default=str)
            
            return [types.TextContent(type="text", text=result_text)]
            
        except KustoServiceError as e:
            error_msg = f"Error listing tables: {e}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Interactive Kusto MCP Server")
        logger.info(f"Available clusters: {list(self.cluster_configs.keys())}")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    initialization_options=InitializationOptions(
                        server_name="interactive-kusto-mcp-server",
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
    print("Interactive Kusto MCP Server")
    print("="*50)
    print("This server will prompt you to authenticate with your work account")
    print("You may see a browser window or device code prompt")
    print()
    
    try:
        server = InteractiveKustoMCPServer()
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