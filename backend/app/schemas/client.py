"""
Schemas Pydantic para clientes
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from uuid import UUID


class ClientBase(BaseModel):
    """Schema base para cliente"""
    name: str = Field(..., min_length=1, max_length=255)
    whatsapp: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    
    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        """Validar formato do WhatsApp"""
        if not v.startswith('+'):
            if v.startswith('55'):
                v = '+' + v
            elif v.startswith('0'):
                v = '+55' + v[1:]
            else:
                v = '+55' + v
        return v


class ClientCreate(ClientBase):
    """Schema para criação de cliente"""
    pass


class ClientUpdate(BaseModel):
    """Schema para atualização de cliente"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    whatsapp: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    
    @validator('whatsapp')
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


class ClientResponse(ClientBase):
    """Schema para resposta de cliente"""
    id: UUID
    user_id: UUID
    appointment_history: Optional[List[UUID]] = None
    frequency: int
    preferred_services: Optional[List[UUID]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ClientList(BaseModel):
    """Schema para listagem de clientes"""
    clients: List[ClientResponse]
    total: int
    page: int
    per_page: int


class ClientStats(BaseModel):
    """Schema para estatísticas do cliente"""
    total_appointments: int
    last_appointment: Optional[datetime]
    favorite_service: Optional[str]
    total_spent: Optional[float]
