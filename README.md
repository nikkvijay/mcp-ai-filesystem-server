# 🚀 MCP File System

An intelligent, Model Context Protocol (MCP) powered filesystem server enabling seamless file management and AI-assisted editing.

## [Demo Video](https://drive.google.com/file/d/1wwRwuxC2zCDFHheD-TBXR8-d_kdMyGGD/view?usp=sharing)

## ✨ Overview

The **MCP File System ** is a sophisticated application designed to streamline file operations with the power of Artificial Intelligence. It implements a robust Model Context Protocol (MCP) server, offering a secure and extensible foundation for interacting with files. Through its intuitive web interface, users can upload entire folders, manage individual files, and leverage an integrated AI assistant for intelligent content manipulation.

### Key Capabilities:

- **MCP Server Implementation**: A true JSON-RPC 2.0 compliant server for standardized communication.
- **Comprehensive File Tools**: Supports create, read, edit, and delete operations on files.
- **Intelligent AI Editing**: Utilizes advanced AI models (like Mixtral-8x7B-Instruct) for natural language-driven file modifications.
- **Modern Web Frontend**: A responsive and user-friendly interface built with HTML, CSS (Tailwind-inspired), and JavaScript.
- **Efficient File Management**: Features for bulk folder uploads, file filtering, and one-click downloads.
- **Real-time Feedback**: Provides clear notifications and loading indicators for all operations.

---

## 🏗️ Technical Architecture

The MCP File System is built with a full-stack architecture combining a robust backend with a seamless frontend.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Web Frontend│ <──> │ Flask Bridge │ <──> │ MCP Client │ <──> │ MCP Server │ <──> │ AI Service │
│             │     │              │     │             │     │             │     │             │
│ File Upload │     │ REST API     │     │ JSON-RPC 2.0│     │ File Ops    │     │ AI Editing │
│ User Actions│     │ CORS Enabled │     │ Protocol    │     │ Tool Reg.   │     │ Mixtral-8x7B│
│ Notifications│     │ File Serving │     │ stdio comm  │     │ Validation  │     │ Together AI │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## 📁 Project Structure

```bash
mcp-filesystem-server/
├── run.py                 # Main entry point to start the Flask Bridge and MCP Server
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment configuration
├── server/
│   ├── mcp_server.py      # Core MCP server implementing JSON-RPC 2.0
│   ├── mcp_client.py      # MCP protocol client for subprocess communication
│   ├── mcp_bridge.py      # Flask application bridging frontend to MCP server
│   └── file_operations.py # Low-level file system utilities (used by mcp_server)
├── frontend/              # Web user interface assets
│   ├── index.html         # Main UI layout
│   ├── scripts/app.js     # Frontend logic and interactivity
│   └── styles/main.css    # Comprehensive Tailwind-inspired styling
├── uploaded_files/        # Default directory for storing user-uploaded files
└── test_mcp.py            # Comprehensive test suite for MCP protocol compliance and functionality
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.7+ installed on your system.
- pip (Python package installer).
- **Together AI API key** (optional, but highly recommended for AI editing features).

### Installation Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/nikkvijay/mcp-ai-filesystem-server.git
   cd mcp-filesystem-server
   ```

2. **Create and activate a virtual environment (recommended):**

   For Windows:

   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

   For macOS/Linux:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   - Copy the example environment file:

     ```bash
     cp .env.example .env
     ```

   - Edit the `.env` file and add your **Together AI API key** (optional).

     ```bash
     TOGETHER_AI_API_KEY=your_together_ai_api_key_here
     ```

5. **Run the server:**

   ```bash
   python run.py
   ```

6. **Access the application:**

   Open your web browser and navigate to: [http://localhost:5000](http://localhost:5000)

---

## 🔧 MCP Tools and Functionality

The MCP server exposes the following tools, accessible via the MCP client:

| Tool          | Description                                        | Parameters                                                  |
| ------------- | -------------------------------------------------- | ----------------------------------------------------------- |
| `create_file` | Creates a new file with specified content.         | `filename (string)`, `content (string)`                     |
| `edit_file`   | Edits an existing file, either manually or via AI. | `filename (string)`, `content (string)`, `use_ai (boolean)` |
| `delete_file` | Deletes a specified file.                          | `filename (string)`                                         |
| `read_file`   | Reads and returns the content of a file.           | `filename (string)`                                         |
| `list_files`  | Lists all files in the storage directory.          | None                                                        |

---

## 🧪 Testing & Verification

### Automated Tests

Execute the comprehensive MCP protocol test suite to ensure all components are functioning correctly:

```bash
python test_mcp.py
```

This test suite verifies:

- ✅ MCP server startup and initialization.
- ✅ Accurate tool discovery and registration (5 tools).
- ✅ End-to-end functionality of file creation, reading, manual editing, and deletion.
- ✅ Seamless AI-powered editing functionality.
- ✅ Adherence to JSON-RPC 2.0 protocol specifications.
- ✅ Robust error handling and various edge cases.

---

## 📋 How to Use the Application

### 1. **Upload Files**

- **Upload Folder**: Upload entire directory structures.
- **Upload Files**: Select individual files.
- **Drag & Drop**: Conveniently drag and drop files or zipped folders.

### 2. **File Management**

- **Browse Files**: All uploaded files are visible.
- **File Count**: Dynamic badge indicating current number of files.
- **Delete Files**: Delete individual files or use "Delete All Files" for a complete cleanup.

### 3. **Edit Files with AI**

- Click the "Edit" icon (✏️) next to any file.
- In the "AI Assistant" section, enter a natural language prompt for changes.

### 4. **Manual File Editing**

- Open any file in the editor.
- Modify the file's content directly.
- Click "Save" to apply changes.

### 5. **Download Files**

- **Individual Download**: Click the download icon (⬇️).
- **Bulk Download**: Download all files as a ZIP archive.
- **Current File Download**: Download the currently open file.

---

## 🎨 Features Showcase

- **Smart Upload**: Supports individual files and zipped folder uploads.
- **Broad File Type Support**: Handles code, data, config, script, documentation, and log files.
- **Real-time Progress Feedback**: Provides updates during uploads and processing.

### AI Integration

- **Natural Language Editing**: Modify files using human-like commands.
- **Mixtral Model**: Uses Together AI's Mixtral-8x7B-Instruct for context-aware editing.

---

## 🛣️ Future Enhancements

- **Tree View for File Navigation**: Better visualization for deeply nested folder structures.
- **Syntax Highlighting**: Client-side syntax highlighter for code files.
- **Undo/Redo**: Implement standard undo/redo for the editor.
- **Batch AI Operations**: Apply a single AI prompt to multiple files.
- **User Authentication**: Support multi-user environments and secure file access.
- **Cloud Storage Integration**: Support for cloud services (e.g., Google Cloud Storage, AWS S3).
- **Version Control**: Git integration to track and revert file changes.

---

## 🤝 Contributing

We welcome contributions! Here's how you can contribute:

1. **Fork the repository**.
2. **Clone your forked repository**:

   ```bash
   git clone https://github.com/nikkvijay/mcp-ai-filesystem-server.git
   ```

3. **Create and activate a Python virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   .\venv\Scripts\activate   # Windows
   ```

4. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

5. **Create a new feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

6. **Run tests before pushing changes**:

   ```bash
   python test
   ```
