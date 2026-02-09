"""
Main FastAPI Application: Single route handling all AI provider requests.
Features:
- Unified request/response schema
- Automatic provider routing
- CORS protection
- Structured error handling
- Request validation
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import ai_provider
from  ai_provider import get_provider_function, PROVIDER_MAP
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Unified AI Router",
    description="Single endpoint to route requests to multiple AI providers",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc" # ReDoc
)

# Security: Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Request/Response Models (Pydantic validation)
class AIRequest(BaseModel):
    """Unified request schema for all providers"""
    provider: str = Field(..., description="AI provider name (openai, anthropic, gemini)")
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt")
    model: Optional[str] = Field(None, description="Model name (uses default if omitted)")
    max_tokens: Optional[int] = Field(500, ge=1, le=4096, description="Max response tokens")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")

class AIResponse(BaseModel):
    """Normalized response schema"""
    provider: str
    model: str
    response: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

@app.post("/ai/chat", response_model=AIResponse, summary="Route to any AI provider")
async def chat_endpoint(request: AIRequest):
    """
    Unified endpoint for all AI providers.
    
    How it works:
    1. Validates provider name against supported list
    2. Routes to appropriate provider function
    3. Returns normalized response
    4. Handles all errors with proper HTTP status codes
    
    Example request:
    {
      "provider": "openai",
      "prompt": "Explain quantum computing simply",
      "temperature": 0.5
    }
    """
    try:
        # Get provider function (validates provider name)
        provider_func = get_provider_function(request.provider.lower())
        
        # Log request (without sensitive data)
        logger.info(f"Routing to {request.provider} | Model: {request.model or 'default'} | Tokens: {request.max_tokens}")
        
        # Call provider API (handles its own error raising)
        response_text = await provider_func(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Return normalized response
        return AIResponse(
            provider=request.provider,
            model=request.model or "default",
            response=response_text
        )
    
    except HTTPException:
        # Re-raise provider-specific HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors (never expose stack traces in prod!)
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing AI request"
        )

@app.get("/health")
async def health_check():
    """Health check with provider availability status"""
    providers = {
        "openai": True,
        "anthropic": True,
        "gemini": True,
        "ollama": settings.is_ollama_available
    }
    return {
        "status": "healthy",
        "providers": providers,
        "ollama_host": settings.ollama_host if settings.is_ollama_available else None
    }

# Startup event (optional but useful)
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Unified AI Router started")
    logger.info(f"SupportedContent: {list(PROVIDER_MAP.keys())}")
    logger.info(f"CORS enabled for: {settings.cors_origins_list}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production!
        log_level="info"
    )