#!/usr/bin/env python3
"""
Direct test of Kusto authentication without MCP protocol overhead
"""

import sys
import json
from pathlib import Path
from azure.identity import DeviceCodeCredential, InteractiveBrowserCredential, DefaultAzureCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder

def test_authentication():
    """Test authentication to your Kusto cluster"""
    print("Direct Kusto Authentication Test")
    print("="*50)
    
    # Load config
    config_file = Path("config") / "config.json"
    if not config_file.exists():
        print("Error: config/config.json not found")
        return
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        clusters = config.get('clusters', {})
        
        if not clusters:
            print("Error: No clusters found in config")
            return
            
        # Use the first cluster
        cluster_name = list(clusters.keys())[0]
        cluster_info = clusters[cluster_name]
        cluster_url = cluster_info['url']
        database = cluster_info['database']
        
        print(f"Testing cluster: {cluster_name}")
        print(f"URL: {cluster_url}")
        print(f"Database: {database}")
        print()
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Test different authentication methods
    auth_methods = [
        {
            'name': 'Device Code Authentication',
            'desc': 'Visit aka.ms/devicelogin with a code',
            'credential': DeviceCodeCredential
        },
        {
            'name': 'Interactive Browser Authentication',
            'desc': 'Opens a browser window',
            'credential': InteractiveBrowserCredential
        },
        {
            'name': 'Default Azure Credential',
            'desc': 'Uses existing Azure CLI login',
            'credential': DefaultAzureCredential
        }
    ]
    
    print("Available authentication methods:")
    for i, method in enumerate(auth_methods, 1):
        print(f"{i}. {method['name']} - {method['desc']}")
    
    choice = input(f"\nChoose method (1-{len(auth_methods)}): ").strip()
    
    try:
        method_index = int(choice) - 1
        if method_index < 0 or method_index >= len(auth_methods):
            print("Invalid choice")
            return
            
        selected_method = auth_methods[method_index]
        print(f"\nUsing: {selected_method['name']}")
        print("=" * 30)
        
    except ValueError:
        print("Invalid choice")
        return
    
    # Try authentication
    try:
        print("Initializing credential...")
        credential = selected_method['credential']()
        
        print("Getting access token...")
        token = credential.get_token("https://kusto.kusto.windows.net/.default")
        print(f"Success! Token expires: {token.expires_on}")
        
        # Test Kusto connection
        print(f"\nTesting connection to Kusto...")
        
        # Try different connection methods
        connection_success = False
        
        if hasattr(KustoConnectionStringBuilder, 'with_aad_application_token_authentication'):
            try:
                print("Trying: AAD Application Token Authentication")
                kcsb = KustoConnectionStringBuilder.with_aad_application_token_authentication(
                    cluster_url,
                    application_token=token.token
                )
                client = KustoClient(kcsb)
                print("Connection string created successfully")
                connection_success = True
            except Exception as e:
                print(f"Failed: {e}")
        
        if not connection_success and hasattr(KustoConnectionStringBuilder, 'with_aad_device_authentication'):
            try:
                print("Trying: AAD Device Authentication")
                kcsb = KustoConnectionStringBuilder.with_aad_device_authentication(
                    cluster_url,
                    authority_id="common"
                )
                client = KustoClient(kcsb)
                print("Connection string created successfully")
                connection_success = True
            except Exception as e:
                print(f"Failed: {e}")
        
        if not connection_success:
            try:
                print("Trying: Basic Connection")
                kcsb = KustoConnectionStringBuilder(cluster_url)
                client = KustoClient(kcsb)
                print("Connection string created successfully")
                connection_success = True
            except Exception as e:
                print(f"Failed: {e}")
        
        if connection_success:
            # Test a simple query
            print(f"\nTesting simple query on database '{database}'...")
            try:
                response = client.execute(database, ".show tables | limit 1")
                print("SUCCESS! Query executed successfully")
                print("Your authentication is working!")
                
                # Show first result if any
                if response.primary_results and len(response.primary_results) > 0:
                    primary_result = response.primary_results[0]
                    if len(list(primary_result)) > 0:
                        first_row = list(primary_result)[0]
                        print(f"Sample result: {first_row}")
                
                return True
                
            except Exception as e:
                print(f"Query failed: {e}")
                if "Forbidden" in str(e):
                    print("This likely means you don't have permission to access this database")
                elif "not found" in str(e).lower():
                    print(f"Database '{database}' might not exist")
                return False
        else:
            print("Could not establish connection")
            return False
            
    except Exception as e:
        print(f"Authentication failed: {e}")
        if "user interaction is required" in str(e).lower():
            print("Try a different authentication method that supports interactive login")
        return False

if __name__ == "__main__":
    success = test_authentication()
    if success:
        print(f"\n*** SUCCESS! ***")
        print("Your authentication is working correctly")
        print("You can now use the MCP server with your corporate cluster")
    else:
        print(f"\n*** FAILED ***") 
        print("Authentication or connection failed")
        print("Check the error messages above")