"""
Endpoints de serviços
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/")
async def get_services():
    """Listar serviços do usuário"""
    # TODO: Implementar listagem de serviços
    return {"message": "Endpoint de serviços em desenvolvimento"}


@router.post("/")
async def create_service():
    """Criar novo serviço"""
    # TODO: Implementar criação de serviço
    return {"message": "Endpoint de criação de serviço em desenvolvimento"}


@router.get("/{service_id}")
async def get_service(service_id: str):
    """Obter serviço específico"""
    # TODO: Implementar obtenção de serviço
    return {"message": f"Endpoint de serviço {service_id} em desenvolvimento"}


@router.put("/{service_id}")
async def update_service(service_id: str):
    """Atualizar serviço"""
    # TODO: Implementar atualização de serviço
    return {"message": f"Endpoint de atualização de serviço {service_id} em desenvolvimento"}


@router.delete("/{service_id}")
async def delete_service(service_id: str):
    """Deletar serviço"""
    # TODO: Implementar deleção de serviço
    return {"message": f"Endpoint de deleção de serviço {service_id} em desenvolvimento"}
