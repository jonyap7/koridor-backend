from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database - supports both SQLite (dev) and PostgreSQL (prod)
    DATABASE_URL: str = "sqlite:///./partimer.db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # JWT/Auth (in production, use proper secret management)
    SECRET_KEY: str = "development-secret-key-change-in-production"
    
    # WhatsApp Business API (for future phase)
    WHATSAPP_API_URL: str = ""
    WHATSAPP_API_TOKEN: str = ""
    
    # Payment Gateway (for future phase)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
