from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import json
import sys
import threading
import queue
import time
import zipfile
import tempfile
import io

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000').split(',')
CORS(app, origins=cors_origins)

# Configuration
FILE_DIRECTORY = os.getenv('FILE_STORAGE_PATH', 'uploaded_files')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10MB

# Ensure directory exists
Path(FILE_DIRECTORY).mkdir(exist_ok=True)

class MCPBridge:
    """Bridge to communicate with MCP server via subprocess"""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
        self.response_queue = queue.Queue()
        self.initialized = False
        self._lock = threading.Lock()
        
    def start_mcp_server(self):
        """Start the MCP server as a subprocess"""
        try:
            server_script = Path(__file__).parent / "mcp_server.py"
            self.process = subprocess.Popen(
                [sys.executable, str(server_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Start reader thread
            reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            reader_thread.start()
            
            # Wait a moment for the server to start
            time.sleep(0.5)
            
            # Initialize the server
            success = self._send_initialize()
            if success:
                self.initialized = True
                logger.info("MCP server started and initialized successfully")
                return True
            else:
                logger.error("Failed to initialize MCP server")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    def _read_responses(self):
        """Read responses from MCP server in a separate thread"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    if line:
                        response = json.loads(line)
                        self.response_queue.put(response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from MCP server: {line}, error: {e}")
            except Exception as e:
                logger.error(f"Error reading MCP response: {e}")
                break
    
    def _send_request(self, method: str, params: dict = None, timeout: float = 30.0):
        """Send a request to MCP server and wait for response"""
        with self._lock:
            if not self.process or self.process.poll() is not None:
                raise RuntimeError("MCP server not running")
            
            self.request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {}
            }
            
            try:
                # Send request
                request_json = json.dumps(request) + "\n"
                self.process.stdin.write(request_json)
                self.process.stdin.flush()
                
                # Wait for response
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        response = self.response_queue.get(timeout=0.1)
                        if response.get("id") == self.request_id:
                            return response
                        else:
                            # Put back non-matching response
                            self.response_queue.put(response)
                    except queue.Empty:
                        continue
                
                raise TimeoutError(f"No response from MCP server for method {method}")
                
            except Exception as e:
                logger.error(f"Error sending request {method}: {e}")
                raise
    
    def _send_initialize(self):
        """Send initialization request"""
        try:
            params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "flask-bridge", "version": "1.0.0"}
            }
            response = self._send_request("initialize", params)
            return "result" in response
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def call_tool(self, tool_name: str, arguments: dict):
        """Call a tool via MCP"""
        try:
            if not self.initialized:
                return {"success": False, "error": "MCP server not initialized"}
                
            params = {"name": tool_name, "arguments": arguments}
            response = self._send_request("tools/call", params)
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            else:
                return {"success": True, "result": response.get("result", {})}
                
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_tools(self):
        """List available tools"""
        try:
            if not self.initialized:
                return {"success": False, "error": "MCP server not initialized"}
                
            response = self._send_request("tools/list")
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            else:
                return {"success": True, "tools": response.get("result", {}).get("tools", [])}
        except Exception as e:
            logger.error(f"List tools failed: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_server(self):
        """Stop the MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            logger.info("MCP server stopped")

# Global MCP bridge instance
mcp_bridge = MCPBridge()

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file upload from frontend"""
    try:
        if 'files' not in request.files:
            return jsonify({"success": False, "message": "No files provided"}), 400
        
        files = request.files.getlist('files')
        uploaded_files = []
        
        # Ensure directory exists
        Path(FILE_DIRECTORY).mkdir(exist_ok=True)
        
        for file in files:
            if file.filename:
                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > MAX_FILE_SIZE:
                    return jsonify({
                        "success": False, 
                        "message": f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE} bytes"
                    }), 400
                
                content = file.read().decode('utf-8', errors='replace')
                
                # Use MCP bridge to create the file
                result = mcp_bridge.call_tool("create_file", {
                    "filename": file.filename,
                    "content": content
                })
                
                if result.get("success"):
                    uploaded_files.append(file.filename)
                    logger.info(f"Uploaded file via MCP: {file.filename}")
                else:
                    logger.error(f"MCP upload failed for {file.filename}: {result.get('error')}")
        
        return jsonify({
            "success": True,
            "message": f"Uploaded {len(uploaded_files)} files",
            "files": uploaded_files
        })
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all files using MCP"""
    try:
        result = mcp_bridge.call_tool("list_files", {})
        
        if result.get("success"):
            files = result.get("result", {}).get("files", [])
            return jsonify({"success": True, "files": files})
        else:
            return jsonify({"success": False, "message": result.get("error", "Unknown error")}), 500
            
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/files/<path:filename>', methods=['GET'])
def get_file_content(filename):
    """Get file content using MCP"""
    try:
        result = mcp_bridge.call_tool("read_file", {"filename": filename})
        
        if result.get("success"):
            content = result.get("result", {}).get("file_content", "")
            return jsonify({"success": True, "content": content})
        else:
            return jsonify({"success": False, "message": result.get("error", "File not found")}), 404
            
    except Exception as e:
        logger.error(f"Get file error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/files/create', methods=['POST'])
def create_file():
    """Create a new file using MCP"""
    try:
        data = request.json
        filename = data.get('filename')
        content = data.get('content', '')
        
        if not filename:
            return jsonify({"success": False, "message": "Filename required"}), 400
        
        result = mcp_bridge.call_tool("create_file", {
            "filename": filename,
            "content": content
        })
        
        if result.get("success"):
            logger.info(f"Created file via MCP: {filename}")
            return jsonify({"success": True, "message": "File created successfully"})
        else:
            return jsonify({"success": False, "message": result.get("error", "Creation failed")}), 500
            
    except Exception as e:
        logger.error(f"Create file error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/files/edit', methods=['PUT'])
def edit_file():
    """Edit a file using MCP"""
    try:
        data = request.json
        filename = data.get('filename')
        prompt = data.get('prompt')
        new_content = data.get('content')
        use_ai = data.get('use_ai', False)
        
        if not filename:
            return jsonify({"success": False, "message": "Filename required"}), 400
        
        # Use MCP edit_file tool with appropriate parameters
        if use_ai and prompt:
            result = mcp_bridge.call_tool("edit_file", {
                "filename": filename,
                "prompt": prompt,
                "use_ai": True
            })
        else:
            result = mcp_bridge.call_tool("edit_file", {
                "filename": filename,
                "content": new_content or "",
                "use_ai": False
            })
        
        if result.get("success"):
            response_data = {"success": True, "message": "File edited successfully"}
            
            # Include new content if available (from AI editing)
            mcp_result = result.get("result", {})
            if "new_content" in mcp_result:
                response_data["new_content"] = mcp_result["new_content"]
            
            logger.info(f"Edited file via MCP: {filename}")
            return jsonify(response_data)
        else:
            return jsonify({"success": False, "message": result.get("error", "Edit failed")}), 500
            
    except Exception as e:
        logger.error(f"Edit file error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    """Delete a file using MCP"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"success": False, "message": "Filename required"}), 400
        
        result = mcp_bridge.call_tool("delete_file", {"filename": filename})
        
        if result.get("success"):
            logger.info(f"Deleted file via MCP: {filename}")
            return jsonify({"success": True, "message": "File deleted successfully"})
        else:
            return jsonify({"success": False, "message": result.get("error", "Delete failed")}), 500
            
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check if MCP server is available
        tools_result = mcp_bridge.list_tools()
        mcp_available = tools_result.get("success", False)
        
        # Check AI service availability
        ai_key = os.getenv('TOGETHER_AI_API_KEY')
        ai_status = "available" if ai_key and ai_key != 'your_api_key_here' else "unavailable"
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "mcp_server": "available" if mcp_available else "unavailable",
            "ai_service": ai_status,
            "model": os.getenv('TOGETHER_AI_MODEL', 'mistralai/Mixtral-8x7B-Instruct-v0.1') if ai_status == "available" else None
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download a specific file"""
    try:
        result = mcp_bridge.call_tool("read_file", {"filename": filename})
        
        if result.get("success"):
            content = result.get("result", {}).get("file_content", "")
            
            # Create response with file content
            response = Response(
                content,
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="{os.path.basename(filename)}"'
                }
            )
            
            logger.info(f"Downloaded file: {filename}")
            return response
        else:
            return jsonify({"success": False, "message": result.get("error", "File not found")}), 404
            
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/download/all', methods=['GET'])
def download_all_files():
    """Download all files as a ZIP archive"""
    try:
        # Get list of all files
        files_result = mcp_bridge.call_tool("list_files", {})
        
        if not files_result.get("success"):
            return jsonify({"success": False, "message": "Failed to list files"}), 500
        
        files = files_result.get("result", {}).get("files", [])
        
        if not files:
            return jsonify({"success": False, "message": "No files to download"}), 404
        
        # Create ZIP file in memory
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in files:
                # Read file content via MCP
                file_result = mcp_bridge.call_tool("read_file", {"filename": filename})
                
                if file_result.get("success"):
                    content = file_result.get("result", {}).get("file_content", "")
                    zf.writestr(filename, content)
                    logger.info(f"Added to ZIP: {filename}")
                else:
                    logger.warning(f"Skipped file due to read error: {filename}")
        
        memory_file.seek(0)
        
        # Create response
        response = Response(
            memory_file.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': 'attachment; filename="filesystem-files.zip"',
                'Content-Type': 'application/zip'
            }
        )
        
        logger.info(f"Created ZIP download with {len(files)} files")
        return response
        
    except Exception as e:
        logger.error(f"Download all files error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# Serve frontend files
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory('../frontend', path)
    except Exception:
        return jsonify({"error": "File not found"}), 404

def cleanup():
    """Cleanup MCP bridge on shutdown"""
    global mcp_bridge
    if mcp_bridge:
        mcp_bridge.stop_server()

if __name__ == '__main__':
    import atexit
    
    # Start MCP server
    if not mcp_bridge.start_mcp_server():
        logger.error("Failed to start MCP server. Exiting.")
        sys.exit(1)
    
    # Register cleanup function
    atexit.register(cleanup)
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    logger.info("Starting MCP Flask Bridge Server...")
    logger.info("This server uses MCP protocol internally for all filesystem operations")
    
    try:
        app.run(debug=debug, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        cleanup()
