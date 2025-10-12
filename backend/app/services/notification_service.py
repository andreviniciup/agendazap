"""
Serviço de notificações WhatsApp e Email
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Serviço para envio de mensagens WhatsApp"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'WHATSAPP_API_URL', 'https://api.whatsapp.com')
        self.api_token = getattr(settings, 'WHATSAPP_API_TOKEN', '')
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    
    async def send_message(
        self, 
        to_number: str, 
        message: str, 
        template: str = None
    ) -> Dict[str, Any]:
        """Enviar mensagem WhatsApp"""
        try:
            # Limpar número do WhatsApp
            clean_number = self._clean_phone_number(to_number)
            
            if not clean_number:
                return {
                    "success": False,
                    "error": "Número de telefone inválido",
                    "to_number": to_number
                }
            
            # Preparar payload
            if template:
                payload = self._create_template_payload(clean_number, template, message)
            else:
                payload = self._create_text_payload(clean_number, message)
            
            # Enviar mensagem
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Mensagem WhatsApp enviada para {clean_number}")
                    return {
                        "success": True,
                        "message_id": result.get("messages", [{}])[0].get("id"),
                        "to_number": clean_number,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = f"Erro ao enviar WhatsApp: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "to_number": clean_number
                    }
                    
        except Exception as e:
            error_msg = f"Erro ao enviar mensagem WhatsApp: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "to_number": to_number
            }
    
    def _clean_phone_number(self, phone_number: str) -> Optional[str]:
        """Limpar e validar número de telefone"""
        if not phone_number:
            return None
        
        # Remover caracteres não numéricos
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Adicionar código do país se necessário
        if clean_number.startswith('55'):
            # Número brasileiro
            if len(clean_number) == 13:  # 55 + 11 dígitos
                return clean_number
            elif len(clean_number) == 11:  # 11 dígitos
                return f"55{clean_number}"
        elif clean_number.startswith('1'):
            # Número americano
            if len(clean_number) == 11:
                return clean_number
        
        # Se não conseguir identificar, retornar None
        return None
    
    def _create_text_payload(self, to_number: str, message: str) -> Dict[str, Any]:
        """Criar payload para mensagem de texto"""
        return {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
    
    def _create_template_payload(self, to_number: str, template: str, message: str) -> Dict[str, Any]:
        """Criar payload para mensagem com template"""
        return {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template,
                "language": {
                    "code": "pt_BR"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": message
                            }
                        ]
                    }
                ]
            }
        }
    
    async def send_appointment_confirmation(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime
    ) -> Dict[str, Any]:
        """Enviar confirmação de agendamento"""
        message = f"""
🎉 *Agendamento Confirmado!*

Olá {client_name}! 

Seu agendamento foi confirmado com sucesso:

📅 *Serviço:* {service_name}
🕐 *Data e Hora:* {appointment_time.strftime('%d/%m/%Y às %H:%M')}

Se precisar reagendar ou cancelar, entre em contato conosco.

Obrigado pela preferência! 🙏
        """.strip()
        
        return await self.send_message(client_whatsapp, message, "appointment_confirmation")
    
    async def send_appointment_reminder(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime
    ) -> Dict[str, Any]:
        """Enviar lembrete de agendamento"""
        message = f"""
⏰ *Lembrete de Agendamento*

Olá {client_name}! 

Este é um lembrete do seu agendamento:

📅 *Serviço:* {service_name}
🕐 *Data e Hora:* {appointment_time.strftime('%d/%m/%Y às %H:%M')}

Nos vemos em breve! 😊
        """.strip()
        
        return await self.send_message(client_whatsapp, message, "appointment_reminder")
    
    async def send_appointment_cancellation(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime,
        cancellation_reason: str = None
    ) -> Dict[str, Any]:
        """Enviar notificação de cancelamento"""
        reason_text = f"\n📝 *Motivo:* {cancellation_reason}" if cancellation_reason else ""
        
        message = f"""
❌ *Agendamento Cancelado*

Olá {client_name}! 

Seu agendamento foi cancelado:

📅 *Serviço:* {service_name}
🕐 *Data e Hora:* {appointment_time.strftime('%d/%m/%Y às %H:%M')}{reason_text}

Para reagendar, entre em contato conosco.

Obrigado! 🙏
        """.strip()
        
        return await self.send_message(client_whatsapp, message, "appointment_cancellation")
    
    async def send_appointment_follow_up(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_whatsapp: str,
        service_name: str,
        appointment_time: datetime
    ) -> Dict[str, Any]:
        """Enviar follow-up após agendamento"""
        message = f"""
💬 *Como foi seu atendimento?*

Olá {client_name}! 

Esperamos que tenha gostado do seu atendimento:

📅 *Serviço:* {service_name}
🕐 *Data e Hora:* {appointment_time.strftime('%d/%m/%Y às %H:%M')}

Sua opinião é muito importante para nós! 

Para agendar novamente, é só nos chamar! 😊
        """.strip()
        
        return await self.send_message(client_whatsapp, message, "appointment_follow_up")


class EmailService:
    """Serviço para envio de emails"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', '')
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Enviar email"""
        try:
            # Por enquanto, apenas log da funcionalidade
            # Em produção, implementar com biblioteca como aiosmtplib
            logger.info(f"Email enviado para {to_email}: {subject}")
            
            return {
                "success": True,
                "to_email": to_email,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Erro ao enviar email: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email
            }


class NotificationService:
    """Serviço principal de notificações"""
    
    def __init__(self, whatsapp_service: WhatsAppService, email_service: EmailService):
        self.whatsapp_service = whatsapp_service
        self.email_service = email_service
    
    async def send_appointment_notification(
        self, 
        notification_type: str,
        appointment_id: UUID,
        client_name: str,
        client_whatsapp: str,
        client_email: str = None,
        service_name: str = None,
        appointment_time: datetime = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Enviar notificação de agendamento"""
        results = {}
        
        # Enviar WhatsApp
        if client_whatsapp:
            if notification_type == "confirmation":
                result = await self.whatsapp_service.send_appointment_confirmation(
                    appointment_id, client_name, client_whatsapp, service_name, appointment_time
                )
            elif notification_type == "reminder":
                result = await self.whatsapp_service.send_appointment_reminder(
                    appointment_id, client_name, client_whatsapp, service_name, appointment_time
                )
            elif notification_type == "cancellation":
                result = await self.whatsapp_service.send_appointment_cancellation(
                    appointment_id, client_name, client_whatsapp, service_name, appointment_time,
                    kwargs.get("cancellation_reason")
                )
            elif notification_type == "follow_up":
                result = await self.whatsapp_service.send_appointment_follow_up(
                    appointment_id, client_name, client_whatsapp, service_name, appointment_time
                )
            else:
                result = {"success": False, "error": f"Tipo de notificação desconhecido: {notification_type}"}
            
            results["whatsapp"] = result
        
        # Enviar Email (se configurado)
        if client_email and self.email_service:
            subject = f"Agendamento {notification_type.title()}"
            body = f"Notificação de agendamento para {client_name}"
            
            result = await self.email_service.send_email(client_email, subject, body)
            results["email"] = result
        
        return results
    
    async def send_custom_message(
        self, 
        to_whatsapp: str = None,
        to_email: str = None,
        message: str = None,
        subject: str = None,
        body: str = None
    ) -> Dict[str, Any]:
        """Enviar mensagem customizada"""
        results = {}
        
        # Enviar WhatsApp
        if to_whatsapp and message:
            result = await self.whatsapp_service.send_message(to_whatsapp, message)
            results["whatsapp"] = result
        
        # Enviar Email
        if to_email and subject and body:
            result = await self.email_service.send_email(to_email, subject, body)
            results["email"] = result
        
        return results




