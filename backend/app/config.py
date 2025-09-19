"""
Configurações da aplicação AgendaZap
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # Ambiente
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://agendazap.com",
        "https://www.agendazap.com"
    ]
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "agendazap.com",
        "www.agendazap.com"
    ]
    
    # Banco de dados
    DATABASE_URL: str = "postgresql://agendazap:agendazap123@localhost:5432/agendazap"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: str = "+14155238886"  # Número sandbox do Twilio
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@agendazap.com"
    
    # n8n
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook"
    N8N_API_KEY: Optional[str] = None
    
    # Limites por plano
    FREE_APPOINTMENTS_LIMIT: int = 10
    STARTER_MESSAGES_LIMIT: int = 200
    PRO_MESSAGES_LIMIT: int = 500
    ENTERPRISE_MESSAGES_LIMIT: int = 1000
    
    # Cache TTL (em segundos)
    CACHE_TTL_AGENDA: int = 3600  # 1 hora
    CACHE_TTL_SERVICES: int = 86400  # 24 horas
    CACHE_TTL_TEMPLATES: int = 0  # Sem expiração
    
    # Upload de arquivos
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    UPLOAD_DIR: str = "uploads"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # segundos
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT deve ser: development, staging ou production")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global das configurações
settings = Settings()


# Configurações específicas por ambiente
def get_database_url() -> str:
    """Retorna a URL do banco baseada no ambiente"""
    if settings.ENVIRONMENT == "production":
        return settings.DATABASE_URL
    elif settings.ENVIRONMENT == "staging":
        return settings.DATABASE_URL.replace("agendazap", "agendazap_staging")
    else:
        return settings.DATABASE_URL


def get_redis_url() -> str:
    """Retorna a URL do Redis baseada no ambiente"""
    if settings.ENVIRONMENT == "production":
        return settings.REDIS_URL
    elif settings.ENVIRONMENT == "staging":
        return settings.REDIS_URL.replace("/0", "/1")
    else:
        return settings.REDIS_URL


# Configurações de logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/agendazap.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "sqlalchemy": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
