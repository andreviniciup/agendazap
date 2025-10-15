"""
Serviço de notificações WhatsApp e Email
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Serviço para envio de mensagens WhatsApp via Twilio"""
    
    def __init__(self):
        # Configurações do Twilio
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')
        
        # Inicializar cliente Twilio
        if self.account_sid and self.auth_token:
            self.twilio_client = TwilioClient(self.account_sid, self.auth_token)
        else:
            self.twilio_client = None
            logger.warning("Twilio não configurado - mensagens WhatsApp não serão enviadas")
    
    async def send_message(
        self, 
        to_number: str, 
        message: str, 
        template: str = None
    ) -> Dict[str, Any]:
        """Enviar mensagem WhatsApp via Twilio"""
        try:
            # Verificar se Twilio está configurado
            if not self.twilio_client:
                return {
                    "success": False,
                    "error": "Twilio não configurado",
                    "to_number": to_number
                }
            
            # Limpar número do WhatsApp
            clean_number = self._clean_phone_number(to_number)
            
            if not clean_number:
                return {
                    "success": False,
                    "error": "Número de telefone inválido",
                    "to_number": to_number
                }
            
            # Formatar número para WhatsApp
            whatsapp_to = f"whatsapp:{clean_number}"
            whatsapp_from = f"whatsapp:{self.whatsapp_from}"
            
            # Enviar mensagem via Twilio
            try:
                message_obj = self.twilio_client.messages.create(
                    body=message,
                    from_=whatsapp_from,
                    to=whatsapp_to
                )
                
                logger.info(f"Mensagem WhatsApp enviada para {clean_number} - SID: {message_obj.sid}")
                return {
                    "success": True,
                    "message_id": message_obj.sid,
                    "to_number": clean_number,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": message_obj.status
                }
                
            except TwilioException as e:
                error_msg = f"Erro do Twilio: {str(e)}"
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
    """Serviço para envio de emails via SMTP"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', '')
        self.from_name = getattr(settings, 'FROM_NAME', 'AgendaZap')
        
        # Verificar se SMTP está configurado
        if not all([self.smtp_username, self.smtp_password, self.from_email]):
            logger.warning("SMTP não configurado - emails não serão enviados")
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Enviar email via SMTP"""
        try:
            # Verificar se SMTP está configurado
            if not all([self.smtp_username, self.smtp_password, self.from_email]):
                return {
                    "success": False,
                    "error": "SMTP não configurado",
                    "to_email": to_email
                }
            
            # Criar mensagem
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            # Adicionar corpo da mensagem
            if is_html:
                message.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                message.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Conectar e enviar
            smtp = aiosmtplib.SMTP(hostname=self.smtp_server, port=self.smtp_port)
            await smtp.connect()
            await smtp.starttls()
            await smtp.login(self.smtp_username, self.smtp_password)
            
            await smtp.send_message(message)
            await smtp.quit()
            
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
    
    async def send_appointment_confirmation_email(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_email: str,
        service_name: str,
        appointment_time: datetime
    ) -> Dict[str, Any]:
        """Enviar email de confirmação de agendamento"""
        subject = "Agendamento Confirmado - AgendaZap"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">🎉 Agendamento Confirmado!</h2>
                
                <p>Olá <strong>{client_name}</strong>!</p>
                
                <p>Seu agendamento foi confirmado com sucesso:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">📅 Detalhes do Agendamento</h3>
                    <p><strong>Serviço:</strong> {service_name}</p>
                    <p><strong>Data e Hora:</strong> {appointment_time.strftime('%d/%m/%Y às %H:%M')}</p>
                </div>
                
                <p>Se precisar reagendar ou cancelar, entre em contato conosco.</p>
                
                <p>Obrigado pela preferência! 🙏</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">
                    Este é um email automático do sistema AgendaZap.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(client_email, subject, html_body, is_html=True)
    
    async def send_appointment_reminder_email(
        self, 
        appointment_id: UUID, 
        client_name: str, 
        client_email: str,
        service_name: str,
        appointment_time: datetime
    ) -> Dict[str, Any]:
        """Enviar email de lembrete de agendamento"""
        subject = "Lembrete de Agendamento - AgendaZap"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">⏰ Lembrete de Agendamento</h2>
                
                <p>Olá <strong>{client_name}</strong>!</p>
                
                <p>Este é um lembrete do seu agendamento:</p>
                
                <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">📅 Detalhes do Agendamento</h3>
                    <p><strong>Serviço:</strong> {service_name}</p>
                    <p><strong>Data e Hora:</strong> {appointment_time.strftime('%d/%m/%Y às %H:%M')}</p>
                </div>
                
                <p>Nos vemos em breve! 😊</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">
                    Este é um email automático do sistema AgendaZap.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(client_email, subject, html_body, is_html=True)


class NotificationService:
    """Serviço principal de notificações"""
    
    def __init__(self, whatsapp_service: WhatsAppService = None, email_service: EmailService = None):
        self.whatsapp_service = whatsapp_service or WhatsAppService()
        self.email_service = email_service or EmailService()
    
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
            if notification_type == "confirmation":
                result = await self.email_service.send_appointment_confirmation_email(
                    appointment_id, client_name, client_email, service_name, appointment_time
                )
            elif notification_type == "reminder":
                result = await self.email_service.send_appointment_reminder_email(
                    appointment_id, client_name, client_email, service_name, appointment_time
                )
            else:
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
    
    async def send_handoff_alert(
        self,
        provider_email: str,
        provider_whatsapp: str = None,
        client_whatsapp: str = None,
        reason: str = "human_requested",
        conversation_snippet: List[Dict[str, str]] = None,
        alert_channels: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Enviar alerta de handoff ao prestador
        
        Args:
            provider_email: Email do prestador
            provider_whatsapp: WhatsApp do prestador (opcional)
            client_whatsapp: WhatsApp do cliente
            reason: Razão do handoff
            conversation_snippet: Trecho da conversa
            alert_channels: Canais para enviar alerta
            metadata: Metadados adicionais
        
        Returns:
            Resultados do envio
        """
        results = {}
        alert_channels = alert_channels or ["email"]
        
        # Mapear razões para mensagens amigáveis
        reason_messages = {
            "human_requested": "Cliente solicitou falar com um profissional",
            "media": "Cliente enviou mídia (áudio/imagem/vídeo/documento)",
            "low_confidence": "Bot com baixa confiança na resposta",
            "unknown": "Intenção não compreendida"
        }
        
        reason_text = reason_messages.get(reason, reason)
        
        # Construir snippet da conversa
        snippet_text = ""
        if conversation_snippet:
            snippet_lines = []
            for item in conversation_snippet[-5:]:  # Últimas 5 interações
                user_msg = item.get("text", "")
                bot_msg = item.get("response", "")
                if user_msg:
                    snippet_lines.append(f"Cliente: {user_msg[:100]}")
                if bot_msg:
                    snippet_lines.append(f"Bot: {bot_msg[:100]}")
            snippet_text = "\n".join(snippet_lines)
        
        # Enviar email se solicitado
        if "email" in alert_channels and provider_email:
            subject = f"🔔 Alerta: Cliente {client_whatsapp or 'desconhecido'} precisa de atendimento"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #d32f2f;">🔔 Alerta de Atendimento</h2>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #856404;">Cliente precisa de atendimento</h3>
                        <p><strong>Cliente:</strong> {client_whatsapp or "Não identificado"}</p>
                        <p><strong>Motivo:</strong> {reason_text}</p>
                    </div>
                    
                    {f'''
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2c3e50;">📝 Contexto da Conversa</h3>
                        <pre style="white-space: pre-wrap; font-size: 13px; color: #666;">{snippet_text}</pre>
                    </div>
                    ''' if snippet_text else ''}
                    
                    <p><strong>Próximos passos:</strong></p>
                    <ul>
                        <li>Entre em contato com o cliente pelo WhatsApp: {client_whatsapp}</li>
                        <li>Revise o contexto da conversa acima</li>
                        <li>Responda prontamente para melhor experiência do cliente</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Este é um alerta automático do sistema AgendaZap.
                    </p>
                </div>
            </body>
            </html>
            """
            
            email_result = await self.email_service.send_email(
                provider_email,
                subject,
                html_body,
                is_html=True
            )
            results["email"] = email_result
        
        # Enviar WhatsApp se solicitado
        if "whatsapp" in alert_channels and provider_whatsapp:
            whatsapp_message = f"""
🔔 *Alerta de Atendimento*

Cliente {client_whatsapp or "não identificado"} precisa de atendimento.

*Motivo:* {reason_text}

{f"*Últimas mensagens:*\n{snippet_text[:500]}" if snippet_text else ""}

Responda o quanto antes para melhor experiência! 🙏
            """.strip()
            
            whatsapp_result = await self.whatsapp_service.send_message(
                provider_whatsapp,
                whatsapp_message
            )
            results["whatsapp"] = whatsapp_result
        
        return results





