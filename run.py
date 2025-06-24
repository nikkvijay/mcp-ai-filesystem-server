
"""
MCP Filesystem Server Runner

This script starts the MCP-based filesystem server with AI integration.
The server now uses proper MCP protocol internally for all file operations.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the server directory to Python path
server_dir = Path(__file__).parent / 'server'
sys.path.insert(0, str(server_dir))

# Import and run the MCP bridge server (fixed version)
from server.mcp_bridge import app, mcp_bridge, cleanup

if __name__ == '__main__':
    import atexit
    
    # Check if Together AI API key is set
    api_key = os.getenv('TOGETHER_AI_API_KEY')
    if not api_key:
        print("⚠️  Warning: TOGETHER_AI_API_KEY not set. AI features will not work.")
        print("   Please check your .env file.")
        print("   You can still use the file management features.\n")
    elif api_key == 'your_api_key_here':
        print("⚠️  Warning: Default API key detected. Please update your .env file.")
        print("   You can still use the file management features.\n")
    else:
        print("✅ Together AI API key loaded successfully")
    
    print("🚀 Starting MCP Filesystem Server...")
    print("📡 Using Model Context Protocol (MCP) for file operations")
    
    # Start MCP server
    if not mcp_bridge.start_mcp_server():
        print("❌ ERROR: Failed to start MCP server. Exiting.")
        sys.exit(1)
    
    print("✅ MCP server started successfully")
    
    # Register cleanup
    atexit.register(cleanup)
    
    print("📁 File storage directory: uploaded_files/")
    print("🌐 Frontend available at: http://localhost:5000")
    print("📡 API Bridge available at: http://localhost:5000/api")
    print("🏥 Health check: http://localhost:5000/api/health")
    print("\nPress Ctrl+C to stop the server")
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    try:
        app.run(debug=debug, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n🛑 Server interrupted by user")
    finally:
        cleanup()
        print("🔧 Server cleanup complete")