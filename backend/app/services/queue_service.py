"""
Serviço de filas para mensagens automáticas
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    """Serviço para gerenciar filas de mensagens"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.queues = {
            "appointment_confirmations": "queue:appointment:confirmations",
            "appointment_reminders": "queue:appointment:reminders",
            "appointment_cancellations": "queue:appointment:cancellations",
            "appointment_follow_ups": "queue:appointment:follow_ups",
            "whatsapp_messages": "queue:whatsapp:messages",
            "email_notifications": "queue:email:notifications"
        }
    
    async def enqueue_message(
        self, 
        queue_name: str, 
        message_data: Dict[str, Any], 
        delay_seconds: int = 0,
        priority: int = 0
    ) -> bool:
        """Adicionar mensagem à fila"""
        try:
            if not self.redis_client:
                logger.warning("Redis não disponível, mensagem não será enqueued")
                return False
            
            queue_key = self.queues.get(queue_name)
            if not queue_key:
                logger.error(f"Fila desconhecida: {queue_name}")
                return False
            
            # Criar payload da mensagem
            message_payload = {
                "id": str(UUID()),
                "data": message_data,
                "created_at": datetime.utcnow().isoformat(),
                "priority": priority,
                "retry_count": 0,
                "max_retries": 3
            }
            
            # Se há delay, usar sorted set para agendamento
            if delay_seconds > 0:
                scheduled_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
                score = scheduled_time.timestamp()
                await self.redis_client.zadd(
                    f"{queue_key}:scheduled", 
                    {json.dumps(message_payload): score}
                )
                logger.info(f"Mensagem agendada para {scheduled_time} na fila {queue_name}")
            else:
                # Adicionar à fila imediatamente
                await self.redis_client.lpush(queue_key, json.dumps(message_payload))
                logger.info(f"Mensagem adicionada à fila {queue_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem à fila {queue_name}: {e}")
            return False
    
    async def dequeue_message(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Remover e retornar próxima mensagem da fila"""
        try:
            if not self.redis_client:
                return None
            
            queue_key = self.queues.get(queue_name)
            if not queue_key:
                return None
            
            # Verificar mensagens agendadas primeiro
            now = datetime.utcnow().timestamp()
            scheduled_messages = await self.redis_client.zrangebyscore(
                f"{queue_key}:scheduled", 0, now, withscores=True
            )
            
            if scheduled_messages:
                # Mover mensagens agendadas para a fila principal
                for message, score in scheduled_messages:
                    await self.redis_client.lpush(queue_key, message)
                    await self.redis_client.zrem(f"{queue_key}:scheduled", message)
            
            # Obter próxima mensagem da fila
            message = await self.redis_client.rpop(queue_key)
            if message:
                return json.loads(message)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter mensagem da fila {queue_name}: {e}")
            return None
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Obter tamanho da fila"""
        try:
            if not self.redis_client:
                return 0
            
            queue_key = self.queues.get(queue_name)
            if not queue_key:
                return 0
            
            size = await self.redis_client.llen(queue_key)
            scheduled_size = await self.redis_client.zcard(f"{queue_key}:scheduled")
            return size + scheduled_size
            
        except Exception as e:
            logger.error(f"Erro ao obter tamanho da fila {queue_name}: {e}")
            return 0
    
    async def retry_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any], 
        delay_seconds: int = 60
    ) -> bool:
        """Reenviar mensagem para a fila com delay"""
        try:
            if not self.redis_client:
                return False
            
            # Incrementar contador de tentativas
            message["retry_count"] = message.get("retry_count", 0) + 1
            message["last_retry_at"] = datetime.utcnow().isoformat()
            
            # Verificar se excedeu o limite de tentativas
            if message["retry_count"] > message.get("max_retries", 3):
                logger.error(f"Mensagem excedeu limite de tentativas: {message['id']}")
                await self._move_to_failed_queue(queue_name, message)
                return False
            
            # Reenviar com delay
            return await self.enqueue_message(queue_name, message["data"], delay_seconds)
            
        except Exception as e:
            logger.error(f"Erro ao reenviar mensagem: {e}")
            return False
    
    async def _move_to_failed_queue(self, queue_name: str, message: Dict[str, Any]):
        """Mover mensagem para fila de falhas"""
        try:
            if not self.redis_client:
                return
            
            failed_queue = f"{self.queues[queue_name]}:failed"
            await self.redis_client.lpush(failed_queue, json.dumps(message))
            logger.error(f"Mensagem movida para fila de falhas: {message['id']}")
            
        except Exception as e:
            logger.error(f"Erro ao mover mensagem para fila de falhas: {e}")
    
    async def get_failed_messages(self, queue_name: str) -> List[Dict[str, Any]]:
        """Obter mensagens que falharam"""
        try:
            if not self.redis_client:
                return []
            
            failed_queue = f"{self.queues[queue_name]}:failed"
            messages = await self.redis_client.lrange(failed_queue, 0, -1)
            return [json.loads(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Erro ao obter mensagens falhadas: {e}")
            return []
    
    async def clear_failed_messages(self, queue_name: str) -> bool:
        """Limpar mensagens falhadas"""
        try:
            if not self.redis_client:
                return False
            
            failed_queue = f"{self.queues[queue_name]}:failed"
            await self.redis_client.delete(failed_queue)
            logger.info(f"Fila de falhas limpa: {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao limpar mensagens falhadas: {e}")
            return False


class MessageQueue:
    """Classe para gerenciar diferentes tipos de mensagens"""
    
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
    
    async def schedule_appointment_confirmation(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime,
        delay_seconds: int = 0
    ) -> bool:
        """Agendar confirmação de agendamento"""
        message_data = {
            "type": "appointment_confirmation",
            "appointment_id": str(appointment_id),
            "client_name": client_name,
            "client_whatsapp": client_whatsapp,
            "service_name": service_name,
            "appointment_time": appointment_time.isoformat(),
            "template": "appointment_confirmation"
        }
        
        return await self.queue_service.enqueue_message(
            "appointment_confirmations", 
            message_data, 
            delay_seconds,
            priority=1
        )
    
    async def schedule_appointment_reminder(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime,
        reminder_hours: int = 24
    ) -> bool:
        """Agendar lembrete de agendamento"""
        # Calcular delay para o lembrete
        now = datetime.utcnow()
        reminder_time = appointment_time - timedelta(hours=reminder_hours)
        
        if reminder_time <= now:
            # Se o lembrete deveria ter sido enviado, enviar imediatamente
            delay_seconds = 0
        else:
            delay_seconds = int((reminder_time - now).total_seconds())
        
        message_data = {
            "type": "appointment_reminder",
            "appointment_id": str(appointment_id),
            "client_name": client_name,
            "client_whatsapp": client_whatsapp,
            "service_name": service_name,
            "appointment_time": appointment_time.isoformat(),
            "reminder_hours": reminder_hours,
            "template": "appointment_reminder"
        }
        
        return await self.queue_service.enqueue_message(
            "appointment_reminders", 
            message_data, 
            delay_seconds,
            priority=2
        )
    
    async def schedule_appointment_cancellation(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime,
        cancellation_reason: str = None
    ) -> bool:
        """Agendar notificação de cancelamento"""
        message_data = {
            "type": "appointment_cancellation",
            "appointment_id": str(appointment_id),
            "client_name": client_name,
            "client_whatsapp": client_whatsapp,
            "service_name": service_name,
            "appointment_time": appointment_time.isoformat(),
            "cancellation_reason": cancellation_reason,
            "template": "appointment_cancellation"
        }
        
        return await self.queue_service.enqueue_message(
            "appointment_cancellations", 
            message_data, 
            delay_seconds=0,
            priority=1
        )
    
    async def schedule_appointment_follow_up(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime,
        follow_up_hours: int = 24
    ) -> bool:
        """Agendar follow-up após agendamento"""
        # Calcular delay para o follow-up
        now = datetime.utcnow()
        follow_up_time = appointment_time + timedelta(hours=follow_up_hours)
        delay_seconds = int((follow_up_time - now).total_seconds())
        
        message_data = {
            "type": "appointment_follow_up",
            "appointment_id": str(appointment_id),
            "client_name": client_name,
            "client_whatsapp": client_whatsapp,
            "service_name": service_name,
            "appointment_time": appointment_time.isoformat(),
            "follow_up_hours": follow_up_hours,
            "template": "appointment_follow_up"
        }
        
        return await self.queue_service.enqueue_message(
            "appointment_follow_ups", 
            message_data, 
            delay_seconds,
            priority=3
        )
    
    async def schedule_whatsapp_message(
        self, 
        to_number: str, 
        message: str, 
        template: str = None,
        delay_seconds: int = 0
    ) -> bool:
        """Agendar mensagem WhatsApp"""
        message_data = {
            "type": "whatsapp_message",
            "to_number": to_number,
            "message": message,
            "template": template,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.queue_service.enqueue_message(
            "whatsapp_messages", 
            message_data, 
            delay_seconds,
            priority=1
        )
    
    async def schedule_email_notification(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        template: str = None,
        delay_seconds: int = 0
    ) -> bool:
        """Agendar notificação por email"""
        message_data = {
            "type": "email_notification",
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "template": template,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.queue_service.enqueue_message(
            "email_notifications", 
            message_data, 
            delay_seconds,
            priority=2
        )







