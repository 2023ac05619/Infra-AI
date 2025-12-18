"""FastAPI main application"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from app.db import init_db, engine
from app.core.engine import get_engine
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("[STARTUP] Initializing InfraAI Backend...")
    
    # Initialize database
    await init_db()
    print("[STARTUP] Database initialized")
    
    # Initialize LangGraph engine
    get_engine()
    print("[STARTUP] LangGraph engine initialized")
    
    print("[STARTUP] InfraAI Backend ready")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] Closing connections...")
    await engine.dispose()
    print("[SHUTDOWN] InfraAI Backend stopped")


# Create FastAPI app
app = FastAPI(
    title="InfraAI AIOps Backend",
    description="Intelligent AIOps platform with autonomous remediation",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "InfraAI",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
