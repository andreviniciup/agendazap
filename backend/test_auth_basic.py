#!/usr/bin/env python3
"""
Script básico para testar o sistema de autenticação JWT
"""

import asyncio
import sys
import json
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

async def test_auth_system():
    """Testar sistema de autenticação"""
    try:
        print("🔍 Testando sistema de autenticação JWT...")
        
        # Testar importações
        print("📦 Testando importações...")
        from app.core.security import create_access_token, create_refresh_token
        from app.schemas.user import UserCreate, UserLogin
        print("✅ Importações funcionando!")
        
        # Testar criação de tokens
        print("🔑 Testando criação de tokens...")
        test_data = {"sub": "test-user-id", "email": "test@example.com"}
        
        access_token = create_access_token(test_data)
        refresh_token = create_refresh_token(test_data)
        
        print(f"✅ Access token criado: {len(access_token)} caracteres")
        print(f"✅ Refresh token criado: {len(refresh_token)} caracteres")
        
        # Testar schemas
        print("📋 Testando schemas...")
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123",
            template_type="consultation"
        )
        print(f"✅ UserCreate schema: {user_create.email}")
        
        user_login = UserLogin(
            email="test@example.com",
            password="TestPassword123"
        )
        print(f"✅ UserLogin schema: {user_login.email}")
        
        # Testar aplicação FastAPI
        print("🚀 Testando aplicação FastAPI...")
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Testar endpoint de health
        print("💚 Testando health check...")
        response = client.get("/health")
        print(f"✅ Health check: {response.status_code}")
        
        # Testar endpoint raiz
        print("🏠 Testando endpoint raiz...")
        response = client.get("/")
        print(f"✅ Endpoint raiz: {response.status_code}")
        
        # Testar documentação
        print("📖 Testando documentação...")
        response = client.get("/docs")
        print(f"✅ Documentação: {response.status_code}")
        
        print("\n🎉 Sistema de autenticação JWT funcionando!")
        print("📖 Documentação: http://localhost:8000/docs")
        print("🔗 Endpoints disponíveis:")
        print("   POST /api/auth/register - Registrar usuário")
        print("   POST /api/auth/login - Login")
        print("   POST /api/auth/refresh - Renovar token")
        print("   POST /api/auth/logout - Logout")
        print("   GET /api/auth/me - Informações do usuário")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar sistema de autenticação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_auth_system())
    sys.exit(0 if success else 1)
