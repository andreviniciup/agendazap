"""
Schemas Pydantic para usuários
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID

from app.utils.enums import TemplateType, PlanType


class UserBase(BaseModel):
    """Schema base para usuário"""
    email: EmailStr
    template_type: TemplateType


class UserCreate(UserBase):
    """Schema para criação de usuário"""
    password: str = Field(..., min_length=8, max_length=100)
    whatsapp_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    
    @validator('password')
    def validate_password(cls, v):
        """Validar força da senha"""
        if len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter pelo menos um número')
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
