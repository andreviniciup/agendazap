"""
Endpoints de agendamentos
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/")
async def get_appointments():
    """Listar agendamentos do usuário"""
    # TODO: Implementar listagem de agendamentos
    return {"message": "Endpoint de agendamentos em desenvolvimento"}


@router.post("/")
async def create_appointment():
    """Criar novo agendamento"""
    # TODO: Implementar criação de agendamento
    return {"message": "Endpoint de criação de agendamento em desenvolvimento"}


@router.get("/{appointment_id}")
async def get_appointment(appointment_id: str):
    """Obter agendamento específico"""
    # TODO: Implementar obtenção de agendamento
    return {"message": f"Endpoint de agendamento {appointment_id} em desenvolvimento"}


@router.put("/{appointment_id}")
async def update_appointment(appointment_id: str):
    """Atualizar agendamento"""
    # TODO: Implementar atualização de agendamento
    return {"message": f"Endpoint de atualização de agendamento {appointment_id} em desenvolvimento"}


@router.delete("/{appointment_id}")
async def delete_appointment(appointment_id: str):
    """Deletar agendamento"""
    # TODO: Implementar deleção de agendamento
    return {"message": f"Endpoint de deleção de agendamento {appointment_id} em desenvolvimento"}
