# 🎨 Hybrid RAG Frontend

A sleek, **glassmorphism-themed** chat interface for the Hybrid RAG Assistant. Built with pure **Vanilla HTML, CSS, and JavaScript** — no frameworks, no build step required.

---

## 📁 Project Structure

```
frontend/
├── index.html    # Main application shell & layout
├── styles.css    # Complete design system (glassmorphism, animations, dark mode)
└── script.js     # Application logic (chat, uploads, sessions)
```

---

## ✨ Features

| Feature               | Description                                                  |
|-----------------------|--------------------------------------------------------------|
| 💬 **Real-time Chat**  | Send queries and get AI responses with source metadata       |
| 📄 **Document Upload** | Drag & drop or click-to-upload PDF/DOCX files               |
| 📂 **Document Manager**| View and delete uploaded documents from the sidebar          |
| 🏷️ **Source Labels**   | Every response is tagged as `📄 Document` or `🌐 Web Search`|
| ⚡ **Cache Badges**    | Visual indicator when a response is served from cache        |
| 🕐 **Session Memory**  | Persistent sessions via `localStorage` with UUID tracking    |
| 📊 **Live Stats**      | Real-time document count and message count in the sidebar    |
| 🎯 **Relevance Score** | Percentage match score displayed on document-sourced answers |
| 🔔 **Toast Alerts**    | Non-intrusive notifications for uploads, errors, and actions |
| ✅ **Confirm Modals**   | Safe delete/clear operations with confirmation dialogs       |

---

## 🚀 How to Run

### Option 1 — Open Directly (Simplest)

Just double-click `index.html` in your file explorer or open it in any browser:

```
file:///path/to/RAG/frontend/index.html
```

> ⚠️ Some browsers restrict `fetch()` calls from `file://` URLs. If you see CORS errors, use Option 2 instead.

### Option 2 — Local HTTP Server (Recommended)

**Using Python:**

```bash
cd frontend
python -m http.server 5500
```

Then open **`http://localhost:5500`** in your browser.

**Using Node.js:**

```bash
npx -y serve ./frontend -l 5500
```

Then open **`http://localhost:5500`** in your browser.

**Using VS Code:**

1. Install the **Live Server** extension
2. Right-click `index.html` → **Open with Live Server**
3. It will auto-open at `http://127.0.0.1:5500`

---

## ⚙️ Configuration

The frontend connects to the backend API at:

```javascript
const API = 'http://localhost:8000/api/v1';
```

This is defined at the top of `script.js` (line 4). Update it if your backend runs on a different host or port.

---

## 🔗 Backend Requirements

The frontend expects the backend server to be running at `http://localhost:8000`. Make sure:

1. The backend is started (`uvicorn app.main:app --reload --port 8000`)
2. CORS is enabled on the backend (the backend includes CORS middleware)
3. MongoDB and Redis services are running

Without the backend, the UI will load but chat and upload features will show connection errors.

---

## 🎨 Design System

- **Theme**: Dark mode with glassmorphism (frosted glass panels)
- **Typography**: [Outfit](https://fonts.google.com/specimen/Outfit) (headings) + [Inter](https://fonts.google.com/specimen/Inter) (body)
- **Animations**: Smooth micro-animations on hover, typing indicator, upload progress
- **Layout**: Responsive sidebar + main chat area
- **Colors**: Indigo/violet accent palette with subtle gradients

---

## 🖥️ Browser Compatibility

| Browser        | Support |
|----------------|---------|
| Chrome 90+     | ✅       |
| Firefox 90+    | ✅       |
| Edge 90+       | ✅       |
| Safari 15+     | ✅       |

Requires modern JavaScript features: `crypto.randomUUID()`, `fetch()`, `async/await`, `localStorage`.
