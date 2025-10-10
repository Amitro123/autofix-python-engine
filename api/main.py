"""AutoFix FastAPI Backend - v2.0.0"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import fix
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(
    title="AutoFix API",
    description="🔧 Automatic Python code error fixing",
    version="2.0.0",
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

@app.get("/") #maybe remove strings to constants file later amitro
def root():
    return {
        "message": "🔧 AutoFix API",
        "version": "2.0.0",
        "docs": "http://localhost:8000/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "autofix": "1.0.0", "api": "2.0.0"}
