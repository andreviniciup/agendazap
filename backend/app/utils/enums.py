"""
Enums utilizados na aplicação
"""

from enum import Enum


class TemplateType(str, Enum):
    """Tipos de template disponíveis"""
    CONSULTATION = "consultation"  # Consulta profissional (formal)
    SERVICE_TABLE = "service_table"  # Tabela de serviços (visual)


class PlanType(str, Enum):
    """Tipos de planos disponíveis"""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AppointmentStatus(str, Enum):
    """Status dos agendamentos"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class MessageType(str, Enum):
    """Tipos de mensagens para WhatsApp"""
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    POST_APPOINTMENT = "post_appointment"
    CANCELLATION = "cancellation"


class NotificationChannel(str, Enum):
    """Canais de notificação"""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    BOTH = "both"
