"""
Endpoints de agendamentos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date
import logging

from app.database import get_db
from app.dependencies import get_current_active_user, get_appointment_service
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentList, AppointmentStats,
    AppointmentSearch, PublicAppointmentCreate, AppointmentConfirmation, AppointmentCancellation,
    AppointmentAvailability
)
from app.models.user import User
from app.services.appointment_service import AppointmentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=AppointmentList)
async def get_appointments(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    query: str = Query(None, description="Termo de busca"),
    service_id: UUID = Query(None, description="Filtrar por serviço"),
    client_id: UUID = Query(None, description="Filtrar por cliente"),
    status: str = Query(None, description="Filtrar por status"),
    start_date: date = Query(None, description="Data inicial"),
    end_date: date = Query(None, description="Data final"),
    is_today: bool = Query(None, description="Apenas agendamentos de hoje"),
    is_tomorrow: bool = Query(None, description="Apenas agendamentos de amanhã"),
    is_past: bool = Query(None, description="Apenas agendamentos passados"),
    is_future: bool = Query(None, description="Apenas agendamentos futuros"),
    sort_by: str = Query("start_time", description="Campo para ordenação"),
    sort_order: str = Query("asc", description="Ordem da ordenação"),
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Obter agendamentos do usuário com filtros e paginação"""
    try:
        # Criar parâmetros de busca
        search_params = AppointmentSearch(
            query=query,
            service_id=service_id,
            client_id=client_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            is_today=is_today,
            is_tomorrow=is_tomorrow,
            is_past=is_past,
            is_future=is_future,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        result = appointment_service.get_appointments(current_user, search_params, page, per_page)
        
        # Converter agendamentos para response
        appointments_response = []
        for appointment in result["appointments"]:
            appointment_dict = {
                "id": appointment.id,
                "service_id": appointment.service_id,
                "user_id": appointment.user_id,
                "client_id": appointment.client_id,
                "client_name": appointment.client_name,
                "client_whatsapp": appointment.client_whatsapp,
                "client_email": appointment.client_email,
                "start_time": appointment.start_time,
                "end_time": appointment.end_time,
                "duration_minutes": appointment.duration_minutes,
                "status": appointment.status,
                "is_confirmed": appointment.is_confirmed,
                "is_cancelled": appointment.is_cancelled,
                "is_completed": appointment.is_completed,
                "notes": appointment.notes,
                "internal_notes": appointment.internal_notes,
                "reminder_sent": appointment.reminder_sent,
                "confirmation_sent": appointment.confirmation_sent,
                "source": appointment.source,
                "custom_fields": appointment.custom_fields,
                "created_at": appointment.created_at,
                "updated_at": appointment.updated_at,
                "service": None,
                "client": None
            }
            
            # Adicionar informações do serviço se existir
            if appointment.service:
                appointment_dict["service"] = {
                    "id": appointment.service.id,
                    "name": appointment.service.name,
                    "duration": appointment.service.duration,
                    "price": appointment.service.price
                }
            
            # Adicionar informações do cliente se existir
            if appointment.client:
                appointment_dict["client"] = {
                    "id": appointment.client.id,
                    "name": appointment.client.name,
                    "whatsapp": appointment.client.whatsapp
                }
            
            appointments_response.append(appointment_dict)
        
        return AppointmentList(
            appointments=appointments_response,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"]
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter agendamentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Criar novo agendamento"""
    try:
        appointment = await appointment_service.create_appointment(appointment_data, current_user)
        
        # Converter para response
        appointment_response = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "user_id": appointment.user_id,
            "client_id": appointment.client_id,
            "client_name": appointment.client_name,
            "client_whatsapp": appointment.client_whatsapp,
            "client_email": appointment.client_email,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "is_confirmed": appointment.is_confirmed,
            "is_cancelled": appointment.is_cancelled,
            "is_completed": appointment.is_completed,
            "notes": appointment.notes,
            "internal_notes": appointment.internal_notes,
            "reminder_sent": appointment.reminder_sent,
            "confirmation_sent": appointment.confirmation_sent,
            "source": appointment.source,
            "custom_fields": appointment.custom_fields,
            "created_at": appointment.created_at,
            "updated_at": appointment.updated_at,
            "service": None,
            "client": None
        }
        
        return appointment_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar agendamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Obter agendamento específico"""
    try:
        appointment = appointment_service.get_appointment(appointment_id, current_user)
        
        # Converter para response
        appointment_response = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "user_id": appointment.user_id,
            "client_id": appointment.client_id,
            "client_name": appointment.client_name,
            "client_whatsapp": appointment.client_whatsapp,
            "client_email": appointment.client_email,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "is_confirmed": appointment.is_confirmed,
            "is_cancelled": appointment.is_cancelled,
            "is_completed": appointment.is_completed,
            "notes": appointment.notes,
            "internal_notes": appointment.internal_notes,
            "reminder_sent": appointment.reminder_sent,
            "confirmation_sent": appointment.confirmation_sent,
            "source": appointment.source,
            "custom_fields": appointment.custom_fields,
            "created_at": appointment.created_at,
            "updated_at": appointment.updated_at,
            "service": None,
            "client": None
        }
        
        return appointment_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter agendamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    appointment_data: AppointmentUpdate,
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Atualizar agendamento"""
    try:
        appointment = appointment_service.update_appointment(appointment_id, appointment_data, current_user)
        
        # Converter para response
        appointment_response = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "user_id": appointment.user_id,
            "client_id": appointment.client_id,
            "client_name": appointment.client_name,
            "client_whatsapp": appointment.client_whatsapp,
            "client_email": appointment.client_email,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "is_confirmed": appointment.is_confirmed,
            "is_cancelled": appointment.is_cancelled,
            "is_completed": appointment.is_completed,
            "notes": appointment.notes,
            "internal_notes": appointment.internal_notes,
            "reminder_sent": appointment.reminder_sent,
            "confirmation_sent": appointment.confirmation_sent,
            "source": appointment.source,
            "custom_fields": appointment.custom_fields,
            "created_at": appointment.created_at,
            "updated_at": appointment.updated_at,
            "service": None,
            "client": None
        }
        
        return appointment_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar agendamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Deletar agendamento"""
    try:
        appointment_service.delete_appointment(appointment_id, current_user)
        return {"message": "Agendamento deletado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar agendamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/stats/overview", response_model=AppointmentStats)
async def get_appointment_stats(
    current_user: User = Depends(get_current_active_user),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """Obter estatísticas dos agendamentos"""
    try:
        stats = appointment_service.get_appointment_stats(current_user)
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de agendamentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
