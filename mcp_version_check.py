#!/usr/bin/env python3
"""
Check MCP library version and compatibility
"""

import sys

def check_mcp_version():
    """Check MCP library version and available classes"""
    print("🔍 Checking MCP Library Compatibility...")
    print("="*50)
    
    try:
        import mcp
        print(f"✅ MCP version: {mcp.__version__}")
    except AttributeError:
        print("⚠️ MCP version not available")
    except ImportError:
        print("❌ MCP library not found")
        return False
    
    # Check available modules
    try:
        from mcp.server import Server
        print("✅ mcp.server.Server")
    except ImportError as e:
        print(f"❌ mcp.server.Server: {e}")
        return False
    
    try:
        from mcp.server.stdio import stdio_server
        print("✅ mcp.server.stdio.stdio_server")
    except ImportError as e:
        print(f"❌ mcp.server.stdio.stdio_server: {e}")
        return False
    
    try:
        from mcp.server.models import InitializationOptions
        print("✅ mcp.server.models.InitializationOptions")
    except ImportError as e:
        print(f"❌ mcp.server.models.InitializationOptions: {e}")
        return False
    
    try:
        from mcp.types import Resource, Tool, TextContent
        print("✅ mcp.types (Resource, Tool, TextContent)")
    except ImportError as e:
        print(f"❌ mcp.types: {e}")
        return False
    
    # Test creating a basic server
    try:
        server = Server("test")
        print("✅ Server instantiation works")
        
        # Check get_capabilities method signature
        import inspect
        sig = inspect.signature(server.get_capabilities)
        print(f"✅ get_capabilities signature: {sig}")
        
    except Exception as e:
        print(f"❌ Server instantiation failed: {e}")
        return False
    
    return True

def test_minimal_server():
    """Test the most minimal MCP server possible"""
    print("\n🧪 Testing Minimal MCP Server...")
    print("="*40)
    
    try:
        import asyncio
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.server.models import InitializationOptions
        
        async def minimal_test():
            server = Server("minimal-test")
            
            @server.list_tools()
            async def list_tools():
                return []
            
            @server.list_resources() 
            async def list_resources():
                return []
            
            print("✅ Server setup complete")
            
            # Try to get capabilities
            try:
                caps = server.get_capabilities()
                print("✅ get_capabilities() works (no args)")
            except TypeError:
                try:
                    caps = server.get_capabilities(notification_options=None, experimental_capabilities=None)
                    print("✅ get_capabilities() works (with args)")
                except Exception as e:
                    print(f"❌ get_capabilities() failed: {e}")
                    return False
            
            print("✅ Minimal server test passed")
            return True
        
        result = asyncio.run(minimal_test())
        return result
        
    except Exception as e:
        print(f"❌ Minimal server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 MCP Library Diagnostic Tool")
    print("="*60)
    
    version_ok = check_mcp_version()
    if not version_ok:
        print("\n❌ MCP version check failed!")
        sys.exit(1)
    
    minimal_ok = test_minimal_server()
    if not minimal_ok:
        print("\n❌ Minimal server test failed!")
        sys.exit(1)
    
    print("\n🎉 MCP library appears to be working!")
    print("The issue might be in the server implementation.")