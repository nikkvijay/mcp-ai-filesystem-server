# server/mcp_server.py

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import requests
from dotenv import load_dotenv
from filelock import FileLock
from retrying import retry

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FILE_DIRECTORY = os.getenv('FILE_STORAGE_PATH', 'uploaded_files')
TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_MODEL = os.getenv('TOGETHER_AI_MODEL', 'meta-llama/Llama-3.3-70B-Instruct-Turbo')
TOGETHER_AI_BASE_URL = 'https://api.together.xyz/v1/chat/completions'

ALLOWED_EXTENSIONS = [
    'txt', 'md', 'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs',
    'php', 'rb', 'go', 'rs', 'swift', 'kt', 'html', 'htm', 'css', 'scss',
    'sass', 'less', 'json', 'xml', 'csv', 'sql', 'yaml', 'yml', 'doc', 'docx',
    'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp',
    'zip', 'rar', '7z', 'tar', 'gz', 'env', 'config', 'ini', 'toml'
]

Path(FILE_DIRECTORY).mkdir(exist_ok=True)

class MCPServer:
    def __init__(self):
        self.tools = self._register_tools()
        self.initialized = False

    def _register_tools(self):
        return {
            "create_file": {
                "description": "Create a new file with specified content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to create"},
                        "content": {"type": "string", "description": "Content to write to the file", "default": ""}
                    },
                    "required": ["filename"]
                }
            },
            "edit_file": {
                "description": "Edit an existing file using AI assistance or direct content replacement",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to edit"},
                        "prompt": {"type": "string", "description": "Natural language prompt for AI editing"},
                        "content": {"type": "string", "description": "New content to replace the file"},
                        "use_ai": {"type": "boolean", "description": "Whether to use AI assistance", "default": True}
                    },
                    "required": ["filename"]
                }
            },
            "delete_file": {
                "description": "Delete an existing file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to delete"}
                    },
                    "required": ["filename"]
                }
            },
            "read_file": {
                "description": "Read the content of an existing file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to read"}
                    },
                    "required": ["filename"]
                }
            },
            "list_files": {
                "description": "List all files in the filesystem",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}
            }
        }

    @staticmethod
    def validate_path(filename: str) -> str:
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise ValueError(f"Invalid filename: {filename}")
        file_path = Path(FILE_DIRECTORY) / filename
        resolved_path = file_path.resolve()
        base_path = Path(FILE_DIRECTORY).resolve()
        if not str(resolved_path).startswith(str(base_path)):
            raise ValueError(f"Path traversal detected: {filename}")
        return str(resolved_path)

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return extension in ALLOWED_EXTENSIONS

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    async def call_together_ai(self, prompt: str, file_content: str = "") -> Optional[str]:
        if not TOGETHER_AI_API_KEY or TOGETHER_AI_API_KEY == 'your_api_key_here':
            logger.error("Together AI API key not configured")
            return None
        headers = {
            'Authorization': f'Bearer {TOGETHER_AI_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": TOGETHER_AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that edits files based on user instructions. Return only the modified content without any explanations or markdown formatting."
                },
                {
                    "role": "user",
                    "content": f"File content:\n{file_content}\n\nInstructions: {prompt}\n\nPlease provide the modified file content:"
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.7
        }
        try:
            logger.info(f"Making request to Together AI with model: {TOGETHER_AI_MODEL}")
            response = requests.post(TOGETHER_AI_BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error calling Together AI API: {e}")
            raise

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        try:
            if method == "initialize":
                self.initialized = True
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {"name": "filesystem-server", "version": "1.0.0"}
                    }
                }
            elif method == "tools/list":
                tools = [
                    {"name": name, "description": tool_def["description"], "inputSchema": tool_def["inputSchema"]}
                    for name, tool_def in self.tools.items()
                ]
                return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")
                result = await self.execute_tool(tool_name, arguments)
                return {"jsonrpc": "2.0", "id": request_id, "result": result}
            else:
                raise ValueError(f"Unknown method: {method}")
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Request failed: {str(e)}"}
            }

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "create_file":
            filename = arguments["filename"]
            content = arguments.get("content", "")
            if not self.validate_file_extension(filename):
                raise ValueError(f"Invalid file extension for {filename}")
            file_path = self.validate_path(filename)
            lock_file = f"{file_path}.lock"
            with FileLock(lock_file):
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            logger.info(f"Created file: {filename}")
            return {"content": [{"type": "text", "text": f"File '{filename}' created successfully"}]}

        elif tool_name == "edit_file":
            filename = arguments["filename"]
            prompt = arguments.get("prompt")
            new_content = arguments.get("content")
            use_ai = arguments.get("use_ai", True)
            if not self.validate_file_extension(filename):
                raise ValueError(f"Invalid file extension for {filename}")
            file_path = self.validate_path(filename)
            lock_file = f"{file_path}.lock"
            with FileLock(lock_file):
                if not Path(file_path).exists():
                    raise ValueError(f"File '{filename}' not found")
                if use_ai and prompt:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                    try:
                        modified_content = await self.call_together_ai(prompt, current_content)
                        if modified_content is None:
                            raise ValueError("AI service unavailable")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)
                        logger.info(f"AI-edited file: {filename}")
                        return {
                            "content": [{"type": "text", "text": f"File '{filename}' edited with AI assistance"}],
                            "new_content": modified_content
                        }
                    except Exception as e:
                        raise ValueError(f"AI edit failed: {str(e)}")
                elif new_content is not None:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    logger.info(f"Manually edited file: {filename}")
                    return {"content": [{"type": "text", "text": f"File '{filename}' content updated"}]}
                else:
                    raise ValueError("Either 'prompt' or 'content' required")

        elif tool_name == "delete_file":
            filename = arguments["filename"]
            if not self.validate_file_extension(filename):
                raise ValueError(f"Invalid file extension for {filename}")
            file_path = self.validate_path(filename)
            lock_file = f"{file_path}.lock"
            with FileLock(lock_file):
                if not Path(file_path).exists():
                    raise ValueError(f"File '{filename}' not found")
                Path(file_path).unlink()
            logger.info(f"Deleted file: {filename}")
            return {"content": [{"type": "text", "text": f"File '{filename}' deleted successfully"}]}

        elif tool_name == "read_file":
            filename = arguments["filename"]
            if not self.validate_file_extension(filename):
                raise ValueError(f"Invalid file extension for {filename}")
            file_path = self.validate_path(filename)
            lock_file = f"{file_path}.lock"
            with FileLock(lock_file):
                if not Path(file_path).exists():
                    raise ValueError(f"File '{filename}' not found")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            return {"content": [{"type": "text", "text": content}], "file_content": content}

        elif tool_name == "list_files":
            files = []
            for root, dirs, filenames in os.walk(FILE_DIRECTORY):
                for filename in filenames:
                    if not self.validate_file_extension(filename):
                        logger.warning(f"Skipped file due to invalid extension: {filename}")
                        continue
                    rel_path = os.path.relpath(os.path.join(root, filename), FILE_DIRECTORY)
                    files.append(rel_path.replace('\\', '/'))
            files_list = files if files else []
            return {
                "content": [{"type": "text", "text": f"Files: {', '.join(files_list) if files_list else 'No files found'}"}],
                "files": files_list
            }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def run(self):
        logger.info("Starting MCP Filesystem Server...")
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                try:
                    request = json.loads(line.strip())
                    response = await self.handle_request(request)
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                    }
                    print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            logger.info("Server stopping...")
        except Exception as e:
            logger.error(f"Server error: {e}")

async def main():
    server = MCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())