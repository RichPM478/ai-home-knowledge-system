from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime
import logging

# Import our services and API routers
from app.api.endpoints import connectors
from app.services.vector_service import vector_service
from app.services.chat_service import chat_service
from app.models.schemas import ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Home Knowledge Discovery System - Enhanced",
    description="Personal AI system with vector search and semantic understanding",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(connectors.router, prefix="/connectors", tags=["connectors"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting up AI Home Knowledge Discovery System...")
        # Vector service will initialize when first used
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}")

@app.get("/")
async def root():
    return {
        "message": "AI Home Knowledge Discovery System - Enhanced",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Vector embeddings with semantic search",
            "Real-time sync progress tracking", 
            "Enhanced chat with context understanding",
            "Multiple email connector support"
        ],
        "endpoints": {
            "health": "/health",
            "connectors": "/connectors",
            "chat": "/chat",
            "search": "/search",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

@app.get("/health/")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Home Knowledge Discovery System Enhanced",
        "vector_db": "ChromaDB with sentence-transformers"
    }

@app.post("/chat/")
async def enhanced_chat(message: ChatMessage):
    """Enhanced chat with semantic search and intelligent responses"""
    try:
        logger.info(f"Processing chat message: {message.message}")
        
        # Use enhanced chat service
        response = await chat_service.process_message(message)
        
        return response
        
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/")
async def semantic_search(query: dict):
    """Direct semantic search endpoint"""
    try:
        search_query = query.get("query", "")
        limit = query.get("limit", 10)
        
        if not search_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Perform semantic search
        results = await vector_service.semantic_search(search_query, limit)
        
        return {
            "query": search_query,
            "results": [
                {
                    "content": result.content,
                    "metadata": result.metadata,
                    "score": result.score
                }
                for result in results
            ],
            "total_results": len(results)
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/")
async def get_system_stats():
    """Get system statistics"""
    try:
        # Get vector database stats
        vector_stats = await vector_service.get_stats()
        
        # Get connector stats
        from app.api.endpoints.connectors import active_connectors, sync_status
        
        connector_stats = {
            "total_connectors": len(active_connectors),
            "connected_connectors": sum(1 for c in active_connectors.values() if c.status.value == "connected"),
            "sync_status": {cid: status for cid, status in sync_status.items()}
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "vector_database": vector_stats,
            "connectors": connector_stats,
            "system_status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )