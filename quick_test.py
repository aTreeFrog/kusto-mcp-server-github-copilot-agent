#!/usr/bin/env python3
"""
Quick test to verify VS Code setup and dependencies
Run this first to make sure everything is working
"""

import sys
import os
from pathlib import Path

def test_basic_setup():
    """Test basic Python setup"""
    print("🧪 Testing VS Code MCP Kusto Server Setup")
    print("="*50)
    
    # Test 1: Python version
    print(f"✅ Python version: {sys.version}")
    
    # Test 2: Working directory
    print(f"✅ Current directory: {os.getcwd()}")
    
    # Test 3: Virtual environment
    if 'venv' in sys.executable:
        print(f"✅ Virtual environment active: {sys.executable}")
    else:
        print(f"⚠️ Virtual environment not detected: {sys.executable}")
    
    # Test 4: Required directories
    required_dirs = ['config', 'logs', '.vscode']
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✅ Directory exists: {dir_name}")
        else:
            print(f"❌ Directory missing: {dir_name}")
            Path(dir_name).mkdir(exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
    
    # Test 5: Config file
    config_file = Path('config/config.json')
    if config_file.exists():
        print(f"✅ Config file exists: {config_file}")
    else:
        print(f"❌ Config file missing: {config_file}")
    
    # Test 6: Try importing required packages
    packages_to_test = [
        ('azure.identity', 'azure-identity'),
        ('azure.kusto.data', 'azure-kusto-data'),
        ('mcp', 'mcp')
    ]
    
    for package_name, pip_name in packages_to_test:
        try:
            __import__(package_name)
            print(f"✅ Package imported: {package_name}")
        except ImportError:
            print(f"❌ Package missing: {package_name}")
            print(f"   Install with: pip install {pip_name}")
    
    # Test 7: Environment variables
    config_file_env = os.getenv('KUSTO_CONFIG_FILE')
    if config_file_env:
        print(f"✅ KUSTO_CONFIG_FILE set: {config_file_env}")
    else:
        print(f"⚠️ KUSTO_CONFIG_FILE not set (will use default)")
    
    print("\n" + "="*50)
    print("🎉 Setup test complete!")
    print("\nNext steps:")
    print("1. Fix any ❌ issues above")
    print("2. Run 'az login' if you haven't")
    print("3. Update config/config.json with your Kusto cluster")
    print("4. Try running: python mcp_kusto_server.py")

if __name__ == "__main__":
    test_basic_setup()