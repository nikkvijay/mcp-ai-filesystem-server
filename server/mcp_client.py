# server/mcp_client.py

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = [
    'txt', 'md', 'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs',
    'php', 'rb', 'go', 'rs', 'swift', 'kt', 'html', 'htm', 'css', 'scss',
    'sass', 'less', 'json', 'xml', 'csv', 'sql', 'yaml', 'yml', 'doc', 'docx',
    'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp',
    'zip', 'rar', '7z', 'tar', 'gz', 'env', 'config', 'ini', 'toml'
]

class MCPClient:
    def __init__(self):
        self.process = None
        self.request_id = 0

    async def start_server(self):
        try:
            server_script = Path(__file__).parent / "mcp_server.py"
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, str(server_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("MCP server started")
            await self._send_initialize()
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False

    async def stop_server(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info("MCP server stopped")

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
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
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        try:
            response = json.loads(response_line.decode())
            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']['message']}")
            return response.get("result", {})
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {str(e)}")

    async def _send_initialize(self):
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "filesystem-client", "version": "1.0.0"}
        }
        return await self._send_request("initialize", params)

    async def list_tools(self) -> List[Dict[str, Any]]:
        try:
            result = await self._send_request("tools/list")
            return result.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            params = {"name": name, "arguments": arguments}
            result = await self._send_request("tools/call", params)
            return {
                "success": True,
                "result": result,
                "content": result.get("content", [])
            }
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            return {"success": False, "error": f"Tool call failed: {str(e)}"}

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return extension in ALLOWED_EXTENSIONS

    async def create_file(self, filename: str, content: str = "") -> Dict[str, Any]:
        if not self.validate_file_extension(filename):
            return {"success": False, "error": f"Invalid file extension for {filename}"}
        return await self.call_tool("create_file", {"filename": filename, "content": content})

    async def edit_file(self, filename: str, prompt: str = None, content: str = None, use_ai: bool = True) -> Dict[str, Any]:
        if not self.validate_file_extension(filename):
            return {"success": False, "error": f"Invalid file extension for {filename}"}
        arguments = {"filename": filename, "use_ai": use_ai}
        if prompt:
            arguments["prompt"] = prompt
        if content is not None:
            arguments["content"] = content
        return await self.call_tool("edit_file", arguments)

    async def delete_file(self, filename: str) -> Dict[str, Any]:
        if not self.validate_file_extension(filename):
            return {"success": False, "error": f"Invalid file extension for {filename}"}
        return await self.call_tool("delete_file", {"filename": filename})

    async def read_file(self, filename: str) -> Dict[str, Any]:
        if not self.validate_file_extension(filename):
            return {"success": False, "error": f"Invalid file extension for {filename}"}
        return await self.call_tool("read_file", {"filename": filename})

    async def list_files(self) -> Dict[str, Any]:
        return await self.call_tool("list_files", {})

mcp_client = MCPClient()

async def initialize_mcp_client():
    success = await mcp_client.start_server()
    if success:
        logger.info("MCP client initialized successfully")
    else:
        logger.error("Failed to initialize MCP client")
    return success

async def shutdown_mcp_client():
    await mcp_client.stop_server()
    logger.info("MCP client shutdown complete")

async def test_mcp_client():
    if not await initialize_mcp_client():
        return
    try:
        tools = await mcp_client.list_tools()
        print(f"Available tools: {[tool.get('name') for tool in tools]}")
        result = await mcp_client.create_file("test.txt", "Hello, MCP World!")
        print(f"Create file result: {result}")
        result = await mcp_client.read_file("test.txt")
        print(f"Read file result: {result}")
        result = await mcp_client.list_files()
        print(f"List files result: {result}")
        result = await mcp_client.edit_file("test.txt", prompt="Make it more enthusiastic!")
        print(f"Edit file result: {result}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await shutdown_mcp_client()

if __name__ == "__main__":
    asyncio.run(test_mcp_client())