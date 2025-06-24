// frontend/scripts/app.js

class FilesystemApp {
  constructor() {
    this.currentFile = null;
    this.allFiles = []; // Store all files loaded from server
    this.filteredFiles = []; // Files currently displayed after search/filter
    this.aiServiceAvailable = false;
    this.currentTheme = localStorage.getItem("theme") || "light";

    this.initializeEventListeners();
    this.loadFiles();
    this.checkAIService();
    this.applyTheme();

    // For custom confirmation modal
    this.confirmActionCallback = null;
  }

  applyTheme() {
    document.documentElement.setAttribute("data-theme", this.currentTheme);
    const themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      const icon = themeBtn.querySelector("i");
      if (this.currentTheme === "dark") {
        icon.className = "fas fa-sun";
      } else {
        icon.className = "fas fa-moon";
      }
    }
  }

  toggleTheme() {
    this.currentTheme = this.currentTheme === "light" ? "dark" : "light";
    localStorage.setItem("theme", this.currentTheme);
    this.applyTheme();
  }

  async checkAIService() {
    try {
      const response = await fetch("/api/health");
      const result = await response.json();

      if (result.success) {
        this.aiServiceAvailable = result.ai_service === "available";
        this.updateAIServiceStatus(result);
      }
    } catch (error) {
      console.warn("Could not check AI service status:", error);
      this.aiServiceAvailable = false;
    }
  }

  updateAIServiceStatus(healthData) {
    const aiButton = document.getElementById("apply-ai-edit");
    const promptSection = document.querySelector(".ai-prompts");
    const aiWarningDiv = promptSection.querySelector(".ai-warning");

    if (this.aiServiceAvailable) {
      aiButton.disabled = false;
      aiButton.innerHTML = `<i class="fas fa-magic"></i><span>Apply AI Edit (${healthData.model})</span>`;
      promptSection.style.opacity = "1";
      if (aiWarningDiv) {
        aiWarningDiv.remove();
      }
    } else {
      aiButton.disabled = true;
      aiButton.innerHTML = `<i class="fas fa-exclamation-triangle"></i><span>AI Service Unavailable</span>`;
      promptSection.style.opacity = "0.5";

      // Add warning message if not already present
      if (!aiWarningDiv) {
        const warningDiv = document.createElement("div");
        warningDiv.className = "ai-warning";
        warningDiv.innerHTML = `
          <div style="background: rgba(239, 68, 68, 0.1); color: var(--accent-danger); padding: var(--spacing-md); border-radius: var(--radius-md); margin-bottom: var(--spacing-lg); border: 1px solid rgba(239, 68, 68, 0.2);">
            <i class="fas fa-exclamation-triangle" style="margin-right: var(--spacing-sm);"></i>
            AI service is not available. Check server logs for API key configuration.
          </div>
        `;
        promptSection.insertBefore(warningDiv, promptSection.firstChild);
      }
    }
  }

  initializeEventListeners() {
    // Theme toggle
    document
      .getElementById("theme-toggle")
      .addEventListener("click", () => this.toggleTheme());

    // File upload
    const folderUpload = document.getElementById("folder-upload");
    const filesUpload = document.getElementById("files-upload");

    folderUpload.addEventListener("change", () => {
      if (folderUpload.files.length > 0) {
        this.handleFileUpload(folderUpload.files);
      }
    });

    filesUpload.addEventListener("change", () => {
      if (filesUpload.files.length > 0) {
        this.handleFileUpload(filesUpload.files);
      }
    });

    // File management
    document
      .getElementById("refresh-files")
      .addEventListener("click", () => this.loadFiles());
    document
      .getElementById("create-file")
      .addEventListener("click", () => this.showCreateFileModal());
    document
      .getElementById("download-all")
      .addEventListener("click", () => this.downloadAllFiles());
    document
      .getElementById("delete-all-files")
      .addEventListener("click", () => this.deleteAllFiles());
    document
      .getElementById("file-search")
      .addEventListener("input", (e) => this.filterFiles(e.target.value));

    // Editor
    document
      .getElementById("apply-ai-edit")
      .addEventListener("click", () => this.applyAIEdit());
    document
      .getElementById("save-file")
      .addEventListener("click", () => this.saveFile());
    document
      .getElementById("close-editor")
      .addEventListener("click", () => this.closeEditor());
    document
      .getElementById("download-current")
      .addEventListener("click", () => this.downloadCurrentFile());

    // Create file modal
    document
      .getElementById("confirm-create")
      .addEventListener("click", () => this.createNewFile());
    document
      .getElementById("cancel-create")
      .addEventListener("click", () => this.hideCreateFileModal());

    // Custom Confirmation modal
    document
      .getElementById("confirm-action-btn")
      .addEventListener("click", () => this.handleConfirmAction(true));
    document
      .getElementById("cancel-action-btn")
      .addEventListener("click", () => this.handleConfirmAction(false));

    // Guided AI Prompts
    document.querySelectorAll(".prompt-btn").forEach((button) => {
      button.addEventListener("click", (e) =>
        this.applyGuidedAIPrompt(e.currentTarget.dataset.promptType)
      );
    });

    // Drag and drop
    this.setupDragAndDrop();
  }

  setupDragAndDrop() {
    const uploadCards = document.querySelectorAll(".upload-card");

    uploadCards.forEach((uploadCard) => {
      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        uploadCard.addEventListener(eventName, this.preventDefaults, false);
      });

      ["dragenter", "dragover"].forEach((eventName) => {
        uploadCard.addEventListener(
          eventName,
          () => uploadCard.classList.add("dragover"),
          false
        );
      });

      ["dragleave", "drop"].forEach((eventName) => {
        uploadCard.addEventListener(
          eventName,
          () => uploadCard.classList.remove("dragover"),
          false
        );
      });

      uploadCard.addEventListener(
        "drop",
        (e) => {
          // Determine if it's a folder drop (webkitdirectory attribute)
          const isFolderDrop = uploadCard.id === "folder-upload-area";
          let files = [];

          if (
            isFolderDrop &&
            e.dataTransfer.items &&
            e.dataTransfer.items.length > 0
          ) {
            // For folder drops, we need to manually traverse
            // This is a simplified approach, full directory upload requires more complex WebKitDirectoryEntry API
            // For now, we'll treat it as individual files if dropped on folder area.
            // A proper folder upload via drag-and-drop is more complex and typically involves
            // iterating through e.dataTransfer.items and using webkitGetAsEntry().
            // For simplicity, we'll just get files from dataTransfer for now.
            files = e.dataTransfer.files;
            if (files.length > 0 && !isFolderDrop) {
              // If files are dropped on the 'files' area
              this.handleFileUpload(files);
            } else if (files.length > 0 && isFolderDrop) {
              // If files are dropped on the 'folder' area
              // If it's a folder drop, we still need to zip it before sending.
              // For the current setup, we'll just handle it as individual files if a ZIP isn't formed.
              this.showStatus(
                "For folder drag-and-drop, please zip the folder first and drop the .zip file.",
                "info"
              );
              return;
            }
          } else {
            files = e.dataTransfer.files;
          }

          if (files.length > 0) {
            this.handleFileUpload(files);
          }
        },
        false
      );
    });
  }

  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  async handleFileUpload(files) {
    this.showLoading(true, "Uploading files...");

    try {
      const formData = new FormData();

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // Preserve directory structure for folder uploads
        const relativePath = file.webkitRelativePath || file.name;
        formData.append("files", file, relativePath);
      }

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        this.showStatus(
          `Successfully uploaded ${files.length} file(s)`,
          "success"
        );
        this.loadFiles(); // Refresh file list
      } else {
        this.showStatus(
          `Upload failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Upload error:", error);
      this.showStatus(
        "Upload failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  async loadFiles() {
    try {
      const response = await fetch("/api/files");
      const result = await response.json();

      if (result.success) {
        this.allFiles = result.files || [];
        this.filteredFiles = [...this.allFiles];
        this.renderFileList();
        this.updateFileCount();
      } else {
        this.showStatus(
          `Failed to load files: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Load files error:", error);
      this.showStatus(
        "Failed to load files: Network error or server unavailable",
        "error"
      );
    }
  }

  filterFiles(searchTerm) {
    if (!searchTerm.trim()) {
      this.filteredFiles = [...this.allFiles];
    } else {
      this.filteredFiles = this.allFiles.filter((file) =>
        file.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    this.renderFileList();
    this.updateFileCount();
  }

  getFileIcon(filename) {
    const extension = filename.split(".").pop().toLowerCase();

    const iconMap = {
      // Code files
      js: "fab fa-js-square",
      ts: "fab fa-js-square",
      jsx: "fab fa-react",
      tsx: "fab fa-react",
      py: "fab fa-python",
      java: "fab fa-java",
      cpp: "fas fa-code",
      c: "fas fa-code",
      cs: "fas fa-code",
      php: "fab fa-php",
      rb: "fas fa-gem",
      go: "fas fa-code",
      rs: "fas fa-code",
      swift: "fab fa-swift",
      kt: "fas fa-code",

      // Web files
      html: "fab fa-html5",
      htm: "fab fa-html5",
      css: "fab fa-css3-alt",
      scss: "fab fa-sass",
      sass: "fab fa-sass",
      less: "fab fa-less",

      // Data files
      json: "fas fa-brackets-curly",
      xml: "fas fa-code",
      csv: "fas fa-table",
      sql: "fas fa-database",
      yaml: "fas fa-file-code",
      yml: "fas fa-file-code",

      // Document files
      md: "fab fa-markdown",
      txt: "fas fa-file-alt",
      pdf: "fas fa-file-pdf",
      doc: "fas fa-file-word",
      docx: "fas fa-file-word",
      xls: "fas fa-file-excel",
      xlsx: "fas fa-file-excel",
      ppt: "fas fa-file-powerpoint",
      pptx: "fas fa-file-powerpoint",

      // Image files
      jpg: "fas fa-file-image",
      jpeg: "fas fa-file-image",
      png: "fas fa-file-image",
      gif: "fas fa-file-image",
      svg: "fas fa-file-image",
      webp: "fas fa-file-image",

      // Archive files
      zip: "fas fa-file-archive",
      rar: "fas fa-file-archive",
      "7z": "fas fa-file-archive",
      tar: "fas fa-file-archive",
      gz: "fas fa-file-archive",

      // Config files
      env: "fas fa-cog",
      config: "fas fa-cog",
      ini: "fas fa-cog",
      toml: "fas fa-cog",

      // Default
      default: "fas fa-file",
    };

    return iconMap[extension] || iconMap["default"];
  }

  renderFileList() {
    const fileList = document.getElementById("file-list");

    if (this.filteredFiles.length === 0) {
      fileList.innerHTML = `
        <div style="text-align: center; padding: var(--spacing-2xl); color: var(--text-muted);">
          <i class="fas fa-folder-open" style="font-size: var(--font-size-4xl); margin-bottom: var(--spacing-md); opacity: 0.5;"></i>
          <p>No files found</p>
          <p style="font-size: var(--font-size-sm); margin-top: var(--spacing-sm);">
            ${
              this.allFiles.length === 0
                ? "Upload some files to get started"
                : "Try adjusting your search"
            }
          </p>
        </div>
      `;
      return;
    }

    fileList.innerHTML = this.filteredFiles
      .map(
        (filename) => `
          <div class="file-item" onclick="app.editFile('${filename}')">
            <div class="file-icon">
              <i class="${this.getFileIcon(filename)}"></i>
            </div>
            <div class="file-name">${filename}</div>
            <div class="file-actions">
              <button onclick="event.stopPropagation(); app.downloadFile('${filename}')" title="Download">
                <i class="fas fa-download"></i>
              </button>
              <button onclick="event.stopPropagation(); app.deleteFile('${filename}')" title="Delete">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        `
      )
      .join("");
  }

  updateFileCount() {
    const fileCount = document.getElementById("file-count");
    const total = this.allFiles.length;
    const filtered = this.filteredFiles.length;

    if (total === filtered) {
      fileCount.textContent = `${total} file${total !== 1 ? "s" : ""}`;
    } else {
      fileCount.textContent = `${filtered} of ${total} files`;
    }
  }

  async editFile(filename) {
    try {
      this.showLoading(true, "Loading file...");

      const response = await fetch(
        `/api/files/${encodeURIComponent(filename)}`
      );
      const result = await response.json();

      if (result.success) {
        this.currentFile = filename;
        document.getElementById("file-content").value = result.content;
        document.getElementById("current-file").textContent = filename;
        document.getElementById("editor-section").style.display = "block";

        // Scroll to editor
        document.getElementById("editor-section").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });

        this.showStatus(`Opened ${filename}`, "success");
      } else {
        this.showStatus(
          `Failed to load file: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Edit file error:", error);
      this.showStatus(
        "Failed to load file: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  applyGuidedAIPrompt(promptType) {
    const promptMap = {
      refactor:
        "Please refactor this code to improve readability, performance, and maintainability. Follow best practices and add comments where necessary.",
      summarize:
        "Please provide a brief summary of what this code does, its main functionality, and any important details.",
      "fix-errors":
        "Please identify and fix any syntax errors, logical issues, or potential bugs in this code.",
      docstrings:
        "Please add comprehensive docstrings and comments to this code to improve documentation and readability.",
    };

    const prompt = promptMap[promptType];
    if (prompt) {
      document.getElementById("ai-prompt").value = prompt;
      this.showStatus(`Applied ${promptType} prompt`, "info");
    }
  }

  async applyAIEdit() {
    if (!this.currentFile) {
      this.showStatus("No file is currently open", "warning");
      return;
    }

    const prompt = document.getElementById("ai-prompt").value.trim();
    if (!prompt) {
      this.showStatus("Please enter a prompt for AI editing", "warning");
      return;
    }

    this.showLoading(true, "Applying AI edits...");

    try {
      const response = await fetch("/api/ai-edit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename: this.currentFile,
          prompt: prompt,
        }),
      });

      const result = await response.json();

      if (result.success) {
        document.getElementById("file-content").value = result.content;
        this.showStatus("AI edit applied successfully", "success");
      } else {
        this.showStatus(
          `AI edit failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("AI edit error:", error);
      this.showStatus(
        "AI edit failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  async saveFile() {
    if (!this.currentFile) {
      this.showStatus("No file is currently open", "warning");
      return;
    }

    const content = document.getElementById("file-content").value;

    this.showLoading(true, "Saving file...");

    try {
      const response = await fetch(
        `/api/files/${encodeURIComponent(this.currentFile)}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ content }),
        }
      );

      const result = await response.json();

      if (result.success) {
        this.showStatus("File saved successfully", "success");
      } else {
        this.showStatus(
          `Save failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Save error:", error);
      this.showStatus(
        "Save failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  closeEditor() {
    this.currentFile = null;
    document.getElementById("editor-section").style.display = "none";
    document.getElementById("file-content").value = "";
    document.getElementById("ai-prompt").value = "";
    document.getElementById("current-file").textContent = "No file selected";
    this.showStatus("Editor closed", "info");
  }

  async deleteFile(filename) {
    this.showConfirmModal(
      "Delete File",
      `Are you sure you want to delete "${filename}"? This action cannot be undone.`,
      () => this.performDeleteFile(filename)
    );
  }

  async performDeleteFile(filename) {
    this.showLoading(true, "Deleting file...");

    try {
      const response = await fetch(
        `/api/files/${encodeURIComponent(filename)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (result.success) {
        this.showStatus(`Deleted ${filename}`, "success");
        this.loadFiles(); // Refresh file list

        // If the deleted file was currently open, close the editor
        if (this.currentFile === filename) {
          this.closeEditor();
        }
      } else {
        this.showStatus(
          `Delete failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Delete error:", error);
      this.showStatus(
        "Delete failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  showCreateFileModal() {
    document.getElementById("create-file-modal").style.display = "flex";
    document.getElementById("new-filename").focus();
  }

  hideCreateFileModal() {
    document.getElementById("create-file-modal").style.display = "none";
    document.getElementById("new-filename").value = "";
    document.getElementById("new-file-content").value = "";
  }

  async createNewFile() {
    const filename = document.getElementById("new-filename").value.trim();
    const content = document.getElementById("new-file-content").value;

    if (!filename) {
      this.showStatus("Please enter a filename", "warning");
      return;
    }

    this.showLoading(true, "Creating file...");

    try {
      const response = await fetch("/api/files", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename, content }),
      });

      const result = await response.json();

      if (result.success) {
        this.showStatus(`Created ${filename}`, "success");
        this.hideCreateFileModal();
        this.loadFiles(); // Refresh file list
      } else {
        this.showStatus(
          `Create failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Create error:", error);
      this.showStatus(
        "Create failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  showStatus(message, type = "info") {
    const toastContainer = document.getElementById("toast-container");

    const icons = {
      success: "fas fa-check-circle",
      error: "fas fa-exclamation-circle",
      warning: "fas fa-exclamation-triangle",
      info: "fas fa-info-circle",
    };

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-icon">
        <i class="${icons[type]}"></i>
      </div>
      <div class="toast-content">
        <p>${message}</p>
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">
        <i class="fas fa-times"></i>
      </button>
      <div class="toast-progress"></div>
    `;

    toastContainer.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.add("hide");
        setTimeout(() => {
          if (toast.parentElement) {
            toast.remove();
          }
        }, 300);
      }
    }, 5000);
  }

  showLoading(show, message = "Processing...") {
    const overlay = document.getElementById("loading-overlay");
    const loadingText = document.getElementById("loading-text");

    if (show) {
      loadingText.textContent = message;
      overlay.style.display = "flex";
    } else {
      overlay.style.display = "none";
    }
  }

  async downloadFile(filename) {
    try {
      const response = await fetch(
        `/api/files/${encodeURIComponent(filename)}/download`
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        this.showStatus(`Downloaded ${filename}`, "success");
      } else {
        this.showStatus(`Download failed for ${filename}`, "error");
      }
    } catch (error) {
      console.error("Download error:", error);
      this.showStatus("Download failed: Network error", "error");
    }
  }

  async downloadCurrentFile() {
    if (this.currentFile) {
      await this.downloadFile(this.currentFile);
    } else {
      this.showStatus("No file is currently open", "warning");
    }
  }

  async downloadAllFiles() {
    if (this.allFiles.length === 0) {
      this.showStatus("No files to download", "warning");
      return;
    }

    this.showLoading(true, "Preparing download...");

    try {
      const response = await fetch("/api/download-all");

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "files.zip";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        this.showStatus("All files downloaded as ZIP", "success");
      } else {
        this.showStatus("Download failed", "error");
      }
    } catch (error) {
      console.error("Download all error:", error);
      this.showStatus("Download failed: Network error", "error");
    } finally {
      this.showLoading(false);
    }
  }

  async deleteAllFiles() {
    if (this.allFiles.length === 0) {
      this.showStatus("No files to delete", "warning");
      return;
    }

    this.showConfirmModal(
      "Delete All Files",
      `Are you sure you want to delete all ${this.allFiles.length} files? This action cannot be undone.`,
      () => this.performDeleteAllFiles()
    );
  }

  async performDeleteAllFiles() {
    this.showLoading(true, "Deleting all files...");

    try {
      const response = await fetch("/api/files", {
        method: "DELETE",
      });

      const result = await response.json();

      if (result.success) {
        this.showStatus("All files deleted", "success");
        this.allFiles = [];
        this.filteredFiles = [];
        this.renderFileList();
        this.updateFileCount();

        // Close editor if it was open
        if (this.currentFile) {
          this.closeEditor();
        }
      } else {
        this.showStatus(
          `Delete failed: ${result.error || "Unknown error"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Delete all error:", error);
      this.showStatus(
        "Delete failed: Network error or server unavailable",
        "error"
      );
    } finally {
      this.showLoading(false);
    }
  }

  showConfirmModal(title, message, callback) {
    this.confirmActionCallback = callback;
    document.getElementById("confirmation-modal-title").innerHTML = `
      <i class="fas fa-exclamation-triangle"></i>
      ${title}
    `;
    document.getElementById("confirmation-modal-message").textContent = message;
    document.getElementById("confirmation-modal").style.display = "flex";
  }

  hideConfirmModal() {
    document.getElementById("confirmation-modal").style.display = "none";
    this.confirmActionCallback = null;
  }

  handleConfirmAction(confirmed) {
    this.hideConfirmModal();
    if (confirmed && this.confirmActionCallback) {
      this.confirmActionCallback();
    }
  }
}

// Initialize the app when the DOM is loaded
let app;
document.addEventListener("DOMContentLoaded", () => {
  app = new FilesystemApp();
});
