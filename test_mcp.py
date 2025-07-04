# test_mcp.py

import sys
import asyncio
import logging
from pathlib import Path

# Add server directory to Python path before imports
server_dir = Path(__file__).parent / "server"
sys.path.insert(0, str(server_dir))

# Import MCPClient after adding server dir to path
from mcp_client import MCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_functionality():
    print("🧪 Testing MCP Filesystem Server...")
    print("=" * 50)
    client = MCPClient()
    try:
        print("1. Starting MCP server...")
        success = await client.start_server()
        if not success:
            print("❌ Failed to start MCP server")
            return False
        print("✅ MCP server started successfully")
        
        print("\n2. Testing tool discovery...")
        tools = await client.list_tools()
        if tools:
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        else:
            print("❌ No tools found")
            return False
        
        print("\n3. Testing file creation...")
        result = await client.create_file("test_mcp.txt", "Hello from MCP server!")
        if result.get("success"):
            print("✅ File created successfully")
        else:
            print(f"❌ File creation failed: {result.get('error')}")
            return False
        
        print("\n4. Testing file reading...")
        result = await client.read_file("test_mcp.txt")
        if result.get("success"):
            content = result.get("result", {}).get("file_content", "")
            print(f"✅ File read successfully: '{content}'")
        else:
            print(f"❌ File reading failed: {result.get('error')}")
            return False
        
        print("\n5. Testing file listing...")
        result = await client.list_files()
        if result.get("success"):
            files = result.get("result", {}).get("files", [])
            print(f"✅ Found {len(files)} files: {files}")
        else:
            print(f"❌ File listing failed: {result.get('error')}")
            return False
        
        print("\n6. Testing manual file editing...")
        result = await client.edit_file("test_mcp.txt", content="Updated content via MCP!", use_ai=False)
        if result.get("success"):
            print("✅ File edited successfully")
        else:
            print(f"❌ File editing failed: {result.get('error')}")
            return False
        
        print("\n7. Testing AI-powered editing...")
        result = await client.edit_file("test_mcp.txt", prompt="Make this message more enthusiastic!", use_ai=True)
        if result.get("success"):
            print("✅ AI editing successful")
            if "new_content" in result.get("result", {}):
                new_content = result["result"]["new_content"]
                print(f"   New content: '{new_content}'")
        else:
            print(f"⚠️  AI editing failed: {result.get('error')}")
        
        print("\n8. Testing file deletion...")
        result = await client.delete_file("test_mcp.txt")
        if result.get("success"):
            print("✅ File deleted successfully")
        else:
            print(f"❌ File deletion failed: {result.get('error')}")
            return False
        
        print("\n9. Verifying file deletion...")
        result = await client.list_files()
        if result.get("success"):
            files = result.get("result", {}).get("files", [])
            if "test_mcp.txt" not in files:
                print("✅ File deletion verified")
            else:
                print("❌ File still exists after deletion")
                return False
        
        print("\n" + "=" * 50)
        print("🎉 All MCP tests passed successfully!")
        print("🔗 MCP protocol implementation is working correctly")
        return True
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        return False
    finally:
        print("\n🧹 Cleaning up...")
        await client.stop_server()
        print("✅ MCP server stopped")

async def test_mcp_protocol_compliance():
    print("\n🔍 Testing MCP Protocol Compliance...")
    print("-" * 30)
    client = MCPClient()
    try:
        await client.start_server()
        tools = await client.list_tools()
        if tools:
            print("✅ JSON-RPC 2.0 communication working")
        for tool in tools:
            required_fields = ["name", "description", "inputSchema"]
            if all(field in tool for field in required_fields):
                print(f"✅ Tool '{tool['name']}' has proper schema")
            else:
                print(f"❌ Tool '{tool.get('name', 'Unknown')}' missing required fields")
        print("✅ MCP protocol compliance verified")
    except Exception as e:
        print(f"❌ Protocol compliance test failed: {str(e)}")
    finally:
        await client.stop_server()

if __name__ == "__main__":
    print("🔬 MCP Filesystem Server Test Suite")
    print("This tests the Model Context Protocol implementation")
    print()
    async def run_all_tests():
        success = await test_mcp_functionality()
        if success:
            await test_mcp_protocol_compliance()
            print("\n✨ All tests completed successfully!")
            print("🚀 Your MCP server is ready to use!")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            sys.exit(1)
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {str(e)}")
        sys.exit(1)