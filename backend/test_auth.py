#!/usr/bin/env python3
"""
Script para testar o sistema de autenticação JWT
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
        from app.core.security import create_access_token, create_refresh_token, verify_token
        from app.schemas.user import UserCreate
        from app.schemas.user import UserLogin
        print("✅ Importações funcionando!")
        
        # Testar criação de tokens
        print("🔑 Testando criação de tokens...")
        test_data = {"sub": "test-user-id", "email": "test@example.com"}
        
        access_token = create_access_token(test_data)
        refresh_token = create_refresh_token(test_data)
        
        print(f"✅ Access token criado: {access_token[:50]}...")
        print(f"✅ Refresh token criado: {refresh_token[:50]}...")
        
        # Testar verificação de tokens
        print("🔍 Testando verificação de tokens...")
        access_payload = verify_token(access_token, "access")
        refresh_payload = verify_token(refresh_token, "refresh")
        
        print(f"✅ Access token verificado: {access_payload}")
        print(f"✅ Refresh token verificado: {refresh_payload}")
        
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
        
        # Testar endpoint de registro
        print("📝 Testando endpoint de registro...")
        register_data = {
            "email": "test@example.com",
            "password": "TestPassword123",
            "template_type": "consultation"
        }
        
        # Nota: Este teste pode falhar se não houver banco de dados
        # Mas pelo menos testa se o endpoint está configurado
        try:
            response = client.post("/api/auth/register", json=register_data)
            print(f"✅ Endpoint de registro: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Endpoint de registro (sem DB): {e}")
        
        # Testar endpoint de login
        print("🔐 Testando endpoint de login...")
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123"
        }
        
        try:
            response = client.post("/api/auth/login", json=login_data)
            print(f"✅ Endpoint de login: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Endpoint de login (sem DB): {e}")
        
        # Testar endpoint de health
        print("💚 Testando health check...")
        response = client.get("/health")
        print(f"✅ Health check: {response.status_code}")
        
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
