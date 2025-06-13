#!/usr/bin/env python3
"""
Setup script for MCP Kusto Server local development
Run this script to verify and setup your development environment
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path

def print_step(step_num, description):
    """Print a formatted step"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print('='*60)

def run_command(command, description, required=True):
    """Run a command and handle errors"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - Failed")
            print(f"Error: {result.stderr.strip()}")
            if required:
                sys.exit(1)
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - Timeout")
        return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        if required:
            sys.exit(1)
        return False

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    print("✅ Python version OK")

def setup_virtual_environment():
    """Setup virtual environment"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv venv", "Create virtual environment")
    else:
        print("✅ Virtual environment already exists")
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = "venv\\Scripts\\activate"
        pip_path = "venv\\Scripts\\pip"
        python_path = "venv\\Scripts\\python"
    else:
        activate_script = "venv/bin/activate"
        pip_path = "venv/bin/pip"
        python_path = "venv/bin/python"
    
    print(f"Virtual environment activation: {activate_script}")
    return pip_path, python_path

def install_dependencies(pip_path):
    """Install Python dependencies"""
    print("Installing dependencies...")
    
    # Install each package individually for better error handling
    packages = [
        "azure-identity>=1.15.0",
        "azure-kusto-data>=4.3.1", 
        "mcp>=1.0.0"
    ]
    
    for package in packages:
        run_command(f"{pip_path} install {package}", f"Install {package}")
    
    # Generate requirements.txt
    run_command(f"{pip_path} freeze > requirements.txt", "Generate requirements.txt")

def verify_azure_cli():
    """Verify Azure CLI installation and authentication"""
    print("Checking Azure CLI...")
    
    # Check if Azure CLI is installed
    if not run_command("az --version", "Azure CLI installation check", required=False):
        print("❌ Azure CLI not found. Please install it:")
        print("   Windows: https://aka.ms/installazurecliwindows")
        print("