"""
Serviço para gerenciamento de templates de mensagem
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging
from uuid import UUID

from app.models.user import User
from app.utils.enums import TemplateType
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class TemplateService:
    """Serviço para operações relacionadas a templates de mensagem"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_default_templates(self) -> Dict[str, Dict[str, str]]:
        """Obter templates padrão do sistema"""
        return {
            "appointment_confirmation": {
                "consultation": """Prezado(a) {client_name},

Sua consulta com {provider_name} foi confirmada para {date} às {time}.

Para dúvidas, responda esta mensagem.

Atenciosamente,
AgendaZap""",
                "service_table": """Oi {client_name}! 😊

Seu {service_name} ({price}) está agendado para {date} às {time}!

Para confirmar ou mudar, responda aqui.

AgendaZap"""
            },
            "appointment_reminder": {
                "consultation": """Lembrete: Sua consulta com {provider_name} é amanhã às {time}.

Se precisar remarcar, avise.

Atenciosamente,
AgendaZap""",
                "service_table": """Ei {client_name}, amanhã é seu {service_name} às {time}! 💅

Se precisar cancelar, me avise.

AgendaZap"""
            },
            "appointment_follow_up": {
                "consultation": """Olá {client_name},

Como foi sua sessão com {provider_name}?

Seu feedback é importante. Responda aqui.

Obrigado,
AgendaZap""",
                "service_table": """E aí {client_name}, gostou do {service_name}? ⭐

Dê uma nota ou agende novamente!

AgendaZap"""
            },
            "appointment_cancellation": {
                "consultation": """Prezado(a) {client_name},

Sua consulta com {provider_name} para {date} às {time} foi cancelada.

Para reagendar, entre em contato conosco.

Atenciosamente,
AgendaZap""",
                "service_table": """Oi {client_name},

Seu {service_name} para {date} às {time} foi cancelado.

Para reagendar, me chame aqui! 😊

AgendaZap"""
            }
        }
    
    def get_user_templates(
        self, 
        user: User, 
        use_cache: bool = True
    ) -> Dict[str, str]:
        """Obter templates personalizados do usuário com cache"""
        try:
            # Tentar obter do cache primeiro
            if use_cache:
                cached_templates = cache_service.get_message_template(f"user_{user.id}")
                if cached_templates:
                    logger.debug(f"Templates obtidos do cache para usuário {user.id}")
                    return cached_templates
            
            # Se não está no cache, buscar do banco ou usar padrões
            # Por enquanto, vamos usar os templates padrão baseados no tipo do usuário
            default_templates = self.get_default_templates()
            user_templates = {}
            
            for template_type, templates in default_templates.items():
                user_templates[template_type] = templates.get(
                    user.template_type.value, 
                    templates["consultation"]  # fallback
                )
            
            # Salvar no cache
            if use_cache:
                cache_service.set_message_template(f"user_{user.id}", user_templates)
                logger.debug(f"Templates salvos no cache para usuário {user.id}")
            
            return user_templates
            
        except Exception as e:
            logger.error(f"Erro ao obter templates do usuário: {e}")
            # Em caso de erro, retornar templates padrão
            default_templates = self.get_default_templates()
            return {
                template_type: templates.get("consultation", "")
                for template_type, templates in default_templates.items()
            }
    
    def get_template_by_type(
        self, 
        user: User, 
        template_type: str,
        use_cache: bool = True
    ) -> str:
        """Obter template específico do usuário"""
        try:
            user_templates = self.get_user_templates(user, use_cache)
            return user_templates.get(template_type, "")
            
        except Exception as e:
            logger.error(f"Erro ao obter template {template_type}: {e}")
            return ""
    
    def update_user_template(
        self, 
        user: User, 
        template_type: str, 
        template_content: str
    ) -> bool:
        """Atualizar template personalizado do usuário"""
        try:
            # Por enquanto, vamos apenas invalidar o cache
            # Em uma implementação futura, salvaríamos no banco de dados
            
            # Invalidar cache de templates do usuário
            cache_service.invalidate_template(f"user_{user.id}")
            
            logger.info(f"Template {template_type} atualizado para usuário {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar template {template_type}: {e}")
            return False
    
    def render_template(
        self, 
        user: User, 
        template_type: str, 
        variables: Dict[str, Any],
        use_cache: bool = True
    ) -> str:
        """Renderizar template com variáveis"""
        try:
            template_content = self.get_template_by_type(user, template_type, use_cache)
            
            if not template_content:
                logger.warning(f"Template {template_type} não encontrado para usuário {user.id}")
                return ""
            
            # Substituir variáveis no template
            rendered_content = template_content
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                rendered_content = rendered_content.replace(placeholder, str(value))
            
            return rendered_content
            
        except Exception as e:
            logger.error(f"Erro ao renderizar template {template_type}: {e}")
            return ""
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Obter lista de templates disponíveis"""
        return [
            {
                "type": "appointment_confirmation",
                "name": "Confirmação de Agendamento",
                "description": "Mensagem enviada quando um agendamento é confirmado"
            },
            {
                "type": "appointment_reminder",
                "name": "Lembrete de Agendamento",
                "description": "Mensagem enviada 24h antes do agendamento"
            },
            {
                "type": "appointment_follow_up",
                "name": "Follow-up Pós-Atendimento",
                "description": "Mensagem enviada após o atendimento"
            },
            {
                "type": "appointment_cancellation",
                "name": "Cancelamento de Agendamento",
                "description": "Mensagem enviada quando um agendamento é cancelado"
            }
        ]
    
    def get_template_variables(self, template_type: str) -> List[Dict[str, str]]:
        """Obter variáveis disponíveis para um tipo de template"""
        variables_map = {
            "appointment_confirmation": [
                {"name": "client_name", "description": "Nome do cliente"},
                {"name": "provider_name", "description": "Nome do provedor"},
                {"name": "service_name", "description": "Nome do serviço"},
                {"name": "date", "description": "Data do agendamento"},
                {"name": "time", "description": "Horário do agendamento"},
                {"name": "price", "description": "Preço do serviço (apenas para service_table)"}
            ],
            "appointment_reminder": [
                {"name": "client_name", "description": "Nome do cliente"},
                {"name": "provider_name", "description": "Nome do provedor"},
                {"name": "service_name", "description": "Nome do serviço"},
                {"name": "time", "description": "Horário do agendamento"}
            ],
            "appointment_follow_up": [
                {"name": "client_name", "description": "Nome do cliente"},
                {"name": "provider_name", "description": "Nome do provedor"},
                {"name": "service_name", "description": "Nome do serviço"}
            ],
            "appointment_cancellation": [
                {"name": "client_name", "description": "Nome do cliente"},
                {"name": "provider_name", "description": "Nome do provedor"},
                {"name": "service_name", "description": "Nome do serviço"},
                {"name": "date", "description": "Data do agendamento"},
                {"name": "time", "description": "Horário do agendamento"}
            ]
        }
        
        return variables_map.get(template_type, [])
    
    def validate_template_content(self, template_content: str) -> Dict[str, Any]:
        """Validar conteúdo do template"""
        errors = []
        warnings = []
        
        # Verificar se o template não está vazio
        if not template_content.strip():
            errors.append("Template não pode estar vazio")
        
        # Verificar se tem pelo menos uma variável
        if "{" not in template_content or "}" not in template_content:
            warnings.append("Template não contém variáveis dinâmicas")
        
        # Verificar variáveis malformadas
        import re
        malformed_vars = re.findall(r'\{[^}]*[^a-zA-Z_][^}]*\}', template_content)
        if malformed_vars:
            errors.append(f"Variáveis malformadas encontradas: {', '.join(malformed_vars)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def invalidate_user_templates(self, user_id: UUID) -> bool:
        """Invalidar cache de templates do usuário"""
        try:
            cache_service.invalidate_template(f"user_{user_id}")
            logger.debug(f"Cache de templates invalidado para usuário {user_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao invalidar cache de templates: {e}")
            return False



