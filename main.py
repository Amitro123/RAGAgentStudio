"""
Main FastAPI server entry point for RAGAgent Studio
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.ws.websocket import router as ws_router
from app.config import settings
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="RAGAgent Studio",
    description="Build AI agents from PDF documents with Gemini File Search",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1", tags=["API"])
app.include_router(ws_router, tags=["WebSocket"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "gemini_api": "configured" if settings.GEMINI_API_KEY else "missing"
    }

@app.on_event("startup")
async def startup_event():
    """On startup"""
    logger.info("=" * 60)
    logger.info("🚀 RAGAgent Studio Starting")
    logger.info("=" * 60)
    logger.info(f"📁 Uploads: {settings.UPLOAD_DIR}")
    logger.info(f"🔌 MindsDB: {settings.MINDSDB_HOST}")
    logger.info(f"📚 API Docs: http://localhost:8000/docs")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """On shutdown"""
    logger.info("🛑 RAGAgent Studio Shutting Down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
