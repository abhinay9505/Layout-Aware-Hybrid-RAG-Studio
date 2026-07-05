import os
import sys
import time
import signal
import subprocess

def main():
    print("==========================================================")
    print("  🧠 Starting RAG Studio Full-Stack Platform")
    print("==========================================================")

    # Resolve absolute paths
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    python_exe = sys.executable

    # 1. Start Backend FastAPI Server
    print("🚀 Launching Backend API Server (FastAPI)...")
    env = os.environ.copy()
    # Add backend to PYTHONPATH to allow imports to work correctly
    env["PYTHONPATH"] = backend_dir
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"

    backend_cmd = [
        python_exe, "-m", "uvicorn", "app.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        env=env
    )

    # 2. Start Frontend Server
    print("🎨 Launching Frontend Static Server (http.server)...")
    frontend_cmd = [
        python_exe, "-m", "http.server", "5500", 
        "--bind", "0.0.0.0"
    ]
    
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir
    )

    print("\n----------------------------------------------------------")
    print("  Services Started Successfully:")
    print("  👉 Frontend Interface : http://localhost:5500")
    print("  👉 Backend API Server : http://localhost:8000")
    print("  👉 API documentation  : http://localhost:8000/docs")
    print("----------------------------------------------------------")
    print("  Press Ctrl+C to terminate both servers.")
    print("==========================================================\n")

    # Flag to handle clean shutdown once
    shutdown_initiated = False

    def shutdown_servers(signum, frame):
        nonlocal shutdown_initiated
        if shutdown_initiated:
            return
        shutdown_initiated = True
        print("\nStopping full-stack servers...")
        
        # Terminate processes
        try:
            print("Terminating backend process...")
            backend_proc.terminate()
        except Exception as e:
            print(f"Error terminating backend: {e}")
            
        try:
            print("Terminating frontend process...")
            frontend_proc.terminate()
        except Exception as e:
            print(f"Error terminating frontend: {e}")
            
        # Wait for shutdown completion
        backend_proc.wait()
        frontend_proc.wait()
        print("All servers stopped successfully. Goodbye!")
        sys.exit(0)

    # Bind exit signals
    signal.signal(signal.SIGINT, shutdown_servers)
    signal.signal(signal.SIGTERM, shutdown_servers)

    # Main monitoring loop
    try:
        while True:
            # Check if backend crashed
            backend_exit = backend_proc.poll()
            if backend_exit is not None:
                print(f"\n❌ Backend process exited unexpectedly with code {backend_exit}.")
                shutdown_servers(None, None)

            # Check if frontend crashed
            frontend_exit = frontend_proc.poll()
            if frontend_exit is not None:
                print(f"\n❌ Frontend process exited unexpectedly with code {frontend_exit}.")
                shutdown_servers(None, None)

            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_servers(None, None)

if __name__ == "__main__":
    main()
