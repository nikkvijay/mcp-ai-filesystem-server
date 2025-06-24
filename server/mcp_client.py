import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPClient:
    """Client for communicating with MCP Filesystem Server"""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
        
    async def start_server(self):
        """Start the MCP server process"""
        try:
            server_script = Path(__file__).parent / "mcp_server.py"
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, str(server_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("MCP server started")
            
            # Initialize the server
            await self._send_initialize()
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info("MCP server stopped")
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.process:
            raise RuntimeError("MCP server not started")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        
        response = json.loads(response_line.decode())
        
        if "error" in response:
            raise RuntimeError(f"MCP server error: {response['error']}")
        
        return response.get("result", {})
    
    async def _send_initialize(self):
        """Send initialization request to MCP server"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "filesystem-client",
                "version": "1.0.0"
            }
        }
        return await self._send_request("initialize", params)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server"""
        try:
            result = await self._send_request("tools/list")
            return result.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            params = {
                "name": name,
                "arguments": arguments
            }
            result = await self._send_request("tools/call", params)
            return {
                "success": True,
                "result": result,
                "content": result.get("content", [])
            }
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_file(self, filename: str, content: str = "") -> Dict[str, Any]:
        """Create a new file"""
        return await self.call_tool("create_file", {
            "filename": filename,
            "content": content
        })
    
    async def edit_file(self, filename: str, prompt: str = None, content: str = None, use_ai: bool = True) -> Dict[str, Any]:
        """Edit an existing file"""
        arguments = {"filename": filename, "use_ai": use_ai}
        
        if prompt:
            arguments["prompt"] = prompt
        if content is not None:
            arguments["content"] = content
            
        return await self.call_tool("edit_file", arguments)
    
    async def delete_file(self, filename: str) -> Dict[str, Any]:
        """Delete a file"""
        return await self.call_tool("delete_file", {"filename": filename})
    
    async def read_file(self, filename: str) -> Dict[str, Any]:
        """Read file content"""
        return await self.call_tool("read_file", {"filename": filename})
    
    async def list_files(self) -> Dict[str, Any]:
        """List all files"""
        return await self.call_tool("list_files", {})

# Global MCP client instance
mcp_client = MCPClient()

async def initialize_mcp_client():
    """Initialize the MCP client"""
    success = await mcp_client.start_server()
    if success:
        logger.info("MCP client initialized successfully")
    else:
        logger.error("Failed to initialize MCP client")
    return success

async def shutdown_mcp_client():
    """Shutdown the MCP client"""
    await mcp_client.stop_server()
    logger.info("MCP client shutdown complete")

# Example usage and testing
async def test_mcp_client():
    """Test the MCP client functionality"""
    if not await initialize_mcp_client():
        return
    
    try:
        # Test listing tools
        tools = await mcp_client.list_tools()
        print(f"Available tools: {[tool.get('name') for tool in tools]}")
        
        # Test creating a file
        result = await mcp_client.create_file("test.txt", "Hello, MCP World!")
        print(f"Create file result: {result}")
        
        # Test reading the file
        result = await mcp_client.read_file("test.txt")
        print(f"Read file result: {result}")
        
        # Test listing files
        result = await mcp_client.list_files()
        print(f"List files result: {result}")
        
        # Test editing with AI (if configured)
        result = await mcp_client.edit_file("test.txt", prompt="Make it more enthusiastic!")
        print(f"Edit file result: {result}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await shutdown_mcp_client()

if __name__ == "__main__":
    asyncio.run(test_mcp_client())
