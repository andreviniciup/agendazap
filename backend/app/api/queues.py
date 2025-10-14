"""
Endpoints para gerenciar sistema de filas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.database import get_db
from app.dependencies import get_current_active_user, get_queue_service, get_message_queue
from app.models.user import User
from app.services.queue_service import QueueService, MessageQueue

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_queue_status(
    current_user: User = Depends(get_current_active_user),
    queue_service: QueueService = Depends(get_queue_service)
):
    """Obter status das filas"""
    try:
        status_info = {}
        
        for queue_name in queue_service.queues.keys():
            size = await queue_service.get_queue_size(queue_name)
            status_info[queue_name] = {
                "size": size,
                "status": "active" if size > 0 else "empty"
            }
        
        return {
            "queues": status_info,
            "total_messages": sum(info["size"] for info in status_info.values()),
            "timestamp": "2025-09-19T18:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status das filas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/failed")
async def get_failed_messages(
    queue_name: str = Query(..., description="Nome da fila"),
    current_user: User = Depends(get_current_active_user),
    queue_service: QueueService = Depends(get_queue_service)
):
    """Obter mensagens que falharam"""
    try:
        if queue_name not in queue_service.queues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fila desconhecida: {queue_name}"
            )
        
        failed_messages = await queue_service.get_failed_messages(queue_name)
        
        return {
            "queue_name": queue_name,
            "failed_messages": failed_messages,
            "count": len(failed_messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter mensagens falhadas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/failed")
async def clear_failed_messages(
    queue_name: str = Query(..., description="Nome da fila"),
    current_user: User = Depends(get_current_active_user),
    queue_service: QueueService = Depends(get_queue_service)
):
    """Limpar mensagens que falharam"""
    try:
        if queue_name not in queue_service.queues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fila desconhecida: {queue_name}"
            )
        
        success = await queue_service.clear_failed_messages(queue_name)
        
        if success:
            return {"message": f"Mensagens falhadas da fila {queue_name} foram limpas"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao limpar mensagens falhadas"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao limpar mensagens falhadas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/test/whatsapp")
async def test_whatsapp_message(
    to_number: str = Query(..., description="Número do WhatsApp"),
    message: str = Query(..., description="Mensagem a ser enviada"),
    current_user: User = Depends(get_current_active_user),
    message_queue: MessageQueue = Depends(get_message_queue)
):
    """Testar envio de mensagem WhatsApp"""
    try:
        success = await message_queue.schedule_whatsapp_message(
            to_number=to_number,
            message=message,
            delay_seconds=0
        )
        
        if success:
            return {
                "message": "Mensagem WhatsApp agendada com sucesso",
                "to_number": to_number,
                "message": message
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao agendar mensagem WhatsApp"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao testar mensagem WhatsApp: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/test/email")
async def test_email_notification(
    to_email: str = Query(..., description="Email de destino"),
    subject: str = Query(..., description="Assunto do email"),
    body: str = Query(..., description="Corpo do email"),
    current_user: User = Depends(get_current_active_user),
    message_queue: MessageQueue = Depends(get_message_queue)
):
    """Testar envio de notificação por email"""
    try:
        success = await message_queue.schedule_email_notification(
            to_email=to_email,
            subject=subject,
            body=body,
            delay_seconds=0
        )
        
        if success:
            return {
                "message": "Notificação por email agendada com sucesso",
                "to_email": to_email,
                "subject": subject
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao agendar notificação por email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao testar notificação por email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/workers/status")
async def get_workers_status(
    current_user: User = Depends(get_current_active_user)
):
    """Obter status dos workers"""
    try:
        from app.workers import worker_manager
        
        return {
            "workers_running": worker_manager.is_running(),
            "status": "active" if worker_manager.is_running() else "stopped",
            "timestamp": "2025-09-19T18:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status dos workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/workers/start")
async def start_workers(
    current_user: User = Depends(get_current_active_user)
):
    """Iniciar workers de mensagens"""
    try:
        from app.workers import worker_manager
        
        if worker_manager.is_running():
            return {"message": "Workers já estão rodando"}
        
        await worker_manager.start_workers()
        
        return {"message": "Workers iniciados com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao iniciar workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/workers/stop")
async def stop_workers(
    current_user: User = Depends(get_current_active_user)
):
    """Parar workers de mensagens"""
    try:
        from app.workers import worker_manager
        
        if not worker_manager.is_running():
            return {"message": "Workers já estão parados"}
        
        await worker_manager.stop_workers()
        
        return {"message": "Workers parados com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao parar workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )







