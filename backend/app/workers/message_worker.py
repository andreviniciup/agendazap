"""
Worker para processar mensagens das filas
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.services.queue_service import QueueService, MessageQueue
from app.services.notification_service import NotificationService, WhatsAppService, EmailService
from app.services.appointment_service import AppointmentService
from app.database import get_db
from app.dependencies import get_redis

logger = logging.getLogger(__name__)


class MessageWorker:
    """Worker para processar mensagens das filas"""
    
    def __init__(self, queue_service: QueueService, notification_service: NotificationService):
        self.queue_service = queue_service
        self.notification_service = notification_service
        self.running = False
        self.workers = {}
    
    async def start(self):
        """Iniciar workers"""
        self.running = True
        logger.info("🚀 Iniciando workers de mensagens...")
        
        # Iniciar workers para cada tipo de fila
        self.workers = {
            "appointment_confirmations": asyncio.create_task(
                self._process_queue("appointment_confirmations")
            ),
            "appointment_reminders": asyncio.create_task(
                self._process_queue("appointment_reminders")
            ),
            "appointment_cancellations": asyncio.create_task(
                self._process_queue("appointment_cancellations")
            ),
            "appointment_follow_ups": asyncio.create_task(
                self._process_queue("appointment_follow_ups")
            ),
            "whatsapp_messages": asyncio.create_task(
                self._process_queue("whatsapp_messages")
            ),
            "email_notifications": asyncio.create_task(
                self._process_queue("email_notifications")
            )
        }
        
        logger.info("✅ Workers iniciados com sucesso!")
    
    async def stop(self):
        """Parar workers"""
        self.running = False
        logger.info("🛑 Parando workers de mensagens...")
        
        # Cancelar todas as tarefas
        for worker_name, task in self.workers.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} parado")
        
        logger.info("✅ Workers parados com sucesso!")
    
    async def _process_queue(self, queue_name: str):
        """Processar mensagens de uma fila específica"""
        logger.info(f"🔄 Iniciando worker para fila: {queue_name}")
        
        while self.running:
            try:
                # Obter próxima mensagem
                message = await self.queue_service.dequeue_message(queue_name)
                
                if message:
                    await self._process_message(queue_name, message)
                else:
                    # Não há mensagens, aguardar um pouco
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro no worker {queue_name}: {e}")
                await asyncio.sleep(5)  # Aguardar antes de tentar novamente
    
    async def _process_message(self, queue_name: str, message: Dict[str, Any]):
        """Processar uma mensagem específica"""
        try:
            message_id = message.get("id", "unknown")
            message_data = message.get("data", {})
            message_type = message_data.get("type", "unknown")
            
            logger.info(f"📨 Processando mensagem {message_id} do tipo {message_type}")
            
            # Processar baseado no tipo de mensagem
            if message_type == "appointment_confirmation":
                await self._process_appointment_confirmation(message_data)
            elif message_type == "appointment_reminder":
                await self._process_appointment_reminder(message_data)
            elif message_type == "appointment_cancellation":
                await self._process_appointment_cancellation(message_data)
            elif message_type == "appointment_follow_up":
                await self._process_appointment_follow_up(message_data)
            elif message_type == "whatsapp_message":
                await self._process_whatsapp_message(message_data)
            elif message_type == "email_notification":
                await self._process_email_notification(message_data)
            else:
                logger.warning(f"Tipo de mensagem desconhecido: {message_type}")
            
            logger.info(f"✅ Mensagem {message_id} processada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {message.get('id', 'unknown')}: {e}")
            
            # Tentar reenviar a mensagem
            await self.queue_service.retry_message(queue_name, message)
    
    async def _process_appointment_confirmation(self, message_data: Dict[str, Any]):
        """Processar confirmação de agendamento"""
        try:
            appointment_id = message_data.get("appointment_id")
            client_name = message_data.get("client_name")
            client_whatsapp = message_data.get("client_whatsapp")
            service_name = message_data.get("service_name")
            appointment_time_str = message_data.get("appointment_time")
            
            if not all([appointment_id, client_name, client_whatsapp, service_name, appointment_time_str]):
                raise ValueError("Dados incompletos para confirmação de agendamento")
            
            appointment_time = datetime.fromisoformat(appointment_time_str)
            
            # Enviar notificação
            result = await self.notification_service.send_appointment_notification(
                "confirmation",
                appointment_id,
                client_name,
                client_whatsapp,
                service_name=service_name,
                appointment_time=appointment_time
            )
            
            # Atualizar status no banco de dados
            await self._update_appointment_notification_status(appointment_id, "confirmation_sent", result)
            
        except Exception as e:
            logger.error(f"Erro ao processar confirmação de agendamento: {e}")
            raise
    
    async def _process_appointment_reminder(self, message_data: Dict[str, Any]):
        """Processar lembrete de agendamento"""
        try:
            appointment_id = message_data.get("appointment_id")
            client_name = message_data.get("client_name")
            client_whatsapp = message_data.get("client_whatsapp")
            service_name = message_data.get("service_name")
            appointment_time_str = message_data.get("appointment_time")
            
            if not all([appointment_id, client_name, client_whatsapp, service_name, appointment_time_str]):
                raise ValueError("Dados incompletos para lembrete de agendamento")
            
            appointment_time = datetime.fromisoformat(appointment_time_str)
            
            # Enviar notificação
            result = await self.notification_service.send_appointment_notification(
                "reminder",
                appointment_id,
                client_name,
                client_whatsapp,
                service_name=service_name,
                appointment_time=appointment_time
            )
            
            # Atualizar status no banco de dados
            await self._update_appointment_notification_status(appointment_id, "reminder_sent", result)
            
        except Exception as e:
            logger.error(f"Erro ao processar lembrete de agendamento: {e}")
            raise
    
    async def _process_appointment_cancellation(self, message_data: Dict[str, Any]):
        """Processar cancelamento de agendamento"""
        try:
            appointment_id = message_data.get("appointment_id")
            client_name = message_data.get("client_name")
            client_whatsapp = message_data.get("client_whatsapp")
            service_name = message_data.get("service_name")
            appointment_time_str = message_data.get("appointment_time")
            cancellation_reason = message_data.get("cancellation_reason")
            
            if not all([appointment_id, client_name, client_whatsapp, service_name, appointment_time_str]):
                raise ValueError("Dados incompletos para cancelamento de agendamento")
            
            appointment_time = datetime.fromisoformat(appointment_time_str)
            
            # Enviar notificação
            result = await self.notification_service.send_appointment_notification(
                "cancellation",
                appointment_id,
                client_name,
                client_whatsapp,
                service_name=service_name,
                appointment_time=appointment_time,
                cancellation_reason=cancellation_reason
            )
            
            logger.info(f"Notificação de cancelamento enviada: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao processar cancelamento de agendamento: {e}")
            raise
    
    async def _process_appointment_follow_up(self, message_data: Dict[str, Any]):
        """Processar follow-up de agendamento"""
        try:
            appointment_id = message_data.get("appointment_id")
            client_name = message_data.get("client_name")
            client_whatsapp = message_data.get("client_whatsapp")
            service_name = message_data.get("service_name")
            appointment_time_str = message_data.get("appointment_time")
            
            if not all([appointment_id, client_name, client_whatsapp, service_name, appointment_time_str]):
                raise ValueError("Dados incompletos para follow-up de agendamento")
            
            appointment_time = datetime.fromisoformat(appointment_time_str)
            
            # Enviar notificação
            result = await self.notification_service.send_appointment_notification(
                "follow_up",
                appointment_id,
                client_name,
                client_whatsapp,
                service_name=service_name,
                appointment_time=appointment_time
            )
            
            logger.info(f"Follow-up enviado: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao processar follow-up de agendamento: {e}")
            raise
    
    async def _process_whatsapp_message(self, message_data: Dict[str, Any]):
        """Processar mensagem WhatsApp customizada"""
        try:
            to_number = message_data.get("to_number")
            message = message_data.get("message")
            template = message_data.get("template")
            
            if not all([to_number, message]):
                raise ValueError("Dados incompletos para mensagem WhatsApp")
            
            # Enviar mensagem
            result = await self.notification_service.whatsapp_service.send_message(
                to_number, message, template
            )
            
            logger.info(f"Mensagem WhatsApp enviada: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem WhatsApp: {e}")
            raise
    
    async def _process_email_notification(self, message_data: Dict[str, Any]):
        """Processar notificação por email"""
        try:
            to_email = message_data.get("to_email")
            subject = message_data.get("subject")
            body = message_data.get("body")
            
            if not all([to_email, subject, body]):
                raise ValueError("Dados incompletos para notificação por email")
            
            # Enviar email
            result = await self.notification_service.email_service.send_email(
                to_email, subject, body
            )
            
            logger.info(f"Email enviado: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao processar notificação por email: {e}")
            raise
    
    async def _update_appointment_notification_status(
        self, 
        appointment_id: str, 
        status_field: str, 
        result: Dict[str, Any]
    ):
        """Atualizar status de notificação no banco de dados"""
        try:
            from app.database import get_db
            from app.models.appointment import Appointment
            from sqlalchemy.orm import Session
            
            # Obter sessão do banco
            db = next(get_db())
            
            # Buscar agendamento
            appointment = db.query(Appointment).filter(
                Appointment.id == appointment_id
            ).first()
            
            if appointment:
                # Atualizar status baseado no resultado
                whatsapp_success = result.get("whatsapp", {}).get("success", False)
                email_success = result.get("email", {}).get("success", False)
                
                if status_field == "confirmation_sent":
                    appointment.confirmation_sent = whatsapp_success or email_success
                elif status_field == "reminder_sent":
                    appointment.reminder_sent = whatsapp_success or email_success
                
                db.commit()
                logger.info(f"Status {status_field} atualizado para agendamento {appointment_id}: {whatsapp_success or email_success}")
            else:
                logger.warning(f"Agendamento {appointment_id} não encontrado para atualização de status")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status de notificação: {e}")


class WorkerManager:
    """Gerenciador de workers"""
    
    def __init__(self):
        self.worker = None
        self.running = False
    
    async def start_workers(self):
        """Iniciar todos os workers"""
        try:
            # Obter dependências
            redis_client = await get_redis()
            queue_service = QueueService(redis_client)
            
            # Criar serviços de notificação
            whatsapp_service = WhatsAppService()
            email_service = EmailService()
            notification_service = NotificationService(whatsapp_service, email_service)
            
            # Criar e iniciar worker
            self.worker = MessageWorker(queue_service, notification_service)
            await self.worker.start()
            self.running = True
            
            logger.info("🎉 Workers de mensagens iniciados com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao iniciar workers: {e}")
            raise
    
    async def stop_workers(self):
        """Parar todos os workers"""
        try:
            if self.worker:
                await self.worker.stop()
                self.running = False
                logger.info("🛑 Workers de mensagens parados com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao parar workers: {e}")
            raise
    
    def is_running(self) -> bool:
        """Verificar se os workers estão rodando"""
        return self.running


# Instância global do gerenciador de workers
worker_manager = WorkerManager()





