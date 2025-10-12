"""
API pública para vitrines e agendamento sem autenticação
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID
import logging

from app.database import get_db
from app.models.user import User
from app.models.service import Service
from app.models.appointment import Appointment
from app.models.client import Client
from app.services.appointment_service import AppointmentService
from app.services.availability_service import AvailabilityService
from app.services.plan_service import PlanService
from app.services.queue_service import QueueService
from app.services.client_service import ClientService
from app.dependencies import get_redis
from app.schemas.appointment import PublicAppointmentCreate, AppointmentAvailability
from app.schemas.service import ServiceResponse
from app.schemas.client import ClientCreate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/services/{user_id}", response_model=List[ServiceResponse])
async def get_public_services(
    user_id: UUID,
    category_id: Optional[UUID] = Query(None, description="Filtrar por categoria"),
    db: Session = Depends(get_db)
):
    """Obter serviços públicos de um usuário (vitrine)"""
    try:
        # Verificar se o usuário existe e está ativo
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Buscar serviços ativos
        query = db.query(Service).filter(
            Service.user_id == user_id,
            Service.is_active == True
        )
        
        if category_id:
            query = query.filter(Service.category_id == category_id)
        
        services = query.all()
        
        # Converter para response
        services_response = []
        for service in services:
            service_dict = {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "duration": service.duration,
                "price": service.price,
                "category_id": service.category_id,
                "category_name": service.category.name if service.category else None,
                "is_active": service.is_active,
                "created_at": service.created_at,
                "updated_at": service.updated_at
            }
            services_response.append(service_dict)
        
        return services_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter serviços públicos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/services/{user_id}/categories")
async def get_public_service_categories(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Obter categorias de serviços públicas de um usuário"""
    try:
        # Verificar se o usuário existe
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Buscar categorias com serviços ativos
        from app.models.service_category import ServiceCategory
        categories = db.query(ServiceCategory).filter(
            ServiceCategory.user_id == user_id,
            ServiceCategory.is_active == True
        ).all()
        
        categories_response = []
        for category in categories:
            category_dict = {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "is_active": category.is_active,
                "created_at": category.created_at
            }
            categories_response.append(category_dict)
        
        return categories_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter categorias públicas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/availability/{user_id}")
async def get_public_availability(
    user_id: UUID,
    service_id: Optional[UUID] = Query(None, description="ID do serviço"),
    target_date: Optional[date] = Query(None, description="Data para verificar disponibilidade"),
    db: Session = Depends(get_db)
):
    """Obter disponibilidade pública de um usuário"""
    try:
        # Verificar se o usuário existe
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Usar data atual se não fornecida
        if not target_date:
            target_date = date.today()
        
        # Obter serviços
        if service_id:
            services = db.query(Service).filter(
                Service.id == service_id,
                Service.user_id == user_id,
                Service.is_active == True
            ).all()
        else:
            services = db.query(Service).filter(
                Service.user_id == user_id,
                Service.is_active == True
            ).all()
        
        if not services:
            return {
                "date": target_date.isoformat(),
                "available_slots": [],
                "services": []
            }
        
        # Obter disponibilidade
        redis_client = await get_redis()
        availability_service = AvailabilityService(db)
        appointment_service = AppointmentService(
            db, None, None, None, availability_service
        )
        
        available_slots = []
        for service in services:
            slots = appointment_service.get_available_slots(
                user_id, service.id, target_date, service.duration
            )
            
            service_slots = {
                "service_id": service.id,
                "service_name": service.name,
                "duration": service.duration,
                "slots": [slot.isoformat() for slot in slots]
            }
            available_slots.append(service_slots)
        
        return {
            "date": target_date.isoformat(),
            "available_slots": available_slots,
            "user_info": {
                "name": user.email,  # Usar email como nome público
                "whatsapp": user.whatsapp_number
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter disponibilidade pública: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/appointments/{user_id}")
async def create_public_appointment(
    user_id: UUID,
    appointment_data: PublicAppointmentCreate,
    db: Session = Depends(get_db)
):
    """Criar agendamento público (sem autenticação)"""
    try:
        # Verificar se o usuário existe
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Verificar se o serviço existe e está ativo
        service = db.query(Service).filter(
            Service.id == appointment_data.service_id,
            Service.user_id == user_id,
            Service.is_active == True
        ).first()
        
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Serviço não encontrado ou inativo"
            )
        
        # Obter dependências
        redis_client = await get_redis()
        plan_service = PlanService(db, redis_client)
        availability_service = AvailabilityService(db)
        queue_service = QueueService(redis_client) if redis_client else None
        client_service = ClientService(db)
        
        # Criar serviço de agendamento
        appointment_service = AppointmentService(
            db, plan_service, queue_service, client_service, availability_service
        )
        
        # Criar agendamento público
        appointment = await appointment_service.create_public_appointment(
            appointment_data, user_id
        )
        
        # Converter para response
        appointment_response = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "client_name": appointment.client_name,
            "client_whatsapp": appointment.client_whatsapp,
            "client_email": appointment.client_email,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "notes": appointment.notes,
            "source": appointment.source,
            "created_at": appointment.created_at,
            "service": {
                "id": service.id,
                "name": service.name,
                "duration": service.duration,
                "price": service.price
            }
        }
        
        return {
            "success": True,
            "message": "Agendamento criado com sucesso",
            "appointment": appointment_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar agendamento público: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/appointments/{user_id}/{appointment_id}")
async def get_public_appointment(
    user_id: UUID,
    appointment_id: UUID,
    db: Session = Depends(get_db)
):
    """Obter agendamento público por ID"""
    try:
        # Buscar agendamento
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.user_id == user_id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Agendamento não encontrado"
            )
        
        # Converter para response
        appointment_response = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "client_name": appointment.client_name,
            "client_whatsapp": appointment.client_whatsapp,
            "client_email": appointment.client_email,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "notes": appointment.notes,
            "source": appointment.source,
            "created_at": appointment.created_at,
            "service": {
                "id": appointment.service.id,
                "name": appointment.service.name,
                "duration": appointment.service.duration,
                "price": appointment.service.price
            } if appointment.service else None
        }
        
        return appointment_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter agendamento público: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/user/{user_id}/info")
async def get_public_user_info(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Obter informações públicas de um usuário"""
    try:
        # Buscar usuário
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Contar serviços ativos
        services_count = db.query(Service).filter(
            Service.user_id == user_id,
            Service.is_active == True
        ).count()
        
        # Informações públicas
        user_info = {
            "id": user.id,
            "email": user.email,
            "whatsapp": user.whatsapp_number,
            "plan_type": user.plan_type.value,
            "services_count": services_count,
            "is_active": user.is_active == 'Y',
            "created_at": user.created_at
        }
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter informações públicas do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/clients/{user_id}")
async def create_public_client(
    user_id: UUID,
    client_data: ClientCreate,
    db: Session = Depends(get_db)
):
    """Criar cliente público (sem autenticação)"""
    try:
        # Verificar se o usuário existe
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == 'Y'
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_F,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Criar cliente
        client_service = ClientService(db)
        client = await client_service.create_client(client_data, user)
        
        # Converter para response
        client_response = {
            "id": client.id,
            "name": client.name,
            "whatsapp": client.whatsapp,
            "email": client.email,
            "created_at": client.created_at
        }
        
        return {
            "success": True,
            "message": "Cliente criado com sucesso",
            "client": client_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar cliente público: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
