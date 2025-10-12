"""
API endpoints para gerenciamento de cache
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.cache_service import cache_service
from app.services.appointment_service import AppointmentService
from app.services.service_service import ServiceService
from app.services.plan_service import PlanService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_cache_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Obter métricas de performance do cache"""
    try:
        metrics = cache_service.get_metrics()
        cache_info = cache_service.get_cache_info()
        
        return {
            "metrics": metrics,
            "cache_info": cache_info,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas de cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/warm")
async def warm_user_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Aquecer cache do usuário atual"""
    try:
        plan_service = PlanService()
        appointment_service = AppointmentService(db, plan_service)
        service_service = ServiceService(db, plan_service)
        
        # Obter dados para aquecer o cache
        services_data = service_service.get_user_services(current_user, use_cache=False)
        
        # Simular dados de agenda para os próximos 7 dias
        from datetime import date, timedelta
        agenda_data = {}
        today = date.today()
        
        for i in range(7):
            target_date = today + timedelta(days=i)
            try:
                agenda = appointment_service.get_user_agenda(current_user, target_date, use_cache=False)
                agenda_data[target_date.isoformat()] = agenda
            except Exception as e:
                logger.warning(f"Erro ao obter agenda para {target_date}: {e}")
                agenda_data[target_date.isoformat()] = {
                    "date": target_date.isoformat(),
                    "appointments": [],
                    "total_appointments": 0,
                    "available_slots": []
                }
        
        # Aquecer cache
        success = cache_service.warm_user_cache(
            current_user.id, 
            agenda_data, 
            services_data
        )
        
        if success:
            return {
                "message": "Cache aquecido com sucesso",
                "user_id": str(current_user.id),
                "services_cached": len(services_data),
                "agenda_days_cached": len(agenda_data)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao aquecer cache"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao aquecer cache do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/invalidate")
async def invalidate_user_cache(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Invalidar todo o cache do usuário atual"""
    try:
        invalidated_count = cache_service.invalidate_user_cache(current_user.id)
        
        return {
            "message": "Cache invalidado com sucesso",
            "user_id": str(current_user.id),
            "invalidated_keys": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao invalidar cache do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/invalidate/agenda")
async def invalidate_user_agenda_cache(
    date: str = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Invalidar cache de agenda do usuário"""
    try:
        if date:
            invalidated_count = cache_service.invalidate_user_agenda(current_user.id, date)
            message = f"Cache de agenda invalidado para a data {date}"
        else:
            invalidated_count = cache_service.invalidate_user_agenda(current_user.id)
            message = "Cache de agenda invalidado para todas as datas"
        
        return {
            "message": message,
            "user_id": str(current_user.id),
            "invalidated_keys": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao invalidar cache de agenda: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/invalidate/services")
async def invalidate_user_services_cache(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Invalidar cache de serviços do usuário"""
    try:
        invalidated_count = cache_service.invalidate_user_services(current_user.id)
        
        return {
            "message": "Cache de serviços invalidado com sucesso",
            "user_id": str(current_user.id),
            "invalidated_keys": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao invalidar cache de serviços: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/status")
async def get_cache_status() -> Dict[str, Any]:
    """Obter status do cache Redis"""
    try:
        cache_info = cache_service.get_cache_info()
        metrics = cache_service.get_metrics()
        fallback_status = cache_service.get_fallback_status()
        
        return {
            "cache_info": cache_info,
            "metrics": metrics,
            "fallback_status": fallback_status,
            "status": "healthy" if cache_info.get("connected", False) else "unhealthy"
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status do cache: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/fallback-status")
async def get_fallback_status() -> Dict[str, Any]:
    """Obter status do sistema de fallback"""
    try:
        fallback_status = cache_service.get_fallback_status()
        
        return {
            "fallback_status": fallback_status,
            "message": "Sistema de fallback ativo" if fallback_status["fallback_active"] else "Cache funcionando normalmente"
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status do fallback: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/reset-metrics")
async def reset_cache_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resetar métricas do cache"""
    try:
        cache_service.reset_metrics()
        
        return {
            "message": "Métricas do cache resetadas com sucesso",
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Erro ao resetar métricas do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
