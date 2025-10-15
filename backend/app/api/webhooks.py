"""
Endpoints de webhooks (n8n)
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import httpx
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.config import settings
from app.models.appointment import Appointment
from app.models.user import User
from app.models.service import Service
from app.models.user import User
from app.services.queue_service import QueueService
from app.services.notification_service import NotificationService, WhatsAppService, EmailService
from app.services.bot.bot_service import BotService
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
                status_code=status.HTTP_404_NOT_FOUND,
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
    if not settings.USE_N8N:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint desabilitado")
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
    """Webhook de mensagens: aceita formato n8n (quando USE_N8N=true) ou provedor direto (Twilio/Meta)."""
    try:
        data = await request.json()
        logger.info(f"Webhook de mensagem recebido: {data}")

        redis_client = await get_redis()
        if not redis_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de mensagens não disponível"
            )

        queue_service = QueueService(redis_client)

        # Caminho n8n (retrocompatível)
        if settings.USE_N8N and all(k in data for k in ["message_type", "recipient", "content"]):
            message_type = data["message_type"]
            recipient = data["recipient"]
            content = data["content"]
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
                "message": f"Mensagem {message_type} processada (n8n)",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Caminho direto: Twilio/Meta → normalizar e decidir
        normalized = _normalize_incoming_provider_payload(data)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

        # Resolver user_id/service_id por número de destino (To)
        user_id = None
        try:
            resolved = _resolve_user_and_defaults(normalized)
            normalized.update(resolved)
            user_id = resolved.get("user_id")
        except Exception as e:
            logger.warning(f"Falha ao resolver user/service pelo destino: {e}")
        
        # Detectar mídia e acionar handoff se necessário
        media_type = normalized.get("media_type")
        if media_type:
            logger.info(f"📎 Mídia detectada: {media_type}")
            
            # Buscar preferências do usuário
            handoff_triggered = False
            if user_id:
                try:
                    from app.database import get_db
                    db = next(get_db())
                    user = db.query(User).filter(User.id == user_id).first()
                    
                    if user:
                        prefs = user.notification_preferences or {}
                        trigger_on_media = prefs.get("trigger_on_media", True)
                        
                        if trigger_on_media:
                            # Acionar handoff
                            from app.services.notification_service import NotificationService
                            notification_service = NotificationService()
                            
                            # Obter snippet da conversa
                            from app.services.bot.conversation_state import ConversationState
                            conv_state = ConversationState(redis_client)
                            snippet = await conv_state.get_conversation_snippet(
                                normalized.get("from"),
                                limit=5
                            )
                            
                            # Enviar alerta
                            alert_channels = prefs.get("alert_channels", ["email"])
                            await notification_service.send_handoff_alert(
                                provider_email=user.email,
                                provider_whatsapp=user.whatsapp_number,
                                client_whatsapp=normalized.get("from"),
                                reason="media",
                                conversation_snippet=snippet,
                                alert_channels=alert_channels,
                                metadata={"media_type": media_type}
                            )
                            
                            handoff_triggered = True
                            logger.info(f"✅ Handoff acionado para {user.email} - mídia: {media_type}")
                except Exception as e:
                    logger.error(f"Erro ao processar handoff de mídia: {e}")
            
            # Responder ao cliente
            from app.services.bot import templates
            now = datetime.utcnow()
            tone = "night" if templates.is_night(now) else "day"
            media_names = {
                "audio": "seu áudio",
                "image": "sua imagem",
                "video": "seu vídeo",
                "document": "seu documento"
            }
            response_message = templates.pick(
                "media_handoff",
                tone,
                media_type=media_names.get(media_type, "a mídia")
            )
            
            await queue_service.schedule_whatsapp_message(
                to_number=normalized.get("from"),
                message=response_message,
                template=None,
                delay_seconds=0
            )
            
            return {
                "success": True,
                "message": "Mídia detectada - handoff acionado",
                "result": {"queued": True, "handoff": handoff_triggered, "media_type": media_type},
                "timestamp": datetime.utcnow().isoformat()
            }

        # Processar texto normalmente com o bot
        bot = BotService(redis_client)
        decision = await bot.process(normalized)
        
        # Se o bot marcou handoff, enviar alerta ao prestador
        if decision.get("handoff") and user_id:
            try:
                from app.database import get_db
                db = next(get_db())
                user = db.query(User).filter(User.id == user_id).first()
                
                if user:
                    prefs = user.notification_preferences or {}
                    
                    # Obter snippet da conversa
                    from app.services.bot.conversation_state import ConversationState
                    conv_state = ConversationState(redis_client)
                    snippet = await conv_state.get_conversation_snippet(
                        normalized.get("from"),
                        limit=5
                    )
                    
                    # Enviar alerta
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService()
                    alert_channels = prefs.get("alert_channels", ["email"])
                    
                    await notification_service.send_handoff_alert(
                        provider_email=user.email,
                        provider_whatsapp=user.whatsapp_number,
                        client_whatsapp=normalized.get("from"),
                        reason=decision.get("handoff_reason", "unknown"),
                        conversation_snippet=snippet,
                        alert_channels=alert_channels,
                        metadata=decision.get("metadata", {})
                    )
                    
                    logger.info(f"✅ Handoff alert sent to {user.email}")
            except Exception as e:
                logger.error(f"Erro ao enviar alerta de handoff: {e}")

        await queue_service.schedule_whatsapp_message(
            to_number=decision.get("to_number"),
            message=decision.get("message"),
            template=None,
            delay_seconds=0
        )

        return {
            "success": True,
            "message": "Mensagem processada pelo bot",
            "result": {
                "queued": True,
                "to": decision.get("to_number"),
                "handoff": decision.get("handoff", False)
            },
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
    if settings.USE_N8N:
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
    
    if settings.USE_N8N:
        await _notify_n8n_workflow("appointment_updated", {
            "appointment_id": str(appointment.id),
            "user_id": str(appointment.user_id),
            "changes": data.get("changes", {}),
            "updated_at": appointment.updated_at.isoformat()
        })


async def _handle_appointment_cancelled(appointment: Appointment, data: Dict[str, Any]):
    """Processar cancelamento de agendamento"""
    logger.info(f"Processando cancelamento de agendamento: {appointment.id}")
    
    if settings.USE_N8N:
        await _notify_n8n_workflow("appointment_cancelled", {
            "appointment_id": str(appointment.id),
            "user_id": str(appointment.user_id),
            "cancellation_reason": data.get("cancellation_reason"),
            "cancelled_at": datetime.utcnow().isoformat()
        })


async def _handle_appointment_confirmed(appointment: Appointment, data: Dict[str, Any]):
    """Processar confirmação de agendamento"""
    logger.info(f"Processando confirmação de agendamento: {appointment.id}")
    
    if settings.USE_N8N:
        await _notify_n8n_workflow("appointment_confirmed", {
            "appointment_id": str(appointment.id),
            "user_id": str(appointment.user_id),
            "confirmed_at": datetime.utcnow().isoformat()
        })


async def _handle_appointment_completed(appointment: Appointment, data: Dict[str, Any]):
    """Processar conclusão de agendamento"""
    logger.info(f"Processando conclusão de agendamento: {appointment.id}")
    
    if settings.USE_N8N:
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


def _normalize_incoming_provider_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza payloads comuns de Twilio/Meta para um formato interno.

    Saída esperada: { "from": str, "text": str, "media_type": str, "attachments": list, "timestamp": str }
    """
    try:
        # Twilio WhatsApp: Body, From, To
        if "Body" in data and "From" in data:
            # Detectar mídia no Twilio
            media_type = None
            if data.get("MediaContentType0"):
                content_type = data["MediaContentType0"].lower()
                if "image" in content_type:
                    media_type = "image"
                elif "audio" in content_type:
                    media_type = "audio"
                elif "video" in content_type:
                    media_type = "video"
                elif "application" in content_type or "document" in content_type:
                    media_type = "document"
            
            return {
                "from": data.get("From"),
                "text": data.get("Body", ""),
                "media_type": media_type,
                "attachments": [],
                "to": data.get("To"),
                "timestamp": data.get("Timestamp") or datetime.utcnow().isoformat(),
            }

        # Meta/Cloud API Webhook (simplificado)
        if "entry" in data and isinstance(data["entry"], list):
            try:
                changes = data["entry"][0]["changes"][0]["value"]
                messages = changes.get("messages") or []
                if messages:
                    msg = messages[0]
                    
                    # Detectar mídia no Meta
                    media_type = None
                    msg_type = msg.get("type", "text")
                    if msg_type in ["image", "audio", "video", "document"]:
                        media_type = msg_type
                    
                    return {
                        "from": msg.get("from"),
                        "text": (msg.get("text") or {}).get("body", ""),
                        "media_type": media_type,
                        "attachments": [],
                        "to": changes.get("metadata", {}).get("phone_number_id"),
                        "timestamp": msg.get("timestamp") or datetime.utcnow().isoformat(),
                    }
            except Exception:
                pass

        return {}
    except Exception:
        return {}


def _clean_phone(num: str) -> str:
    return "".join(ch for ch in (num or "") if ch.isdigit())


def _resolve_user_and_defaults(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve user_id via número de destino (To) e escolhe um service_id padrão."""
    db: Session = next(get_db())
    to_raw = normalized.get("to")
    to_clean = _clean_phone(to_raw)
    if to_clean.startswith("55") and len(to_clean) == 13:
        wa_format = f"+{to_clean}"
    elif to_clean:
        wa_format = f"+{to_clean}"
    else:
        wa_format = None

    user = None
    if wa_format:
        user = db.query(User).filter(User.whatsapp_number == wa_format).first()

    if not user:
        return {}

    # tentar serviço pelo histórico do cliente (último agendamento)
    last_appt = None
    try:
        client_whatsapp = normalized.get("from")
        if client_whatsapp:
            last_appt = db.query(Appointment).filter(
                Appointment.user_id == user.id,
                Appointment.client_whatsapp == client_whatsapp,
                Appointment.is_cancelled == False
            ).order_by(Appointment.start_time.desc()).first()
    except Exception:
        last_appt = None

    if last_appt and last_appt.service_id:
        svc = db.query(Service).filter(Service.id == last_appt.service_id, Service.is_active == True).first()
    else:
        # escolher um serviço ativo como fallback (primeiro por ordem)
        svc = db.query(Service).filter(Service.user_id == user.id, Service.is_active == True).order_by(Service.sort_order, Service.name).first()

    return {
        "user_id": str(user.id),
        "service_id": str(svc.id) if svc else None,
        "client_whatsapp": normalized.get("from"),
    }

