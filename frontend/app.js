// RAG Studio - Frontend Application Script
(function () {
    // -------------------------------------------------------------------------
    // 1. CONFIGURATION & STATE
    // -------------------------------------------------------------------------
    const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
        ? (window.location.port === '5500' || window.location.port === '3000'
            ? 'http://localhost:8000/api/v1'
            : `${window.location.origin}/api/v1`)
        : `${window.location.origin}/api/v1`;

    let sessionId = localStorage.getItem('rag_session_id');
    if (!sessionId) {
        sessionId = generateUUID();
        localStorage.setItem('rag_session_id', sessionId);
    }

    let authToken = localStorage.getItem('rag_auth_token');
    let loggedInUser = localStorage.getItem('rag_username');
    let isSignUpMode = false; // toggles login vs register

    // -------------------------------------------------------------------------
    // 2. DOM ELEMENTS
    // -------------------------------------------------------------------------
    // Authentication Overlay Screen
    const authOverlay = document.getElementById('auth-overlay');
    const authForm = document.getElementById('auth-form');
    const authUsernameInput = document.getElementById('auth-username');
    const authPasswordInput = document.getElementById('auth-password');
    const authSubmitBtn = document.getElementById('auth-submit-btn');
    const authSubtitle = document.getElementById('auth-subtitle');
    const authToggleText = document.getElementById('auth-toggle-text');
    const authToggleBtn = document.getElementById('auth-toggle-btn');
    
    // Sidebar User Profile Status
    const userProfileSection = document.getElementById('user-profile-section');
    const userProfileName = document.getElementById('user-profile-name');
    const logoutBtn = document.getElementById('logout-btn');

    // General UI Controls
    const sessionIdDisplay = document.getElementById('session-id-display');
    const copySessionBtn = document.getElementById('copy-session-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    
    const fileInput = document.getElementById('file-input');
    const uploadLabelArea = document.getElementById('upload-label-area');
    const fileSelectedInfo = document.getElementById('file-selected-info');
    const selectedFileName = document.getElementById('selected-file-name');
    const indexBtn = document.getElementById('index-btn');
    const uploadForm = document.getElementById('upload-form');
    const progressContainer = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressStatus = document.getElementById('upload-progress-status');
    
    const documentsList = document.getElementById('documents-list');
    
    const statusText = document.getElementById('status-text');
    const statusDot = document.querySelector('.status-dot');
    
    const chatMessagesContainer = document.getElementById('chat-messages-container');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const toast = document.getElementById('toast');

    // Inject spinner keyframes dynamically
    const spinnerStyle = document.createElement('style');
    spinnerStyle.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .spinner-icon {
            animation: spin 1s linear infinite;
        }
    `;
    document.head.appendChild(spinnerStyle);

    // -------------------------------------------------------------------------
    // 3. INITIALIZATION
    // -------------------------------------------------------------------------
    document.addEventListener('DOMContentLoaded', () => {
        // Display session ID
        sessionIdDisplay.textContent = sessionId;

        // Check authentication state
        evaluateAuthState();
        
        // Setup Drag & Drop for file upload
        setupDragAndDrop();
    });

    // -------------------------------------------------------------------------
    // 4. AUTHENTICATION & UI FLOW CONTROL
    // -------------------------------------------------------------------------
    function evaluateAuthState() {
        if (authToken) {
            // User is authenticated
            authOverlay.style.display = 'none';
            userProfileName.textContent = loggedInUser;
            userProfileSection.style.display = 'flex';
            
            // Fetch workspace contents
            checkBackendStatus();
            fetchDocuments();
            fetchChatHistory();
        } else {
            // User is not authenticated
            authOverlay.style.display = 'flex';
            userProfileSection.style.display = 'none';
            setConnectedStatus(false, 'Unauthorized');
        }
    }

    // Toggle Login vs SignUp
    authToggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        isSignUpMode = !isSignUpMode;
        
        if (isSignUpMode) {
            authSubtitle.textContent = 'Create a new account to build isolated RAG namespaces.';
            authSubmitBtn.textContent = 'Sign Up';
            authToggleText.textContent = 'Already have an account?';
            authToggleBtn.textContent = 'Login';
        } else {
            authSubtitle.textContent = 'Login to your account to begin indexing and Q&A.';
            authSubmitBtn.textContent = 'Login';
            authToggleText.textContent = "Don't have an account?";
            authToggleBtn.textContent = 'Sign Up';
        }
        authForm.reset();
    });

    // Authenticated Form Submit
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = authUsernameInput.value.trim();
        const password = authPasswordInput.value.trim();
        
        if (!username || !password) return;
        
        authSubmitBtn.setAttribute('disabled', 'true');
        authSubmitBtn.textContent = isSignUpMode ? 'Registering...' : 'Signing in...';

        const endpoint = isSignUpMode ? 'auth/signup' : 'auth/login';
        
        try {
            const res = await fetch(`${API_BASE}/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (res.ok) {
                const data = await res.json();
                if (isSignUpMode) {
                    showToast('Sign up successful! Please log in.');
                    isSignUpMode = false;
                    authSubtitle.textContent = 'Login to your account to begin indexing and Q&A.';
                    authSubmitBtn.textContent = 'Login';
                    authToggleText.textContent = "Don't have an account?";
                    authToggleBtn.textContent = 'Sign Up';
                    authForm.reset();
                } else {
                    authToken = data.access_token;
                    loggedInUser = data.username;
                    localStorage.setItem('rag_auth_token', authToken);
                    localStorage.setItem('rag_username', loggedInUser);
                    
                    showToast(`Welcome back, ${loggedInUser}!`);
                    evaluateAuthState();
                }
            } else {
                const err = await res.json();
                showToast(err.detail || 'Authentication failed', 'error');
            }
        } catch (err) {
            showToast('Unable to reach the authentication service.', 'error');
        } finally {
            authSubmitBtn.removeAttribute('disabled');
            if (!isSignUpMode) {
                authSubmitBtn.textContent = 'Login';
            } else {
                authSubmitBtn.textContent = 'Sign Up';
            }
        }
    });

    // Logout
    logoutBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to log out?')) {
            localStorage.removeItem('rag_auth_token');
            localStorage.removeItem('rag_username');
            localStorage.removeItem('rag_session_id');
            
            authToken = null;
            loggedInUser = null;
            sessionId = generateUUID();
            localStorage.setItem('rag_session_id', sessionId);
            sessionIdDisplay.textContent = sessionId;
            
            // Clear UI inputs/messages
            renderWelcomeCard();
            documentsList.innerHTML = '<div class="no-docs-message">No documents uploaded yet.</div>';
            authForm.reset();
            
            showToast('Logged out successfully.');
            evaluateAuthState();
        }
    });

    // Helper to send authorized requests
    async function authorizedFetch(url, options = {}) {
        if (!options.headers) {
            options.headers = {};
        }
        
        // Inject token
        options.headers['Authorization'] = `Bearer ${authToken}`;
        
        try {
            const res = await fetch(url, options);
            if (res.status === 401) {
                // Token has expired or is invalid
                localStorage.removeItem('rag_auth_token');
                localStorage.removeItem('rag_username');
                authToken = null;
                loggedInUser = null;
                evaluateAuthState();
                showToast('Session expired. Please login again.', 'error');
                throw new Error('Unauthorized access');
            }
            return res;
        } catch (e) {
            throw e;
        }
    }

    // -------------------------------------------------------------------------
    // 5. API HELPER FUNCTIONS
    // -------------------------------------------------------------------------
    async function checkBackendStatus() {
        try {
            const healthUrl = API_BASE.replace('/api/v1', '/health');
            const res = await fetch(healthUrl);
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'healthy') {
                    setConnectedStatus(true, 'Connected');
                } else {
                    setConnectedStatus(true, 'Degraded', 'orange');
                }
            } else {
                setConnectedStatus(false, 'API Error');
            }
        } catch (e) {
            setConnectedStatus(false, 'Disconnected');
        }
    }

    function setConnectedStatus(connected, text, colorClass = 'green') {
        statusText.textContent = text;
        statusDot.className = 'status-dot';
        if (connected) {
            statusDot.classList.add(colorClass);
        } else {
            statusDot.classList.add('orange');
        }
    }

    async function fetchDocuments() {
        try {
            const res = await authorizedFetch(`${API_BASE}/documents`);
            const docs = await res.json();
            renderDocuments(docs);
        } catch (e) {
            console.error('Connection error fetching documents:', e);
        }
    }

    async function fetchChatHistory() {
        try {
            const res = await authorizedFetch(`${API_BASE}/chat/history/${sessionId}`);
            const data = await res.json();
            const messages = data.messages || [];
            if (messages.length > 0) {
                chatMessagesContainer.innerHTML = '';
                messages.forEach(msg => {
                    appendMessageToUI(msg.role, msg.content, msg.meta, msg.sources, false);
                });
                scrollToBottom();
            }
        } catch (e) {
            console.error('Error fetching chat history:', e);
        }
    }

    // -------------------------------------------------------------------------
    // 6. DRAG AND DROP & UPLOAD SETUP
    // -------------------------------------------------------------------------
    
    // File Input selection changed
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFileSelected(file);
    });

    function setupDragAndDrop() {
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadLabelArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadLabelArea.style.borderColor = 'var(--accent-indigo)';
                uploadLabelArea.style.background = 'rgba(99, 102, 241, 0.05)';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadLabelArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadLabelArea.style.borderColor = 'var(--border-glass)';
                uploadLabelArea.style.background = 'var(--bg-glass)';
            }, false);
        });

        uploadLabelArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const file = dt.files[0];
            if (file) {
                fileInput.files = dt.files;
                handleFileSelected(file);
            }
        }, false);
    }

    function handleFileSelected(file) {
        if (file) {
            selectedFileName.textContent = file.name;
            fileSelectedInfo.style.display = 'flex';
            indexBtn.removeAttribute('disabled');
        } else {
            fileSelectedInfo.style.display = 'none';
            indexBtn.setAttribute('disabled', 'true');
        }
    }

    // Form submit for document indexing
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        indexBtn.setAttribute('disabled', 'true');
        fileInput.setAttribute('disabled', 'true');
        progressContainer.style.display = 'flex';
        progressBar.style.width = '10%';
        progressStatus.textContent = 'Uploading file...';

        const formData = new FormData();
        formData.append('file', file);

        let progressVal = 10;
        const progressInterval = setInterval(() => {
            if (progressVal < 90) {
                progressVal += Math.random() * 5;
                progressBar.style.width = `${Math.min(90, Math.floor(progressVal))}%`;
                
                if (progressVal > 70) {
                    progressStatus.textContent = 'Running layout-aware visual parsing...';
                } else if (progressVal > 40) {
                    progressStatus.textContent = 'Extracting figures & document chunks...';
                }
            }
        }, 800);

        try {
            const res = await authorizedFetch(`${API_BASE}/documents/upload`, {
                method: 'POST',
                body: formData
            });

            clearInterval(progressInterval);

            if (res.ok) {
                progressBar.style.width = '100%';
                progressStatus.textContent = 'Indexed successfully!';
                showToast('Document indexed successfully!');
                
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    progressBar.style.width = '0';
                    fileSelectedInfo.style.display = 'none';
                    uploadForm.reset();
                    fileInput.removeAttribute('disabled');
                    fetchDocuments();
                }, 1000);
            } else {
                const errData = await res.json();
                const errMsg = errData.detail || 'Indexing failed';
                showToast(errMsg, 'error');
                resetUploadUI();
            }
        } catch (err) {
            clearInterval(progressInterval);
            showToast('Network error during file upload', 'error');
            resetUploadUI();
        }
    });

    function resetUploadUI() {
        progressContainer.style.display = 'none';
        progressBar.style.width = '0';
        indexBtn.removeAttribute('disabled');
        fileInput.removeAttribute('disabled');
    }

    // Chat submit
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        chatInput.value = '';
        
        const welcomeCard = document.querySelector('.welcome-card');
        if (welcomeCard) {
            welcomeCard.remove();
        }

        appendMessageToUI('user', query);
        scrollToBottom();

        const thinkingId = appendThinkingIndicator();
        scrollToBottom();

        const startTime = Date.now();

        try {
            const res = await authorizedFetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    session_id: sessionId,
                    top_k: 5
                })
            });

            removeThinkingIndicator(thinkingId);

            if (res.ok) {
                const data = await res.json();
                appendMessageToUI('assistant', data.answer, null, data.sources);
                scrollToBottom();
            } else {
                showToast('Failed to retrieve response', 'error');
                appendMessageToUI('assistant', '⚠️ *Error: Unable to synthesize response from the assistant.*');
                scrollToBottom();
            }
        } catch (e) {
            removeThinkingIndicator(thinkingId);
            showToast('Network error occurred', 'error');
            appendMessageToUI('assistant', '⚠️ *Network error: Could not reach the backend service.*');
            scrollToBottom();
        }
    });

    // Sample question buttons click handlers
    document.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('sample-question-btn')) {
            chatInput.value = e.target.textContent;
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // -------------------------------------------------------------------------
    // 7. RENDER FUNCTIONS
    // -------------------------------------------------------------------------
    function renderDocuments(docs) {
        documentsList.innerHTML = '';
        if (!docs || docs.length === 0) {
            documentsList.innerHTML = '<div class="no-docs-message">No documents uploaded yet.</div>';
            return;
        }

        docs.forEach(doc => {
            const card = document.createElement('div');
            card.className = 'doc-card';
            card.innerHTML = `
                <div class="doc-details">
                    <span class="doc-title" title="${escapeHtml(doc.file_name)}">📄 ${escapeHtml(doc.file_name)}</span>
                    <span class="doc-meta">(${doc.total_chunks || 0} chunks)</span>
                </div>
                <button class="btn-delete-doc" title="Delete document" data-id="${doc.document_id}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            `;

            card.querySelector('.btn-delete-doc').addEventListener('click', async (e) => {
                const docId = e.currentTarget.getAttribute('data-id');
                if (confirm('Are you sure you want to delete this document?')) {
                    try {
                        const res = await authorizedFetch(`${API_BASE}/documents/${docId}`, {
                            method: 'DELETE'
                        });
                        if (res.ok) {
                            showToast('Document deleted!');
                            fetchDocuments();
                        } else {
                            showToast('Failed to delete document', 'error');
                        }
                    } catch (err) {
                        showToast('Error connecting to backend', 'error');
                    }
                }
            });

            documentsList.appendChild(card);
        });
    }

    function appendMessageToUI(role, content, meta = null, sources = null, animate = true) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper';
        if (animate) {
            wrapper.style.animation = 'fadeIn 0.3s ease';
        }

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        if (role === 'assistant') {
            if (window.marked && window.marked.parse) {
                bubble.innerHTML = window.marked.parse(content);
            } else {
                bubble.innerHTML = content.replace(/\n/g, '<br>');
            }
        } else {
            bubble.textContent = content;
        }
        
        wrapper.appendChild(bubble);

        if (role === 'assistant' && sources && sources.length > 0) {
            const accordion = document.createElement('div');
            accordion.className = 'inspector-accordion';
            
            const header = document.createElement('div');
            header.className = 'inspector-header';
            header.innerHTML = `
                <span>Inspector: Retrieved Source Chunks (${sources.length})</span>
                <svg class="inspector-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
            `;

            const inspectorContent = document.createElement('div');
            inspectorContent.className = 'inspector-content';

            sources.forEach((src, idx) => {
                const item = document.createElement('div');
                item.className = 'source-item';
                
                const pageInfo = src.page ? `, Page ${src.page}` : '';
                
                item.innerHTML = `
                    <div class="source-meta">
                        <span class="source-title">Chunk ${idx + 1} — ${escapeHtml(src.document_name)}</span>
                        <span>${pageInfo}</span>
                    </div>
                    <div class="source-textarea" readonly>${escapeHtml(src.chunk)}</div>
                `;
                inspectorContent.appendChild(item);
            });

            accordion.appendChild(header);
            accordion.appendChild(inspectorContent);

            header.addEventListener('click', () => {
                accordion.classList.toggle('open');
            });

            wrapper.appendChild(accordion);
        }

        row.appendChild(wrapper);
        chatMessagesContainer.appendChild(row);
    }

    function appendThinkingIndicator() {
        const id = 'thinking-' + Date.now();
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.id = id;
        
        row.innerHTML = `
            <div class="message-wrapper">
                <div class="message-bubble" style="display: flex; align-items: center; gap: 10px; color: var(--text-secondary); background: var(--bg-glass); border: 1px solid var(--border-glass);">
                    <svg class="spinner-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-indigo);">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                    <span>Retrieving sources and synthesizing response...</span>
                </div>
            </div>
        `;

        chatMessagesContainer.appendChild(row);
        return id;
    }

    function removeThinkingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function renderWelcomeCard() {
        chatMessagesContainer.innerHTML = `
            <div class="welcome-card">
                <svg class="welcome-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h3>Welcome to RAG Studio</h3>
                <p>Ingest dense two-column academic papers, retrieve details from visual diagrams, and compile accurate tables with layout-aware hybrid retrieval.</p>
                <div class="sample-questions">
                    <button class="sample-question-btn">Compare BERTBASE and BERTLARGE architecture parameters</button>
                    <button class="sample-question-btn">How much improvement did BERT achieve on GLUE compared with OpenAI GPT?</button>
                    <button class="sample-question-btn">Explain Figure 1 BERT pre-training and fine tuning</button>
                    <button class="sample-question-btn">Explain Figure 2 input representation</button>
                </div>
            </div>
        `;
    }

    // -------------------------------------------------------------------------
    // 8. UTILITY FUNCTIONS
    // -------------------------------------------------------------------------
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function scrollToBottom() {
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = 'toast';
        
        setTimeout(() => {
            toast.classList.add('show', type);
        }, 10);

        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }
})();
