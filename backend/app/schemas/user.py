"""
Schemas Pydantic para usuários
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID

from app.utils.enums import TemplateType, PlanType


class UserBase(BaseModel):
    """Schema base para usuário"""
    email: EmailStr
    template_type: TemplateType


class UserCreate(UserBase):
    """Schema para criação de usuário"""
    password: str = Field(..., min_length=12, max_length=128)
    whatsapp_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    
    @validator('password')
    def validate_password(cls, v):
        """Validar força da senha com requisitos rigorosos"""
        # Comprimento mínimo
        if len(v) < 12:
            raise ValueError('Senha deve ter pelo menos 12 caracteres')
        
        # Verificar se contém letra maiúscula
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        
        # Verificar se contém letra minúscula
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        
        # Verificar se contém número
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter pelo menos um número')
        
        # Verificar se contém caractere especial
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError('Senha deve conter pelo menos um caractere especial (!@#$%^&* etc)')
        
        # Verificar se não tem caracteres repetidos em sequência (mais de 3)
        for i in range(len(v) - 3):
            if v[i] == v[i+1] == v[i+2] == v[i+3]:
                raise ValueError('Senha não pode ter mais de 3 caracteres iguais em sequência')
        
        # Verificar se não é uma senha comum
        common_passwords = [
            'password', '12345678', 'qwerty', 'abc123', 'password123',
            'senha123', '123456789', 'admin123', 'letmein', 'welcome'
        ]
        if v.lower() in common_passwords:
            raise ValueError('Senha muito comum. Escolha uma senha mais segura')
        
        # Verificar se não contém sequências óbvias
        sequences = ['123456', 'abcdef', 'qwerty', '987654', 'fedcba']
        for seq in sequences:
            if seq in v.lower():
                raise ValueError('Senha não pode conter sequências óbvias (123456, qwerty, etc)')
        
        return v
    
    @validator('whatsapp_number')
    def validate_whatsapp(cls, v):
        """Validar formato do WhatsApp"""
        if v and not v.startswith('+'):
            # Adicionar +55 se não tiver código do país
            if v.startswith('55'):
                v = '+' + v
            elif v.startswith('0'):
                v = '+55' + v[1:]
            else:
                v = '+55' + v
        return v


class UserLogin(BaseModel):
    """Schema para login de usuário"""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema para resposta de usuário"""
    id: UUID
    template_type: TemplateType
    plan_type: PlanType
    whatsapp_number: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema para atualização de usuário"""
    email: Optional[EmailStr] = None
    template_type: Optional[TemplateType] = None
    whatsapp_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    
    @validator('whatsapp_number')
    def validate_whatsapp(cls, v):
        """Validar formato do WhatsApp"""
        if v and not v.startswith('+'):
            if v.startswith('55'):
                v = '+' + v
            elif v.startswith('0'):
                v = '+55' + v[1:]
            else:
                v = '+55' + v
        return v


class UserProfile(UserResponse):
    """Schema para perfil completo do usuário"""
    # Adicionar campos específicos do perfil se necessário
    pass


class UserPlanInfo(BaseModel):
    """Schema para informações do plano do usuário"""
    plan_type: PlanType
    limits: dict
    usage: dict
    
    class Config:
        from_attributes = True


class QuietHours(BaseModel):
    """Schema para horários silenciosos"""
    start: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$', description="Hora início (HH:MM)")
    end: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$', description="Hora fim (HH:MM)")


class NotificationPreferences(BaseModel):
    """Schema para preferências de notificação do prestador"""
    alert_channels: List[str] = Field(
        default=["email"],
        description="Canais de alerta (email, whatsapp)"
    )
    quiet_hours: Optional[QuietHours] = Field(
        None,
        description="Horários silenciosos"
    )
    handoff_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Limiar de confiança para acionar handoff"
    )
    trigger_on_media: bool = Field(
        default=True,
        description="Acionar handoff ao detectar mídia"
    )
    include_conversation_snippet: bool = Field(
        default=True,
        description="Incluir trecho da conversa no alerta"
    )
    
    @validator('alert_channels')
    def validate_channels(cls, v):
        """Validar canais permitidos"""
        allowed = {'email', 'whatsapp'}
        for channel in v:
            if channel not in allowed:
                raise ValueError(f'Canal inválido: {channel}. Permitidos: {allowed}')
        return v


class BusinessProfileMetadata(BaseModel):
    """Schema para metadados do perfil do negócio"""
    description: Optional[str] = Field(None, max_length=1000, description="Descrição do negócio")
    regions: Optional[List[str]] = Field(None, description="Regiões de atendimento")
    has_parking: Optional[bool] = Field(None, description="Tem estacionamento")
    allow_companion: Optional[bool] = Field(None, description="Aceita acompanhante")
    payment_methods: Optional[List[str]] = Field(None, description="Formas de pagamento")
    cancel_policy: Optional[Dict[str, Any]] = Field(None, description="Política de cancelamento")
    work_location: Optional[str] = Field(None, description="Local de trabalho (studio, domicilio, ambos)")
    languages: Optional[List[str]] = Field(None, description="Idiomas atendidos")
    
    @validator('payment_methods')
    def validate_payment_methods(cls, v):
        """Validar formas de pagamento"""
        if not v:
            return v
        allowed = {'dinheiro', 'pix', 'cartao', 'debito', 'credito', 'transferencia'}
        for method in v:
            if method.lower() not in allowed:
                raise ValueError(f'Forma de pagamento inválida: {method}')
        return v


class NotificationPreferencesUpdate(BaseModel):
    """Schema para atualização de preferências de notificação"""
    alert_channels: Optional[List[str]] = None
    quiet_hours: Optional[QuietHours] = None
    handoff_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    trigger_on_media: Optional[bool] = None
    include_conversation_snippet: Optional[bool] = None


class BusinessProfileUpdate(BaseModel):
    """Schema para atualização do perfil do negócio"""
    description: Optional[str] = Field(None, max_length=1000)
    regions: Optional[List[str]] = None
    has_parking: Optional[bool] = None
    allow_companion: Optional[bool] = None
    payment_methods: Optional[List[str]] = None
    cancel_policy: Optional[Dict[str, Any]] = None
    work_location: Optional[str] = None
    languages: Optional[List[str]] = None
