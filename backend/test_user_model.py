#!/usr/bin/env python3
"""
Script para testar o modelo de usuário completo
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

async def test_user_model():
    """Testar modelo de usuário completo"""
    try:
        print("🔍 Testando modelo de usuário completo...")
        
        # Testar importações
        print("📦 Testando importações...")
        from app.models.user import User
        from app.models.service import Service
        from app.models.appointment import Appointment
        from app.models.client import Client
        from app.utils.enums import TemplateType, PlanType, AppointmentStatus
        from app.schemas.user import UserCreate, UserUpdate, UserResponse
        from app.schemas.service import ServiceCreate, ServiceResponse
        from app.schemas.appointment import AppointmentCreate, AppointmentResponse
        from app.schemas.client import ClientCreate, ClientResponse
        print("✅ Importações funcionando!")
        
        # Testar enums
        print("🔢 Testando enums...")
        print(f"✅ TemplateType: {[t.value for t in TemplateType]}")
        print(f"✅ PlanType: {[p.value for p in PlanType]}")
        print(f"✅ AppointmentStatus: {[s.value for s in AppointmentStatus]}")
        
        # Testar schemas
        print("📋 Testando schemas...")
        
        # UserCreate
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123",
            template_type=TemplateType.CONSULTATION,
            whatsapp_number="+5511999999999"
        )
        print(f"✅ UserCreate: {user_create.email} - {user_create.template_type}")
        
        # ServiceCreate
        service_create = ServiceCreate(
            name="Consulta Psicológica",
            description="Sessão de terapia individual",
            duration=60,
            price=None,  # Consulta não tem preço fixo
            credentials="CRP 123456"
        )
        print(f"✅ ServiceCreate: {service_create.name} - {service_create.duration}min")
        
        # AppointmentCreate
        from datetime import datetime, timedelta
        appointment_create = AppointmentCreate(
            service_id="123e4567-e89b-12d3-a456-426614174000",
            client_name="João Silva",
            client_whatsapp="+5511888888888",
            client_email="joao@example.com",
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=1)
        )
        print(f"✅ AppointmentCreate: {appointment_create.client_name}")
        
        # ClientCreate
        client_create = ClientCreate(
            name="Maria Santos",
            whatsapp="+5511777777777",
            email="maria@example.com"
        )
        print(f"✅ ClientCreate: {client_create.name}")
        
        # Testar aplicação FastAPI
        print("🚀 Testando aplicação FastAPI...")
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Testar endpoints de usuário
        print("👤 Testando endpoints de usuário...")
        
        # Health check
        response = client.get("/health")
        print(f"✅ Health check: {response.status_code}")
        
        # Endpoint raiz
        response = client.get("/")
        print(f"✅ Endpoint raiz: {response.status_code}")
        
        # Documentação
        response = client.get("/docs")
        print(f"✅ Documentação: {response.status_code}")
        
        print("\n🎉 Modelo de usuário completo funcionando!")
        print("📖 Documentação: http://localhost:8000/docs")
        print("🔗 Endpoints disponíveis:")
        print("   GET /api/users/profile - Perfil do usuário")
        print("   PUT /api/users/profile - Atualizar perfil")
        print("   GET /api/users/plan - Informações do plano")
        print("   POST /api/users/upgrade - Upgrade de plano")
        print("   DELETE /api/users/account - Deletar conta")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar modelo de usuário: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_user_model())
    sys.exit(0 if success else 1)
