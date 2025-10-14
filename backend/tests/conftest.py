"""
Configuração para testes - define variáveis de ambiente necessárias
"""

import os

# Definir variáveis de ambiente para testes
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("ALLOWED_HOSTS", '["localhost"]')
os.environ.setdefault("USE_N8N", "false")
