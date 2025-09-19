#!/usr/bin/env python3
"""
Script simples para testar o servidor FastAPI
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

async def test_server():
    """Testar se o servidor pode ser importado e executado"""
    try:
        print("🔍 Testando importação da aplicação...")
        from app.main import app
        print("✅ Aplicação importada com sucesso!")
        
        print("🔍 Testando configurações...")
        from app.config import settings
        print(f"✅ Ambiente: {settings.ENVIRONMENT}")
        print(f"✅ Debug: {settings.DEBUG}")
        
        print("🔍 Testando endpoints...")
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Testar endpoint raiz
        response = client.get("/")
        print(f"✅ Endpoint raiz: {response.status_code}")
        
        # Testar health check
        response = client.get("/health")
        print(f"✅ Health check: {response.status_code}")
        
        if response.status_code == 200:
            print("🎉 Servidor funcionando perfeitamente!")
            print("📖 Documentação: http://localhost:8000/docs")
            print("🔗 API: http://localhost:8000")
            return True
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar servidor: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)
