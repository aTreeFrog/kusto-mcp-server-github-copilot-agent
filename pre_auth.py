#!/usr/bin/env python3
"""
Pre-authentication script - run this first to authenticate and cache credentials
"""

import os
import json
from pathlib import Path
from azure.identity import InteractiveBrowserCredential, DeviceCodeCredential

def pre_authenticate():
    """Pre-authenticate and cache credentials for the MCP server"""
    print("Pre-Authentication for Kusto MCP Server")
    print("="*50)
    print("This will authenticate you and cache credentials for VS Code")
    print()
    
    # Try different authentication methods
    auth_methods = [
        {
            "name": "Device Code Authentication",
            "desc": "Visit aka.ms/devicelogin with a code",
            "credential": lambda: DeviceCodeCredential()
        },
        {
            "name": "Interactive Browser (no tenant)",
            "desc": "Opens browser with default settings",
            "credential": lambda: InteractiveBrowserCredential()
        },
        {
            "name": "Interactive Browser (common tenant)",
            "desc": "Opens browser with common tenant",
            "credential": lambda: InteractiveBrowserCredential(
                authority="https://login.microsoftonline.com/common"
            )
        }
    ]
    
    print("Available authentication methods:")
    for i, method in enumerate(auth_methods, 1):
        print(f"{i}. {method['name']} - {method['desc']}")
    
    choice = input(f"\nChoose method (1-{len(auth_methods)}): ").strip()
    
    try:
        method_index = int(choice) - 1
        if method_index < 0 or method_index >= len(auth_methods):
            print("Invalid choice, using Device Code Authentication")
            method_index = 0
            
        selected_method = auth_methods[method_index]
        print(f"\nUsing: {selected_method['name']}")
        print("=" * 50)
        
    except ValueError:
        print("Invalid choice, using Device Code Authentication")
        selected_method = auth_methods[0]
    
    try:
        if selected_method['name'] == "Device Code Authentication":
            print("Starting device code authentication...")
            print("You will see a code to enter at aka.ms/devicelogin")
        else:
            print("Opening browser for Microsoft authentication...")
        
        # Create credential
        credential = selected_method['credential']()
        
        # Get token to trigger authentication
        print("Getting access token...")
        token = credential.get_token("https://kusto.kusto.windows.net/.default")
        
        print("✅ Authentication successful!")
        print(f"Token expires: {token.expires_on}")
        print()
        print("Credentials are now cached.")
        print("Your VS Code MCP server should now work without prompting for auth.")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("💡 Try a different authentication method:")
        print("1. Device Code is usually the most reliable")
        print("2. Make sure you're using your work Microsoft account")
        print("3. Check that you have access to the Kusto cluster")
        return False

if __name__ == "__main__":
    success = pre_authenticate()
    if success:
        print("\n🎉 SUCCESS!")
        print("Now you can use VS Code with the MCP server.")
        print("The authentication is cached and will work in the background.")
    else:
        print("\n❌ FAILED!")
        print("Authentication did not complete successfully.")
        print("Try running this script again and choose a different auth method.")