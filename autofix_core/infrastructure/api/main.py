"""AutoFix FastAPI Backend - v2.7.0 with Reflex Dashboard Integration"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from autofix_core.infrastructure.api.routers import fix, debug, quality
from dotenv import load_dotenv
from autofix_core.shared.helpers.logging_utils import setup_logging, get_logger
from contextlib import asynccontextmanager
import subprocess
import threading
import sys
import os


# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Lifespan events (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("🚀 AutoFix API Starting...")
    logger.info(f"📦 Version: 2.7.0")
    logger.info(f"📚 Docs: http://localhost:8000/docs")
    logger.info(f"🔧 Fix API: /api/v1/fix")
    logger.info("🔒 Quality API: /api/v1/quality")
    logger.info(f"🐛 Debug API: /api/v1/debug")
    logger.info("✅ Startup complete")
    yield
    # Shutdown
    logger.info("👋 AutoFix API Shutting down...")


app = FastAPI(
    title="AutoFix API",
    description="🔧 Automatic Python code error fixing with AI + Deep Debugging",
    version="2.7.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # ← Modern lifespan handling
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Development - allow all (change in production!)
        # Or specific:
        # "http://localhost:3001",
        # "http://localhost:3000",
        # "http://127.0.0.1:3001",
        # "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ==================== Routes ====================

# Include routers (DON'T add prefix - already in routers!)
app.include_router(fix.router)
app.include_router(debug.router)
app.include_router(quality.router)


@app.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "message": "🔧 AutoFix API",
        "version": "2.7.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "fix_api": "/api/v1/fix",
            "debug_api": "/api/v1/debug",
            "dashboard": "http://localhost:3000"  # ← Reflex Dashboard
        },
        "features": {
            "ai_fixing": "Gemini 2.0 with function calling",
            "debugging": "RestrictedPython with variable tracing",
            "sandboxing": "Full code isolation",
            "timeout": "Forced thread termination",
            "dashboard": "Reflex UI for monitoring"
        }
    }


@app.get("/health", tags=["monitoring"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AutoFix API",
        "version": {
            "api": "2.7.0",
            "autofix": "1.0.0"
        },
        "components": {
            "debugger": "healthy",
            "gemini": "conditional",
            "fallback": "healthy",
            "dashboard": "running on port 3000"
        },
        "features": [
            "ai_code_fixing",
            "variable_tracing",
            "sandboxed_execution",
            "timeout_protection",
            "reflex_dashboard"
        ]
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for uncaught errors."""
    logger.error(f"💥 Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


# ==================== Dashboard Integration ====================

def run_fastapi():
    """Run FastAPI server"""
    import uvicorn
    uvicorn.run(
        "autofix_core.infrastructure.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def run_dashboard():
    """Run Reflex Dashboard"""
    dashboard_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        'integrations',
        'reflex_dashboard'
    )
    
    logger.info(f"📊 Starting Reflex Dashboard from: {dashboard_path}")
    
    try:
        subprocess.run(
            ['reflex', 'run'],
            cwd=dashboard_path,
            check=True
        )
    except FileNotFoundError:
        logger.error("❌ Reflex not installed! Run: pip install reflex")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Dashboard failed to start: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")


def run_both():
    """Run both FastAPI and Reflex Dashboard together"""
    logger.info("🚀 Starting AutoFix with Dashboard...")
    
    # Start FastAPI in background thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True, name="FastAPI")
    api_thread.start()
    
    logger.info("✅ FastAPI started on http://localhost:8000")
    logger.info("📊 Starting Dashboard on http://localhost:3000...")
    
    # Run dashboard in main thread (keeps process alive)
    run_dashboard()


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--with-dashboard":
        # Run both API and Dashboard
        run_both()
    else:
        # Run only FastAPI
        logger.info("🚀 Starting AutoFix API only...")
        logger.info("💡 To run with dashboard: python -m autofix_core.infrastructure.api.main --with-dashboard")
        run_fastapi()
