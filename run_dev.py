"""Development runner for AutoFix + Dashboard"""
import subprocess
import threading
import time
import sys


def run_fastapi():
    """Run FastAPI"""
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'autofix_core.infrastructure.api.main:app',
        '--reload',
        '--port', '8000'
    ])


def run_dashboard():
    """Run Reflex Dashboard"""
    subprocess.run([
        'reflex', 'run'
    ], cwd='autofix_core/infrastructure/integrations/reflex_dashboard')


if __name__ == "__main__":
    print("🚀 Starting AutoFix Development Environment...")
    
    # Start FastAPI in background
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # Wait a bit for API to start
    time.sleep(2)
    
    print("✅ FastAPI: http://localhost:8000")
    print("📊 Starting Dashboard: http://localhost:3000")
    
    # Run dashboard (keeps main thread alive)
    run_dashboard()
