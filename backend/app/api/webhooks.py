"""
Endpoints de webhooks (n8n)
"""

from fastapi import APIRouter, Request, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import httpx
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models.appointment import Appointment
from app.models.user import User
from app.services.queue_service import QueueService
from app.services.notification_service import NotificationService, WhatsAppService, EmailService
from app.dependencies import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/appointment")
async def appointment_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook para eventos de agendamento do n8n"""
    try:
    data = await request.json()
    logger.info(f"Webhook de agendamento recebido: {data}")
        
        # Validar dados obrigatórios
        required_fields = ["event_type", "appointment_id", "user_id"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo obrigatório ausente: {field}"
                )
        
        event_type = data["event_type"]
        appointment_id = data["appointment_id"]
        user_id = data["user_id"]
        
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
        
        # Processar baseado no tipo de evento
        if event_type == "created":
            await _handle_appointment_created(appointment, data)
        elif event_type == "updated":
            await _handle_appointment_updated(appointment, data)
        elif event_type == "cancelled":
            await _handle_appointment_cancelled(appointment, data)
        elif event_type == "confirmed":
            await _handle_appointment_confirmed(appointment, data)
        elif event_type == "completed":
            await _handle_appointment_completed(appointment, data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de evento inválido: {event_type}"
            )
        
        return {
            "success": True,
            "message": f"Evento {event_type} processado com sucesso",
            "appointment_id": appointment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook de agendamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/sync")
async def sync_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook para sincronização de dados do n8n"""
    try:
    data = await request.json()
    logger.info(f"Webhook de sincronização recebido: {data}")
        
        # Validar dados obrigatórios
        if "sync_type" not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo obrigatório ausente: sync_type"
            )
        
        sync_type = data["sync_type"]
        
        # Processar baseado no tipo de sincronização
        if sync_type == "appointments":
            result = await _sync_appointments(data, db)
        elif sync_type == "clients":
            result = await _sync_clients(data, db)
        elif sync_type == "services":
            result = await _sync_services(data, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de sincronização inválido: {sync_type}"
            )
        
        return {
            "success": True,
            "message": f"Sincronização {sync_type} processada com sucesso",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook de sincronização: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/message")
async def message_webhook(request: Request):
    """Webhook para mensagens do n8n"""
    try:
    data = await request.json()
    logger.info(f"Webhook de mensagem recebido: {data}")
        
        # Validar dados obrigatórios
        required_fields = ["message_type", "recipient", "content"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo obrigatório ausente: {field}"
                )
        
        message_type = data["message_type"]
        recipient = data["recipient"]
        content = data["content"]
        
        # Obter serviços de notificação
        redis_client = await get_redis()
        if not redis_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de mensagens não disponível"
            )
        
        queue_service = QueueService(redis_client)
        whatsapp_service = WhatsAppService()
        email_service = EmailService()
        notification_service = NotificationService(whatsapp_service, email_service)
        
        # Processar baseado no tipo de mensagem
        if message_type == "whatsapp":
            result = await _send_whatsapp_message(recipient, content, data, queue_service)
        elif message_type == "email":
            result = await _send_email_message(recipient, content, data, queue_service)
        elif message_type == "bulk":
            result = await _send_bulk_message(recipient, content, data, queue_service)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de mensagem inválido: {message_type}"
            )
        
        return {
            "success": True,
            "message": f"Mensagem {message_type} processada com sucesso",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook de mensagem: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


# Funções auxiliares para processamento de webhooks

async def _handle_appointment_created(appointment: Appointment, data: Dict[str, Any]):
    """Processar criação de agendamento"""
    logger.info(f"Processando criação de agendamento: {appointment.id}")
    
    # Aqui você pode adicionar lógica específica para criação
    # Por exemplo, enviar notificações, atualizar cache, etc.
    
    # Exemplo: Enviar notificação para o n8n
    await _notify_n8n_workflow("appointment_created", {
        "appointment_id": str(appointment.id),
        "user_id": str(appointment.user_id),
        "client_name": appointment.client_name,
        "start_time": appointment.start_time.isoformat(),
        "service_name": appointment.service.name if appointment.service else "Serviço removido"
    })


async def _handle_appointment_updated(appointment: Appointment, data: Dict[str, Any]):
    """Processar atualização de agendamento"""
    logger.info(f"Processando atualização de agendamento: {appointment.id}")
    
    await _notify_n8n_workflow("appointment_updated", {
        "appointment_id": str(appointment.id),
        "user_id": str(appointment.user_id),
        "changes": data.get("changes", {}),
        "updated_at": appointment.updated_at.isoformat()
    })


async def _handle_appointment_cancelled(appointment: Appointment, data: Dict[str, Any]):
    """Processar cancelamento de agendamento"""
    logger.info(f"Processando cancelamento de agendamento: {appointment.id}")
    
    await _notify_n8n_workflow("appointment_cancelled", {
        "appointment_id": str(appointment.id),
        "user_id": str(appointment.user_id),
        "cancellation_reason": data.get("cancellation_reason"),
        "cancelled_at": datetime.utcnow().isoformat()
    })


async def _handle_appointment_confirmed(appointment: Appointment, data: Dict[str, Any]):
    """Processar confirmação de agendamento"""
    logger.info(f"Processando confirmação de agendamento: {appointment.id}")
    
    await _notify_n8n_workflow("appointment_confirmed", {
        "appointment_id": str(appointment.id),
        "user_id": str(appointment.user_id),
        "confirmed_at": datetime.utcnow().isoformat()
    })


async def _handle_appointment_completed(appointment: Appointment, data: Dict[str, Any]):
    """Processar conclusão de agendamento"""
    logger.info(f"Processando conclusão de agendamento: {appointment.id}")
    
    await _notify_n8n_workflow("appointment_completed", {
        "appointment_id": str(appointment.id),
        "user_id": str(appointment.user_id),
        "completed_at": datetime.utcnow().isoformat()
    })


async def _sync_appointments(data: Dict[str, Any], db: Session):
    """Sincronizar agendamentos"""
    logger.info("Sincronizando agendamentos...")
    
    # Implementar lógica de sincronização
    # Por exemplo, importar agendamentos de sistema externo
    
    return {
        "synced_count": 0,
        "message": "Sincronização de agendamentos processada"
    }


async def _sync_clients(data: Dict[str, Any], db: Session):
    """Sincronizar clientes"""
    logger.info("Sincronizando clientes...")
    
    # Implementar lógica de sincronização
    # Por exemplo, importar clientes de CRM externo
    
    return {
        "synced_count": 0,
        "message": "Sincronização de clientes processada"
    }


async def _sync_services(data: Dict[str, Any], db: Session):
    """Sincronizar serviços"""
    logger.info("Sincronizando serviços...")
    
    # Implementar lógica de sincronização
    # Por exemplo, importar serviços de sistema externo
    
    return {
        "synced_count": 0,
        "message": "Sincronização de serviços processada"
    }


async def _send_whatsapp_message(recipient: str, content: str, data: Dict[str, Any], queue_service: QueueService):
    """Enviar mensagem WhatsApp"""
    try:
        # Adicionar à fila de mensagens
        await queue_service.schedule_whatsapp_message(
            to_number=recipient,
            message=content,
            template=data.get("template"),
            delay_seconds=data.get("delay_seconds", 0)
        )
        
        return {
            "queued": True,
            "recipient": recipient,
            "message": "Mensagem WhatsApp adicionada à fila"
        }
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem WhatsApp: {e}")
        return {
            "queued": False,
            "error": str(e)
        }


async def _send_email_message(recipient: str, content: str, data: Dict[str, Any], queue_service: QueueService):
    """Enviar mensagem por email"""
    try:
        # Adicionar à fila de emails
        await queue_service.schedule_email_notification(
            to_email=recipient,
            subject=data.get("subject", "Mensagem do AgendaZap"),
            body=content,
            template=data.get("template"),
            delay_seconds=data.get("delay_seconds", 0)
        )
        
        return {
            "queued": True,
            "recipient": recipient,
            "message": "Email adicionado à fila"
        }
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}")
        return {
            "queued": False,
            "error": str(e)
        }


async def _send_bulk_message(recipients: list, content: str, data: Dict[str, Any], queue_service: QueueService):
    """Enviar mensagem em massa"""
    try:
        results = []
        
        for recipient in recipients:
            if data.get("message_type") == "whatsapp":
                result = await _send_whatsapp_message(recipient, content, data, queue_service)
            else:
                result = await _send_email_message(recipient, content, data, queue_service)
            
            results.append(result)
        
        return {
            "total_recipients": len(recipients),
            "queued_count": sum(1 for r in results if r.get("queued", False)),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem em massa: {e}")
        return {
            "error": str(e)
        }


async def _notify_n8n_workflow(event_type: str, data: Dict[str, Any]):
    """Notificar workflow do n8n"""
    try:
        # URL do webhook do n8n (configurar nas variáveis de ambiente)
        n8n_webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', '')
        
        if not n8n_webhook_url:
            logger.warning("URL do webhook n8n não configurada")
            return
        
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(n8n_webhook_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Workflow n8n notificado: {event_type}")
            else:
                logger.error(f"Erro ao notificar workflow n8n: {response.status_code}")
                
    except Exception as e:
        logger.error(f"Erro ao notificar workflow n8n: {e}")

