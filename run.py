import os
import sys
import subprocess
import threading
import time

def run_backend(python_exe):
    print("[Backend] Starting FastAPI server on http://localhost:8000...")
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    # Run uvicorn app.main:app from the backend folder so 'app' is recognized as a package
    cmd = [python_exe, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    try:
        subprocess.run(cmd, cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[Backend] Error: {e}")

def run_frontend(python_exe):
    print("[Frontend] Starting HTTP server on http://localhost:5500...")
    # Run python -m http.server 5500 inside frontend directory
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    cmd = [python_exe, "-m", "http.server", "5500"]
    try:
        subprocess.run(cmd, cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[Frontend] Error: {e}")

def main():
    # Detect virtual environment python
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check for venv python executable on Windows
    venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        # Fallback to Unix/Mac path
        venv_python = os.path.join(root_dir, "venv", "bin", "python")
        
    if os.path.exists(venv_python):
        python_exe = venv_python
        print(f"Using virtual environment Python: {python_exe}")
    else:
        python_exe = sys.executable
        print(f"Virtual environment not found at 'venv'. Using system Python: {python_exe}")
        
    # Launch backend thread
    backend_thread = threading.Thread(target=run_backend, args=(python_exe,), daemon=True)
    backend_thread.start()
    
    # Give backend a moment to start
    time.sleep(1)
    
    # Launch frontend thread
    frontend_thread = threading.Thread(target=run_frontend, args=(python_exe,), daemon=True)
    frontend_thread.start()
    
    print("\n--------------------------------------------------")
    print("Hybrid RAG Assistant is starting up!")
    print("- Backend: http://localhost:8000")
    print("- Frontend: http://localhost:5500")
    print("Press Ctrl+C to stop both servers.")
    print("--------------------------------------------------\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")

if __name__ == "__main__":
    main()
