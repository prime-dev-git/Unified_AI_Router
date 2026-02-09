"""
Configuration module: Loads environment variables with Ollama support.
Ollama settings are optional (local inference doesn't require API keys).
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Validated application settings from environment variables"""
    
    # Cloud provider API keys (required for cloud APIs)
    openai_api_key: str
    anthropic_api_key: str
    gemini_api_key: str
    
    # Ollama configuration (optional - local inference)
    ollama_host: str = "http://localhost:11434"  # Default Ollama endpoint
    default_ollama_model: str = "llama3.2:3b"
    
    # Default models for cloud providers
    default_openai_model: str = "gpt-4o-mini"
    default_anthropic_model: str = "claude-3-5-sonnet-20241022"
    default_gemini_model: str = "gemini-1.5-flash"
    
    # Security: CORS configuration
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated string to list for CORS middleware"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    @property
    def is_ollama_available(self) -> bool:
        """Check if Ollama should be enabled (host configured)"""
        return bool(self.ollama_host.strip())
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Initialize settings (cloud keys required, Ollama optional)
try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(
        "❌ Configuration error! Check .env file. Required keys: "
        "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY\n"
        f"Details: {str(e)}"
    )

# Export for other modules
__all__ = ["settings"]