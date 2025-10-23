"""AutoFix FastAPI Backend - v2.7.0"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from autofix_core.infrastructure.api.routers import fix, debug, quality
from dotenv import load_dotenv
from autofix.helpers.logging_utils import setup_logging, get_logger
from contextlib import asynccontextmanager

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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
        "message": "🔧 AutoFix API",  # ← Simplified for tests
        "version": "2.7.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "fix_api": "/api/v1/fix",
            "debug_api": "/api/v1/debug"
        },
        "features": {
            "ai_fixing": "Gemini 2.0 with function calling",
            "debugging": "RestrictedPython with variable tracing",
            "sandboxing": "Full code isolation",
            "timeout": "Forced thread termination"
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
            "fallback": "healthy"
        },
        "features": [
            "ai_code_fixing",
            "variable_tracing",
            "sandboxed_execution",
            "timeout_protection"
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


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting AutoFix API directly...")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
