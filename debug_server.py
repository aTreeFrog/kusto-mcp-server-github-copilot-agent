#!/usr/bin/env python3
"""
Debug script to test MCP server startup
This will help us see exactly what's going wrong
"""

import subprocess
import sys
import time
import os

def test_server_startup():
    """Test if the server can start properly"""
    print("🔍 Testing MCP Server Startup...")
    print("="*50)
    
    # Set up environment
    env = os.environ.copy()
    env['KUSTO_CONFIG_FILE'] = os.path.join(os.getcwd(), 'config', 'config.json')
    
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Config file: {env.get('KUSTO_CONFIG_FILE')}")
    
    # Test 1: Check if server script exists
    server_script = "mcp_kusto_server.py"
    if not os.path.exists(server_script):
        print(f"❌ Server script not found: {server_script}")
        return False
    print(f"✅ Server script found: {server_script}")
    
    # Test 2: Try to start the server process
    print("\n🚀 Starting server process...")
    try:
        process = subprocess.Popen(
            [sys.executable, server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=0  # Unbuffered
        )
        
        print(f"✅ Process started with PID: {process.pid}")
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        poll_result = process.poll()
        if poll_result is not None:
            print(f"❌ Process exited with code: {poll_result}")
            stdout, stderr = process.communicate(timeout=5)
            print("STDOUT:")
            print(stdout)
            print("STDERR:")
            print(stderr)
            return False
        
        print("✅ Process is running")
        
        # Test 3: Try to send a simple message
        print("\n📤 Sending test message...")
        test_message = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}\n'
        
        try:
            process.stdin.write(test_message)
            process.stdin.flush()
            print("✅ Message sent")
            
            # Try to read response (with timeout)
            print("📥 Waiting for response...")
            
            # Set a timeout for reading
            import select
            import threading
            
            def read_with_timeout(process, timeout=5):
                """Read from process with timeout"""
                result = []
                
                def target():
                    try:
                        line = process.stdout.readline()
                        result.append(line)
                    except:
                        result.append(None)
                
                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()
                thread.join(timeout)
                
                if thread.is_alive():
                    return None  # Timeout
                return result[0] if result else None
            
            response = read_with_timeout(process, timeout=10)
            
            if response:
                print(f"✅ Got response: {response.strip()}")
                
                # Try to parse as JSON
                import json
                try:
                    response_data = json.loads(response)
                    print(f"✅ Valid JSON response")
                    print(f"   ID: {response_data.get('id')}")
                    print(f"   Result keys: {list(response_data.get('result', {}).keys())}")
                except json.JSONDecodeError as e:
                    print(f"⚠️ Response is not valid JSON: {e}")
            else:
                print("❌ No response received (timeout)")
                
                # Check if process died
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    print("Process died. Final output:")
                    print("STDOUT:", stdout)
                    print("STDERR:", stderr)
        
        except Exception as e:
            print(f"❌ Error sending message: {e}")
        
        finally:
            # Clean up
            try:
                process.terminate()
                process.wait(timeout=5)
                print("✅ Process terminated cleanly")
            except:
                process.kill()
                print("⚠️ Process killed forcefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start process: {e}")
        return False

def check_dependencies():
    """Check if all dependencies are available"""
    print("\n🔍 Checking Dependencies...")
    print("="*30)
    
    packages = [
        'azure.identity',
        'azure.kusto.data', 
        'mcp',
        'asyncio'
    ]
    
    all_good = True
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError as e:
            print(f"❌ {package}: {e}")
            all_good = False
    
    return all_good

def main():
    """Main test function"""
    print("🧪 MCP Server Debug Tool")
    print("="*60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Some dependencies are missing. Install with:")
        print("pip install azure-identity azure-kusto-data mcp")
        return
    
    # Test server startup
    success = test_server_startup()
    
    print("\n" + "="*60)
    if success:
        print("🎉 Server startup test completed!")
        print("If you saw a valid JSON response above, your server is working.")
        print("You can now try: python test_client.py")
    else:
        print("❌ Server startup failed!")
        print("Check the error messages above and fix any issues.")

if __name__ == "__main__":
    main()