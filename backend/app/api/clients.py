"""
Endpoints para gestão de clientes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from app.database import get_db
from app.dependencies import get_current_active_user, get_client_service
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientList, ClientStats,
    ClientSearch, ClientBulkUpdate, ClientHistory, ClientAnalytics
)
from app.models.user import User
from app.services.client_service import ClientService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=ClientList)
async def get_clients(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    query: str = Query(None, description="Termo de busca"),
    is_active: bool = Query(None, description="Filtrar por status ativo"),
    is_vip: bool = Query(None, description="Filtrar por clientes VIP"),
    is_regular: bool = Query(None, description="Filtrar por clientes regulares"),
    is_frequent: bool = Query(None, description="Filtrar por clientes frequentes"),
    min_appointments: int = Query(None, ge=0, description="Mínimo de agendamentos"),
    max_appointments: int = Query(None, ge=0, description="Máximo de agendamentos"),
    min_frequency_score: float = Query(None, ge=0, le=100, description="Score mínimo de frequência"),
    max_frequency_score: float = Query(None, ge=0, le=100, description="Score máximo de frequência"),
    city: str = Query(None, description="Filtrar por cidade"),
    state: str = Query(None, description="Filtrar por estado"),
    source: str = Query(None, description="Filtrar por fonte"),
    sort_by: str = Query("name", description="Campo para ordenação"),
    sort_order: str = Query("asc", description="Ordem da ordenação"),
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Obter clientes do usuário com filtros e paginação"""
    try:
        # Criar parâmetros de busca
        search_params = ClientSearch(
            query=query,
            is_active=is_active,
            is_vip=is_vip,
            is_regular=is_regular,
            is_frequent=is_frequent,
            min_appointments=min_appointments,
            max_appointments=max_appointments,
            min_frequency_score=min_frequency_score,
            max_frequency_score=max_frequency_score,
            city=city,
            state=state,
            source=source,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        result = await client_service.get_clients(current_user, search_params)
        
        # Converter clientes para response
        clients_response = []
        for client in result["clients"]:
            client_dict = {
                "id": client.id,
                "user_id": client.user_id,
                "name": client.name,
                "whatsapp": client.whatsapp,
                "email": client.email,
                "notes": client.notes,
                "birth_date": client.birth_date,
                "gender": client.gender,
                "address": client.address,
                "city": client.city,
                "state": client.state,
                "zip_code": client.zip_code,
                "communication_preference": client.communication_preference,
                "source": client.source,
                "referral_code": client.referral_code,
                "tags": client.tags,
                "custom_fields": client.custom_fields,
                "is_active": client.is_active,
                "is_vip": client.is_vip,
                "first_appointment_at": client.first_appointment_at,
                "last_appointment_at": client.last_appointment_at,
                "total_appointments": client.total_appointments,
                "completed_appointments": client.completed_appointments,
                "cancelled_appointments": client.cancelled_appointments,
                "no_show_appointments": client.no_show_appointments,
                "frequency_score": client.frequency_score,
                "appointments_this_month": client.appointments_this_month,
                "appointments_last_month": client.appointments_last_month,
                "appointments_this_year": client.appointments_this_year,
                "average_days_between_appointments": client.average_days_between_appointments,
                "preferred_services": client.preferred_services,
                "preferred_days": client.preferred_days,
                "preferred_times": client.preferred_times,
                "total_spent": client.total_spent,
                "average_ticket": client.average_ticket,
                "last_payment_at": client.last_payment_at,
                "is_regular_customer": client.is_regular_customer,
                "is_frequent_customer": client.is_frequent_customer,
                "days_since_last_appointment": client.days_since_last_appointment,
                "customer_lifetime_days": client.customer_lifetime_days,
                "no_show_rate": client.no_show_rate,
                "completion_rate": client.completion_rate,
                "created_at": client.created_at,
                "updated_at": client.updated_at
            }
            clients_response.append(client_dict)
        
        return ClientList(
            clients=clients_response,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter clientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Criar novo cliente"""
    try:
        client = await client_service.create_client(client_data, current_user)
        
        # Converter para response
        client_response = {
            "id": client.id,
            "user_id": client.user_id,
            "name": client.name,
            "whatsapp": client.whatsapp,
            "email": client.email,
            "notes": client.notes,
            "birth_date": client.birth_date,
            "gender": client.gender,
            "address": client.address,
            "city": client.city,
            "state": client.state,
            "zip_code": client.zip_code,
            "communication_preference": client.communication_preference,
            "source": client.source,
            "referral_code": client.referral_code,
            "tags": client.tags,
            "custom_fields": client.custom_fields,
            "is_active": client.is_active,
            "is_vip": client.is_vip,
            "first_appointment_at": client.first_appointment_at,
            "last_appointment_at": client.last_appointment_at,
            "total_appointments": client.total_appointments,
            "completed_appointments": client.completed_appointments,
            "cancelled_appointments": client.cancelled_appointments,
            "no_show_appointments": client.no_show_appointments,
            "frequency_score": client.frequency_score,
            "appointments_this_month": client.appointments_this_month,
            "appointments_last_month": client.appointments_last_month,
            "appointments_this_year": client.appointments_this_year,
            "average_days_between_appointments": client.average_days_between_appointments,
            "preferred_services": client.preferred_services,
            "preferred_days": client.preferred_days,
            "preferred_times": client.preferred_times,
            "total_spent": client.total_spent,
            "average_ticket": client.average_ticket,
            "last_payment_at": client.last_payment_at,
            "is_regular_customer": client.is_regular_customer,
            "is_frequent_customer": client.is_frequent_customer,
            "days_since_last_appointment": client.days_since_last_appointment,
            "customer_lifetime_days": client.customer_lifetime_days,
            "no_show_rate": client.no_show_rate,
            "completion_rate": client.completion_rate,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
        
        return client_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Obter cliente específico"""
    try:
        client = await client_service.get_client(client_id, current_user)
        
        # Converter para response
        client_response = {
            "id": client.id,
            "user_id": client.user_id,
            "name": client.name,
            "whatsapp": client.whatsapp,
            "email": client.email,
            "notes": client.notes,
            "birth_date": client.birth_date,
            "gender": client.gender,
            "address": client.address,
            "city": client.city,
            "state": client.state,
            "zip_code": client.zip_code,
            "communication_preference": client.communication_preference,
            "source": client.source,
            "referral_code": client.referral_code,
            "tags": client.tags,
            "custom_fields": client.custom_fields,
            "is_active": client.is_active,
            "is_vip": client.is_vip,
            "first_appointment_at": client.first_appointment_at,
            "last_appointment_at": client.last_appointment_at,
            "total_appointments": client.total_appointments,
            "completed_appointments": client.completed_appointments,
            "cancelled_appointments": client.cancelled_appointments,
            "no_show_appointments": client.no_show_appointments,
            "frequency_score": client.frequency_score,
            "appointments_this_month": client.appointments_this_month,
            "appointments_last_month": client.appointments_last_month,
            "appointments_this_year": client.appointments_this_year,
            "average_days_between_appointments": client.average_days_between_appointments,
            "preferred_services": client.preferred_services,
            "preferred_days": client.preferred_days,
            "preferred_times": client.preferred_times,
            "total_spent": client.total_spent,
            "average_ticket": client.average_ticket,
            "last_payment_at": client.last_payment_at,
            "is_regular_customer": client.is_regular_customer,
            "is_frequent_customer": client.is_frequent_customer,
            "days_since_last_appointment": client.days_since_last_appointment,
            "customer_lifetime_days": client.customer_lifetime_days,
            "no_show_rate": client.no_show_rate,
            "completion_rate": client.completion_rate,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
        
        return client_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Atualizar cliente"""
    try:
        client = await client_service.update_client(client_id, client_data, current_user)
        
        # Converter para response
        client_response = {
            "id": client.id,
            "user_id": client.user_id,
            "name": client.name,
            "whatsapp": client.whatsapp,
            "email": client.email,
            "notes": client.notes,
            "birth_date": client.birth_date,
            "gender": client.gender,
            "address": client.address,
            "city": client.city,
            "state": client.state,
            "zip_code": client.zip_code,
            "communication_preference": client.communication_preference,
            "source": client.source,
            "referral_code": client.referral_code,
            "tags": client.tags,
            "custom_fields": client.custom_fields,
            "is_active": client.is_active,
            "is_vip": client.is_vip,
            "first_appointment_at": client.first_appointment_at,
            "last_appointment_at": client.last_appointment_at,
            "total_appointments": client.total_appointments,
            "completed_appointments": client.completed_appointments,
            "cancelled_appointments": client.cancelled_appointments,
            "no_show_appointments": client.no_show_appointments,
            "frequency_score": client.frequency_score,
            "appointments_this_month": client.appointments_this_month,
            "appointments_last_month": client.appointments_last_month,
            "appointments_this_year": client.appointments_this_year,
            "average_days_between_appointments": client.average_days_between_appointments,
            "preferred_services": client.preferred_services,
            "preferred_days": client.preferred_days,
            "preferred_times": client.preferred_times,
            "total_spent": client.total_spent,
            "average_ticket": client.average_ticket,
            "last_payment_at": client.last_payment_at,
            "is_regular_customer": client.is_regular_customer,
            "is_frequent_customer": client.is_frequent_customer,
            "days_since_last_appointment": client.days_since_last_appointment,
            "customer_lifetime_days": client.customer_lifetime_days,
            "no_show_rate": client.no_show_rate,
            "completion_rate": client.completion_rate,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
        
        return client_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Deletar cliente"""
    try:
        result = await client_service.delete_client(client_id, current_user)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/{client_id}/history", response_model=ClientHistory)
async def get_client_history(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Obter histórico completo do cliente"""
    try:
        history = await client_service.get_client_history(client_id, current_user)
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter histórico do cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/{client_id}/analytics", response_model=ClientAnalytics)
async def get_client_analytics(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Obter analytics avançados do cliente"""
    try:
        analytics = await client_service.get_client_analytics(client_id, current_user)
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter analytics do cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/stats/overview", response_model=ClientStats)
async def get_client_stats(
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Obter estatísticas dos clientes"""
    try:
        stats = await client_service.get_client_stats(current_user)
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de clientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/bulk-update")
async def bulk_update_clients(
    bulk_data: ClientBulkUpdate,
    current_user: User = Depends(get_current_active_user),
    client_service: ClientService = Depends(get_client_service)
):
    """Atualização em massa de clientes"""
    try:
        result = await client_service.bulk_update_clients(bulk_data, current_user)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na atualização em massa: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )