#!/usr/bin/env python3
"""
MCP Server for Kusto with cached authentication (no interactive prompts)
Perfect for VS Code background usage
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from mcp.server import Server, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging (no Unicode characters)
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'mcp-kusto-cached-auth.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class CachedAuthKustoMCPServer:
    """MCP Server with cached authentication for VS Code background usage"""
    
    def __init__(self):
        self.server = Server("kusto-mcp-server")
        self.kusto_clients: Dict[str, KustoClient] = {}
        self.credential = None
        self.cluster_configs = {}
        
        # Load configuration
        self._load_configuration()
        
        # Initialize authentication with cached credentials
        self._initialize_cached_auth()
        
        # Setup MCP handlers
        self._setup_handlers()
    
    def _load_configuration(self):
        """Load Kusto cluster configurations with environment variable support"""
        # Load .env file if it exists
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info(f"Loaded environment variables from {env_file}")
            except ImportError:
                logger.warning("python-dotenv not installed, skipping .env file loading")
            except Exception as e:
                logger.warning(f"Error loading .env file: {e}")
        
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
                    config_text = f.read()
                    
                    # Substitute environment variables in the format ${VAR_NAME}
                    import re
                    def replace_env_var(match):
                        var_name = match.group(1)
                        return os.getenv(var_name, match.group(0))  # Return original if env var not found
                    
                    config_text = re.sub(r'\$\{([^}]+)\}', replace_env_var, config_text)
                    
                    config = json.loads(config_text)
                    self.cluster_configs = config.get('clusters', {})
                    logger.info(f"Loaded config from: {config_file}")
                    logger.info(f"Environment variables substituted in config")
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
        
        # Environment variable fallback (direct env vars)
        cluster_url = os.getenv('KUSTO_CLUSTER_URL')
        if cluster_url:
            cluster_name = os.getenv('KUSTO_CLUSTER_NAME', 'default')
            self.cluster_configs[cluster_name] = {
                'url': cluster_url,
                'database': os.getenv('KUSTO_DATABASE', 'MyDatabase')
            }
            logger.info(f"Added cluster from direct environment variables: {cluster_name}")
        
        # Default to samples cluster if nothing configured
        if not self.cluster_configs:
            self.cluster_configs['samples'] = {
                'url': 'https://help.kusto.windows.net',
                'database': 'Samples'
            }
            logger.info("Using default samples cluster configuration")
        
        logger.info(f"Configured clusters: {list(self.cluster_configs.keys())}")
    
    def _initialize_cached_auth(self):
        """Initialize authentication using cached credentials"""
        logger.info("Initializing cached authentication for VS Code background usage")
        
        # Try different credential sources in order
        auth_methods = [
            ("DefaultAzureCredential", lambda: DefaultAzureCredential()),
            ("InteractiveBrowserCredential", lambda: InteractiveBrowserCredential(
                authority="https://login.microsoftonline.com/common"
            ))
        ]
        
        for auth_name, auth_factory in auth_methods:
            try:
                logger.info(f"Trying {auth_name}...")
                credential = auth_factory()
                
                # Test the credential silently
                token = credential.get_token("https://kusto.kusto.windows.net/.default")
                
                self.credential = credential
                logger.info(f"Successfully authenticated using {auth_name}")
                logger.info(f"Token expires: {token.expires_on}")
                return
                
            except Exception as e:
                logger.warning(f"{auth_name} failed: {e}")
                continue
        
        # If all methods fail, set credential to None but don't crash
        logger.error("All authentication methods failed - server will start but queries may fail")
        logger.error("Run pre_auth.py first to authenticate interactively")
        self.credential = None
    
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
            
            if not self.credential:
                raise RuntimeError("Authentication not available. Please run pre_auth.py first.")
            
            try:
                # Get a fresh token
                token = self.credential.get_token("https://kusto.kusto.windows.net/.default")
                
                # Use the method that worked in our testing
                if hasattr(KustoConnectionStringBuilder, 'with_aad_application_token_authentication'):
                    kcsb = KustoConnectionStringBuilder.with_aad_application_token_authentication(
                        cluster_url,
                        application_token=token.token
                    )
                    logger.info("Using AAD application token authentication")
                else:
                    # Fallback
                    kcsb = KustoConnectionStringBuilder(cluster_url)
                    logger.info("Using basic connection string")
                
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
                    description="Execute a KQL (Kusto Query Language) query against a Kusto cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "production"
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
                                "default": 100,
                                "maximum": 10000
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_table_schema",
                    description="Get the schema/structure of a specific table in Kusto",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "production"
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
                    description="List all tables available in a Kusto database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cluster": {
                                "type": "string",
                                "description": f"Kusto cluster name. Available: {available_clusters}",
                                "default": available_clusters[0] if available_clusters else "production"
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
        limit = arguments.get('limit', 100)
        
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
        logger.info("Starting Kusto MCP Server with cached authentication for VS Code")
        logger.info(f"Available clusters: {list(self.cluster_configs.keys())}")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    initialization_options=InitializationOptions(
                        server_name="kusto-mcp-server",
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
        server = CachedAuthKustoMCPServer()
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