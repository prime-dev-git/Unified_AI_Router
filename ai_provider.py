"""
AI Provider Integrations: Unified interface for cloud + local (Ollama) LLMs.
All functions return normalized responses with consistent error handling.
"""
import httpx
import ollama  # Official Ollama client
from typing import Dict, Any, Optional
from config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Timeout configuration (prevents hanging requests)
TIMEOUT_CONFIG = httpx.Timeout(30.0, connect=10.0)

# ===== CLOUD PROVIDERS (unchanged from previous implementation) =====

async def call_openai(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7
) -> str:
    """Call OpenAI API with normalized request/response"""
    api_key = settings.openai_api_key
    model = model or settings.default_openai_model
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("error", {}).get("message", str(e))
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"OpenAI API Error: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI request failed: {str(e)}"
        )

async def call_anthropic(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7
) -> str:
    """Call Anthropic API with normalized request/response"""
    api_key = settings.anthropic_api_key
    model = model or settings.default_anthropic_model
    max_tokens = max(1, min(max_tokens, 4096))
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"].strip()
    
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("error", {}).get("message", str(e))
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Anthropic API Error: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Anthropic request failed: {str(e)}"
        )

async def call_gemini(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7
) -> str:
    """Call Google Gemini API with normalized request/response"""
    api_key = settings.gemini_api_key
    model_name = model or settings.default_gemini_model
    # Gemini API expects model name without "gemini-" prefix in URL
    api_model = model_name.replace("gemini-", "") if model_name.startswith("gemini-") else model_name
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent",
                params={"key": api_key},
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("error", {}).get("message", str(e))
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gemini API Error: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {str(e)}"
        )

# ===== OLLAMA PROVIDER (NEW - Local LLMs) =====

async def call_ollama(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7
) -> str:
    """
    Call Ollama (local LLM server) with normalized request/response.
    Uses official Ollama Python client for reliability.
    """
    if not settings.is_ollama_available:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not configured. Set OLLAMA_HOST in .env"
        )
    
    model = model or settings.default_ollama_model
    
    try:
        # Ollama client handles connection to localhost:11434 by default
        # We use synchronous client since Ollama's Python lib isn't async-native
        # (Wrapped in async function for unified interface)
        logger.info(f"Calling Ollama with model: {model}")
        
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={
                "temperature": temperature,
                "num_predict": max_tokens
            }
        )
        
        return response["response"].strip()
    
    except ollama.ResponseError as e:
        # Handle Ollama-specific errors (model not found, server down, etc.)
        if "model not found" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail=f"Ollama model '{model}' not found. Run: ollama pull {model}"
            )
        elif "connection" in str(e).lower() or "refused" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail=f"Ollama server not running at {settings.ollama_host}. Start with: ollama serve"
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama error: {str(e)}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama request failed: {str(e)}"
        )

# ===== PROVIDER REGISTRY =====
PROVIDER_MAP = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "ollama": call_ollama  # NEW!
}

def get_provider_function(provider: str):
    """Safely retrieve provider function with validation"""
    provider = provider.lower()
    
    if provider not in PROVIDER_MAP:
        available = list(PROVIDER_MAP.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: '{provider}'. Available: {available}"
        )
    
    # Special check for Ollama availability
    if provider == "ollama" and not settings.is_ollama_available:
        raise HTTPException(
            status_code=400,
            detail="Ollama provider requested but not configured. Set OLLAMA_HOST in .env"
        )
    
    return PROVIDER_MAP[provider]