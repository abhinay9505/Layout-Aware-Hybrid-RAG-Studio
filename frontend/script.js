// =============================================
// CONFIG & AUTH
// =============================================
const API = 'http://localhost:8000/api/v1';
let jwtToken = localStorage.getItem('rag_jwt_token');
let userEmail = localStorage.getItem('rag_email');
let authMode = 'login'; // 'login' or 'register'

// =============================================
// SESSION
// =============================================
let sessionId = localStorage.getItem('rag_session_id');
if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem('rag_session_id', sessionId);
}

// =============================================
// DOM REFS
// =============================================
const $ = id => document.getElementById(id);
const dropZone          = $('drop-zone');
const fileInput         = $('file-input');
const documentsList     = $('documents-list');
const chatHistory       = $('chat-history');
const chatInput         = $('chat-input');
const sendBtn           = $('send-btn');
const clearChatBtn      = $('clear-chat-btn');
const newSessionBtn     = $('new-session-btn');
const copySessionBtn    = $('copy-session-btn');
const sessionIdDisplay  = $('session-id-display');
const uploadProgress    = $('upload-progress-container');
const progressFill      = $('progress-bar-fill');
const uploadFileName    = $('upload-file-name');
const uploadStatus      = $('upload-status');
const charCount         = $('char-count');
const docCount          = $('doc-count');
const msgCount          = $('msg-count');
const toast             = $('toast');
const modalOverlay      = $('modal-overlay');
const modalTitle        = $('modal-title');
const modalMessage      = $('modal-message');
const modalCancel       = $('modal-cancel');
const modalConfirm      = $('modal-confirm');

// Auth DOM Refs
const authContainer     = $('auth-container');
const appContainer      = $('app-container');
const authForm          = $('auth-form');
const authUsername      = $('auth-username');
const authPassword      = $('auth-password');
const authTitle         = $('auth-title');
const authSubtitle      = $('auth-subtitle');
const btnAuthSubmit     = $('btn-auth-submit');
const authSwitchBtn     = $('auth-switch-btn');
const authSwitchText    = $('auth-switch-text');
const logoutBtn         = $('logout-btn');
const userAvatar        = $('user-avatar');
const userDisplayName   = $('user-display-name');

let messageCount = 0;
let toastTimer = null;
let modalCallback = null;

// =============================================
// API FETCH WRAPPER
// =============================================
async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (jwtToken) {
        options.headers['Authorization'] = `Bearer ${jwtToken}`;
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        handleLogout();
        showToast('Session expired. Please log in again.', 'error');
        throw new Error('Unauthorized');
    }
    return res;
}

// =============================================
// INIT
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    sessionIdDisplay.textContent = sessionId.slice(0, 24) + '…';
    sessionIdDisplay.title = sessionId;
    
    // Auth listeners
    authSwitchBtn.addEventListener('click', toggleAuthMode);
    authForm.addEventListener('submit', handleAuthSubmit);
    logoutBtn.addEventListener('click', handleLogout);
    
    checkAuth();
});

// =============================================
// AUTH HANDLERS
// =============================================
function checkAuth() {
    if (jwtToken) {
        authContainer.style.display = 'none';
        appContainer.style.display = 'flex';
        
        // Show email prefix (part before @) in the sidebar
        const displayName = userEmail ? userEmail.split('@')[0] : 'User';
        userDisplayName.textContent = userEmail || 'User';
        userAvatar.textContent = displayName.charAt(0).toUpperCase();
        
        fetchDocuments();
        fetchChatHistory();
    } else {
        authContainer.style.display = 'flex';
        appContainer.style.display = 'none';
    }
}

function toggleAuthMode() {
    if (authMode === 'login') {
        authMode = 'register';
        authTitle.textContent = 'Create Account';
        authSubtitle.textContent = 'Sign up to start using Hybrid RAG';
        btnAuthSubmit.textContent = 'Sign Up';
        authSwitchText.textContent = 'Already have an account?';
        authSwitchBtn.textContent = 'Login';
    } else {
        authMode = 'login';
        authTitle.textContent = 'Welcome Back';
        authSubtitle.textContent = 'Login to access your Hybrid RAG Assistant';
        btnAuthSubmit.textContent = 'Login';
        authSwitchText.textContent = "Don't have an account?";
        authSwitchBtn.textContent = 'Sign Up';
    }
    authUsername.value = '';
    authPassword.value = '';
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const emailVal = authUsername.value.trim().toLowerCase();
    const passVal = authPassword.value;
    
    if (!emailVal || !passVal) return;

    // Client-side Gmail validation
    if (!/^[a-z0-9.+]+@gmail\.com$/.test(emailVal)) {
        showToast('Please enter a valid Gmail address (e.g. user@gmail.com)', 'error');
        return;
    }
    
    const endpoint = authMode === 'login' ? 'login' : 'register';
    btnAuthSubmit.disabled = true;
    btnAuthSubmit.textContent = authMode === 'login' ? 'Logging in...' : 'Registering...';
    
    try {
        const res = await fetch(`${API}/auth/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailVal, password: passVal })
        });
        
        const data = await res.json();
        if (res.ok && data.access_token) {
            jwtToken = data.access_token;
            userEmail = emailVal;
            localStorage.setItem('rag_jwt_token', jwtToken);
            localStorage.setItem('rag_email', userEmail);
            
            showToast(authMode === 'login' ? 'Welcome back!' : 'Account registered successfully!', 'success');
            
            // Clear input fields
            authUsername.value = '';
            authPassword.value = '';
            
            checkAuth();
        } else {
            showToast(data.detail || 'Authentication failed', 'error');
        }
    } catch (err) {
        showToast('Could not reach the server', 'error');
        console.error(err);
    } finally {
        btnAuthSubmit.disabled = false;
        btnAuthSubmit.textContent = authMode === 'login' ? 'Login' : 'Sign Up';
    }
}

function handleLogout() {
    jwtToken = null;
    userEmail = null;
    localStorage.removeItem('rag_jwt_token');
    localStorage.removeItem('rag_email');
    
    // Reset state
    messageCount = 0;
    msgCount.textContent = '0';
    docCount.textContent = '0';
    documentsList.innerHTML = '';
    chatHistory.innerHTML = '';
    
    checkAuth();
}

// =============================================
// TOAST
// =============================================
function showToast(msg, type = 'info') {
    if (toastTimer) clearTimeout(toastTimer);
    toast.textContent = msg;
    toast.className = `toast ${type}`;
    toastTimer = setTimeout(() => { toast.className = 'toast hidden'; }, 3500);
}

// =============================================
// MODAL
// =============================================
function showModal(title, message, onConfirm) {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalCallback = onConfirm;
    modalOverlay.hidden = false;
}

modalCancel.addEventListener('click', () => { modalOverlay.hidden = true; });
modalConfirm.addEventListener('click', () => {
    modalOverlay.hidden = true;
    if (modalCallback) modalCallback();
});

// =============================================
// SESSION MANAGEMENT
// =============================================
copySessionBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(sessionId).then(() => showToast('Session ID copied!'));
});

newSessionBtn.addEventListener('click', () => {
    showModal(
        'New Session',
        'This will start a fresh session. Your previous chat history will remain in the database.',
        () => {
            sessionId = crypto.randomUUID();
            localStorage.setItem('rag_session_id', sessionId);
            sessionIdDisplay.textContent = sessionId.slice(0, 24) + '…';
            sessionIdDisplay.title = sessionId;
            messageCount = 0;
            msgCount.textContent = '0';
            chatHistory.innerHTML = `
                <div class="welcome-screen">
                    <div class="welcome-glow"></div>
                    <div class="welcome-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                    </div>
                    <h2>New Session Started</h2>
                    <p>Ask anything or upload a document to get started.</p>
                    <div class="feature-chips">
                        <div class="chip">📄 Document Search</div>
                        <div class="chip">🌐 Web Fallback</div>
                        <div class="chip">⚡ Smart Cache</div>
                        <div class="chip">💬 Session Memory</div>
                    </div>
                </div>`;
            showToast('New session started', 'success');
        }
    );
});

// =============================================
// DOCUMENT UPLOAD
// =============================================
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});

fileInput.addEventListener('change', e => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
});

async function uploadFile(file) {
    const allowed = [
        '.pdf', '.docx',
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
        '.mp3', '.wav', '.m4a', '.ogg', '.flac',
        '.mp4', '.avi', '.mov', '.mkv', '.webm'
    ];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showToast('Unsupported file type. Allowed: PDF, DOCX, Images, Audio, Video', 'error');
        return;
    }

    // Show progress
    uploadFileName.textContent = file.name.length > 24 ? file.name.slice(0, 24) + '…' : file.name;
    uploadStatus.textContent = 'Uploading…';
    uploadProgress.hidden = false;
    dropZone.style.pointerEvents = 'none';
    dropZone.style.opacity = '0.5';

    // Fake progress animation
    let pct = 0;
    const ticker = setInterval(() => {
        pct = Math.min(pct + Math.random() * 12, 85);
        progressFill.style.width = pct + '%';
    }, 200);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await apiFetch(`${API}/documents/upload`, { method: 'POST', body: formData });
        const data = await res.json();

        clearInterval(ticker);
        progressFill.style.width = '100%';
        uploadStatus.textContent = 'Done ✓';

        if (data.success) {
            showToast(`"${file.name}" uploaded successfully`, 'success');
            setTimeout(() => { uploadProgress.hidden = true; progressFill.style.width = '0%'; }, 1200);
            fetchDocuments();
        } else {
            showToast(data.detail || 'Upload failed', 'error');
            uploadStatus.textContent = 'Failed';
            setTimeout(() => { uploadProgress.hidden = true; progressFill.style.width = '0%'; }, 2000);
        }
    } catch (err) {
        clearInterval(ticker);
        showToast('Could not reach the server', 'error');
        uploadProgress.hidden = true;
        progressFill.style.width = '0%';
        console.error(err);
    } finally {
        dropZone.style.pointerEvents = 'auto';
        dropZone.style.opacity = '1';
        fileInput.value = '';
    }
}

// =============================================
// FETCH DOCUMENTS
// =============================================
async function fetchDocuments() {
    try {
        const res = await apiFetch(`${API}/documents`);
        const docs = await res.json();
        docCount.textContent = docs.length;

        documentsList.innerHTML = '';

        if (!docs.length) {
            documentsList.innerHTML = `
                <div class="empty-docs">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <p>No documents yet</p>
                </div>`;
            return;
        }

        docs.forEach(doc => {
            const el = document.createElement('div');
            el.className = 'doc-item';
            
            // Determine icon
            let iconSvg = '';
            const ext = '.' + doc.file_name.split('.').pop().toLowerCase();
            const type = doc.file_type || (
                ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'].includes(ext) ? 'image' :
                ['.mp3', '.wav', '.m4a', '.ogg', '.flac'].includes(ext) ? 'audio' :
                ['.mp4', '.avi', '.mov', '.mkv', '.webm'].includes(ext) ? 'video' : 'document'
            );
            
            if (type === 'image') {
                iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent2);flex-shrink:0"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
            } else if (type === 'audio') {
                iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--green);flex-shrink:0"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;
            } else if (type === 'video') {
                iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--yellow);flex-shrink:0"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`;
            } else {
                iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent);flex-shrink:0"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
            }

            el.innerHTML = `
                <div class="doc-info">
                    ${iconSvg}
                    <div style="overflow:hidden">
                        <div class="doc-name" title="${doc.file_name}">${doc.file_name}</div>
                        <div class="doc-chunks">${doc.total_chunks ?? '?'} chunks</div>
                    </div>
                </div>
                <button class="btn-delete" data-id="${doc.document_id}" title="Delete document">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>`;
            el.querySelector('.btn-delete').addEventListener('click', () => deleteDocument(doc.document_id, doc.file_name));
            documentsList.appendChild(el);
        });
    } catch (err) {
        console.error('fetchDocuments:', err);
    }
}

async function deleteDocument(docId, fileName) {
    showModal(
        'Delete Document',
        `Remove "${fileName}" and all its chunks from the knowledge base?`,
        async () => {
            try {
                const res = await apiFetch(`${API}/documents/${docId}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.success) {
                    showToast('Document deleted', 'success');
                    fetchDocuments();
                }
            } catch (err) {
                showToast('Failed to delete document', 'error');
            }
        }
    );
}

// =============================================
// CHAT HISTORY (LOAD ON START)
// =============================================
async function fetchChatHistory() {
    try {
        const res = await apiFetch(`${API}/chat/history/${sessionId}`);
        const data = await res.json();
        const messages = data.messages || [];

        if (messages.length) {
            chatHistory.innerHTML = '';
            messages.forEach(msg => renderMessage(msg.role, msg.content, null));
            messageCount = messages.length;
            msgCount.textContent = messageCount;
            scrollBottom();
        }
    } catch (err) {
        console.error('fetchChatHistory:', err);
    }
}

// =============================================
// CLEAR CHAT
// =============================================
clearChatBtn.addEventListener('click', () => {
    showModal(
        'Clear Chat History',
        'This will permanently delete all messages in this session.',
        async () => {
            try {
                await apiFetch(`${API}/chat/history/${sessionId}`, { method: 'DELETE' });
                chatHistory.innerHTML = `
                    <div class="welcome-screen">
                        <div class="welcome-glow"></div>
                        <div class="welcome-icon">
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                        </div>
                        <h2>Chat Cleared</h2>
                        <p>Start a fresh conversation.</p>
                    </div>`;
                messageCount = 0;
                msgCount.textContent = '0';
                showToast('Chat history cleared', 'success');
            } catch (err) {
                showToast('Failed to clear history', 'error');
            }
        }
    );
});

// =============================================
// INPUT HANDLING
// =============================================
chatInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
    charCount.textContent = `${this.value.length} / 4000`;
    charCount.style.color = this.value.length > 3800 ? 'var(--red)' : 'var(--muted)';
});

chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

// =============================================
// SEND MESSAGE
// =============================================
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || sendBtn.disabled) return;

    chatInput.value = '';
    chatInput.style.height = 'auto';
    charCount.textContent = '0 / 4000';

    renderMessage('user', text, null);
    const typingEl = showTyping();
    sendBtn.disabled = true;

    const start = Date.now();

    try {
        const res = await apiFetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text, session_id: sessionId, top_k: 5 })
        });

        const data = await res.json();
        const elapsed = ((Date.now() - start) / 1000).toFixed(1);

        typingEl.remove();

        if (data.success) {
            renderMessage('assistant', data.answer, {
                source: data.source,
                cached: data.cached,
                chunks: data.retrieved_chunks,
                score: data.relevance_score,
                rewritten: data.rewritten_query,
                elapsed
            });
        } else {
            renderMessage('assistant', '⚠️ Something went wrong. Please try again.', null);
        }
    } catch (err) {
        typingEl.remove();
        renderMessage('assistant', '⚠️ Cannot connect to the server. Make sure the backend is running.', null);
        console.error(err);
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// =============================================
// RENDER MESSAGE
// =============================================
function renderMessage(role, content, meta) {
    // Clear welcome screen on first message
    const welcome = chatHistory.querySelector('.welcome-screen');
    if (welcome) welcome.remove();

    const wrap = document.createElement('div');
    wrap.className = `message ${role}`;

    const formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');

    let footer = '';
    if (meta && role === 'assistant') {
        const srcClass = meta.source === 'document' ? 'doc' : 'web';
        const srcLabel = meta.source === 'document' ? '📄 Document' : '🌐 Web Search';
        const cachedBadge  = meta.cached  ? `<span class="badge cache">⚡ Cached</span>` : '';
        const chunksBadge  = meta.chunks  ? `<span class="badge">${meta.chunks} chunks</span>` : '';
        const scoreBadge   = meta.score != null ? `<span class="badge">${(meta.score * 100).toFixed(0)}% match</span>` : '';
        const timeBadge    = meta.elapsed ? `<span class="badge time">${meta.elapsed}s</span>` : '';
        const rewriteBadge = meta.rewritten ? `<span class="badge rewrite" title="Your question was interpreted with context from the conversation">🔄 Interpreted as: ${meta.rewritten}</span>` : '';

        footer = `
            <div class="message-footer">
                <span class="badge ${srcClass}">${srcLabel}</span>
                ${chunksBadge}
                ${scoreBadge}
                ${cachedBadge}
                ${timeBadge}
                ${rewriteBadge}
            </div>`;
    }

    wrap.innerHTML = `<div class="message-bubble">${formatted}</div>${footer}`;
    chatHistory.appendChild(wrap);

    messageCount++;
    msgCount.textContent = messageCount;
    scrollBottom();
}

// =============================================
// TYPING INDICATOR
// =============================================
function showTyping() {
    const el = document.createElement('div');
    el.className = 'typing-wrapper';
    el.innerHTML = `
        <div class="typing-bubble">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>`;
    chatHistory.appendChild(el);
    scrollBottom();
    return el;
}

// =============================================
// SCROLL
// =============================================
function scrollBottom() {
    chatHistory.scrollTo({ top: chatHistory.scrollHeight, behavior: 'smooth' });
}
