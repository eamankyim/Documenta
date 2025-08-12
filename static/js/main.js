// Main JavaScript for Documenta App

// Utility functions
const Utils = {
    // Show alert message
    showAlert: function(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.innerHTML = `
            <i class="fas fa-${this.getAlertIcon(type)}"></i>
            ${message}
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto remove after duration
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, duration);
        
        return alertDiv;
    },
    
    // Get icon for alert type
    getAlertIcon: function(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    },
    
    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Generate random ID
    generateId: function() {
        return Math.random().toString(36).substr(2, 9);
    },

    // Show delete confirmation modal
    showDeleteConfirmation: function() {
        return new Promise((resolve) => {
            // Create modal HTML if it doesn't exist
            let modal = document.getElementById('deleteConfirmModal');
            if (!modal) {
                modal = this.createDeleteModal();
                document.body.appendChild(modal);
            }

            // Show modal
            modal.classList.add('show');
            
            // Focus the cancel button by default (safer choice)
            const cancelBtn = modal.querySelector('.delete-modal-cancel');
            cancelBtn.focus();

            // Handle confirm
            const handleConfirm = () => {
                hideModal();
                resolve(true);
            };

            // Handle cancel
            const handleCancel = () => {
                hideModal();
                resolve(false);
            };

            // Handle escape key
            const handleKeyDown = (e) => {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    handleCancel();
                }
            };

            // Hide modal
            const hideModal = () => {
                modal.classList.remove('show');
                
                // Remove event listeners
                modal.querySelector('.delete-modal-confirm').removeEventListener('click', handleConfirm);
                modal.querySelector('.delete-modal-cancel').removeEventListener('click', handleCancel);
                document.removeEventListener('keydown', handleKeyDown);
            };

            // Add event listeners
            modal.querySelector('.delete-modal-confirm').addEventListener('click', handleConfirm);
            modal.querySelector('.delete-modal-cancel').addEventListener('click', handleCancel);
            document.addEventListener('keydown', handleKeyDown);
        });
    },

    // Create delete confirmation modal HTML
    createDeleteModal: function() {
        const modal = document.createElement('div');
        modal.id = 'deleteConfirmModal';
        modal.className = 'delete-modal-overlay';
        modal.innerHTML = `
            <div class="delete-modal-content">
                <div class="delete-modal-header">
                    <h3><i class="fas fa-exclamation-triangle"></i> Delete Document</h3>
                </div>
                <div class="delete-modal-body">
                    <p>Are you sure you want to delete this document?</p>
                    <p class="delete-warning">This action cannot be undone.</p>
                    <div class="delete-modal-actions">
                        <button class="btn secondary delete-modal-cancel">Cancel</button>
                        <button class="btn danger delete-modal-confirm">Delete Document</button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }
};

// API helper functions
const API = {
    // Make API request
    request: async function(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    // Get user info
    getMe: async function() {
        return await this.request('/api/me');
    },
    
    // List user documents
    listDocuments: async function() {
        return await this.request('/api/list_outputs');
    },
    
    // Get document content
    getDocument: async function(uniqueId) {
        return await this.request(`/api/content/${uniqueId}`);
    },
    
    // Save document
    saveDocument: async function(uniqueId, content, token) {
        return await this.request(`/api/save/${uniqueId}?token=${token}`, {
            method: 'POST',
            body: JSON.stringify({ content })
        });
    },
    
    // Delete document
    deleteDocument: async function(uniqueId, token) {
        return await this.request(`/api/delete/${uniqueId}?token=${token}`, {
            method: 'DELETE'
        });
    },
    
    // Get edit token
    getToken: async function(uniqueId) {
        return await this.request(`/api/token/${uniqueId}`);
    }
};

// Authentication helper
const Auth = {
    // Check if user is authenticated
    isAuthenticated: function() {
        return document.cookie.includes('session=');
    },
    
    // Get current user
    getCurrentUser: async function() {
        try {
            const user = await API.getMe();
            return user.authenticated ? user : null;
        } catch (error) {
            return null;
        }
    },
    
    // Update UI based on auth status
    updateUI: async function() {
        const user = await this.getCurrentUser();
        const authElements = document.querySelectorAll('[data-auth]');
        const guestElements = document.querySelectorAll('[data-guest]');
        
        if (user) {
            // User is authenticated
            authElements.forEach(el => el.style.display = '');
            guestElements.forEach(el => el.style.display = 'none');
            
            // Update user info
            const userNameElements = document.querySelectorAll('[data-user-name]');
            const userEmailElements = document.querySelectorAll('[data-user-email]');
            const userPlanElements = document.querySelectorAll('[data-user-plan]');
            
            userNameElements.forEach(el => el.textContent = user.name);
            userEmailElements.forEach(el => el.textContent = user.email);
            userPlanElements.forEach(el => el.textContent = user.plan);
            
        } else {
            // User is not authenticated
            authElements.forEach(el => el.style.display = 'none');
            guestElements.forEach(el => el.style.display = '');
        }
    },
    
    // Logout
    logout: function() {
        fetch('/logout', { method: 'GET' })
            .then(() => {
                window.location.href = '/signin';
            })
            .catch(error => {
                console.error('Logout failed:', error);
                Utils.showAlert('Logout failed', 'error');
            });
    }
};

// Navigation helper
const Navigation = {
    // Initialize mobile navigation
    init: function() {
        const navToggle = document.getElementById('navToggle');
        const navLinks = document.getElementById('navLinks');
        
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', () => {
                navLinks.classList.toggle('show');
            });
            
            // Close mobile nav when clicking outside
            document.addEventListener('click', (e) => {
                if (!navLinks.contains(e.target) && !navToggle.contains(e.target)) {
                    navLinks.classList.remove('show');
                }
            });
        }
    },
    
    // Smooth scroll to section
    scrollToSection: function(sectionId) {
        const element = document.getElementById(sectionId);
        if (element) {
            element.scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
};

// Document management
const DocumentManager = {
    // Create new document
    createNew: function() {
        window.location.href = '/new';
    },
    
    // Open document
    openDocument: function(uniqueId) {
        window.location.href = `/edit/${uniqueId}`;
    },
    
    // View document
    viewDocument: function(uniqueId) {
        window.location.href = `/view/${uniqueId}`;
    },
    
    // Download document
    downloadDocument: async function(uniqueId) {
        try {
            const token = await API.getToken(uniqueId);
            if (token.token) {
                window.location.href = `/download/${uniqueId}?token=${token.token}`;
            }
        } catch (error) {
            Utils.showAlert('Failed to get download token', 'error');
        }
    },
    
    // Delete document
    deleteDocument: async function(uniqueId) {
        const confirmed = await Utils.showDeleteConfirmation();
        if (confirmed) {
            try {
                const token = await API.getToken(uniqueId);
                if (token.token) {
                    await API.deleteDocument(uniqueId, token.token);
                    Utils.showAlert('Document deleted successfully', 'success');
                    // Refresh the page or remove from list
                    location.reload();
                }
            } catch (error) {
                Utils.showAlert('Failed to delete document', 'error');
            }
        }
    }
};

// File upload helper
const FileUpload = {
    // Initialize drag and drop
    initDragAndDrop: function(dropZone, onFileSelect) {
        if (!dropZone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.unhighlight, false);
        });
        
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                onFileSelect(files[0]);
            }
        });
    },
    
    preventDefaults: function(e) {
        e.preventDefault();
        e.stopPropagation();
    },
    
    highlight: function(e) {
        e.currentTarget.classList.add('drag-over');
    },
    
    unhighlight: function(e) {
        e.currentTarget.classList.remove('drag-over');
    },
    
    // Validate file
    validateFile: function(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = ['application/pdf'];
        
        if (file.size > maxSize) {
            Utils.showAlert('File size must be less than 50MB', 'error');
            return false;
        }
        
        if (!allowedTypes.includes(file.type)) {
            Utils.showAlert('Only PDF files are allowed', 'error');
            return false;
        }
        
        return true;
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize navigation
    Navigation.init();
    
    // Update UI based on auth status
    Auth.updateUI();
    
    // Set current year in footer
    const yearElement = document.getElementById('y');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
    
    // Initialize any page-specific functionality
    const currentPage = window.location.pathname;
    
    if (currentPage === '/projects' || currentPage === '/') {
        // Initialize projects page
        initProjectsPage();
    } else if (currentPage.includes('/edit/')) {
        // Initialize editor page
        initEditorPage();
    } else if (currentPage.includes('/view/')) {
        // Initialize viewer page
        initViewerPage();
    }
});

// Projects page initialization
function initProjectsPage() {
    // Load user documents
    loadUserDocuments();
    
    // Initialize file upload
    const uploadZone = document.getElementById('uploadZone');
    if (uploadZone) {
        FileUpload.initDragAndDrop(uploadZone, handleFileSelect);
    }
}

// Editor page initialization
function initEditorPage() {
    // Editor-specific initialization will be in editor.html
    console.log('Editor page initialized');
}

// Viewer page initialization
function initViewerPage() {
    // Viewer-specific initialization will be in viewer.html
    console.log('Viewer page initialized');
}

// Load user documents
async function loadUserDocuments() {
    try {
        const response = await API.listDocuments();
        displayDocuments(response.documents);
    } catch (error) {
        Utils.showAlert('Failed to load documents', 'error');
    }
}

// Display documents in the UI
function displayDocuments(documents) {
    const container = document.getElementById('documentsContainer');
    if (!container) return;
    
    if (documents.length === 0) {
        container.innerHTML = `
            <div class="text-center mt-5">
                <i class="fas fa-folder-open" style="font-size: 3rem; color: var(--muted);"></i>
                <h3 class="mt-3">No documents yet</h3>
                <p class="muted">Create your first document to get started</p>
                <a href="/new" class="btn mt-3">
                    <i class="fas fa-plus"></i> Create New Document
                </a>
            </div>
        `;
        return;
    }
    
    const documentsHTML = documents.map(doc => `
        <div class="card document-card" data-document-id="${doc.unique_id}">
            <div class="card-header">
                <h3>${doc.title || 'Untitled Document'}</h3>
                <div class="document-meta">
                    <span class="text-muted">
                        <i class="fas fa-clock"></i> ${Utils.formatDate(doc.modified)}
                    </span>
                    <span class="text-muted">
                        <i class="fas fa-file"></i> ${Utils.formatFileSize(doc.size)}
                    </span>
                </div>
            </div>
            <div class="card-actions">
                <button class="btn btn-secondary" onclick="DocumentManager.viewDocument('${doc.unique_id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn" onclick="DocumentManager.openDocument('${doc.unique_id}')">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-secondary" onclick="DocumentManager.downloadDocument('${doc.unique_id}')">
                    <i class="fas fa-download"></i> Download
                </button>
                <button class="btn btn-error" onclick="DocumentManager.deleteDocument('${doc.unique_id}')">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = documentsHTML;
}

// Handle file selection
function handleFileSelect(file) {
    if (!FileUpload.validateFile(file)) {
        return;
    }
    
    // Handle file upload logic here
    console.log('File selected:', file.name);
    // You can implement the actual upload logic here
}

// Export functions for global use
window.Utils = Utils;
window.API = API;
window.Auth = Auth;
window.Navigation = Navigation;
window.DocumentManager = DocumentManager;
window.FileUpload = FileUpload; 