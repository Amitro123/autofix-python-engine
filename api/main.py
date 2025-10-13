"""AutoFix FastAPI Backend - v2.2.3"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import fix
from dotenv import load_dotenv
from autofix.helpers.logging_utils import setup_logging 
import sys


load_dotenv()

# Setup logging for FastAPI
setup_logging()


app = FastAPI(
    title="AutoFix API",
    description="🔧 Automatic Python code error fixing with AI",
    version="2.2.3",
    docs_url="/docs"
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
app.include_router(fix.router, prefix="/api/v1", tags=["fix"])


@app.get("/")
def root():
    return {
        "message": "🔧 AutoFix API",
        "version": "2.2.3",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy", "autofix": "1.0.0", "api": "2.2.3"}
