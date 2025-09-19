"""
Schemas Pydantic para agendamentos
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID

from app.utils.enums import AppointmentStatus


class AppointmentBase(BaseModel):
    """Schema base para agendamento"""
    client_name: str = Field(..., min_length=1, max_length=255)
    client_whatsapp: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    client_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validar se end_time é posterior a start_time"""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time deve ser posterior a start_time')
        return v
    
    @validator('client_whatsapp')
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


class AppointmentCreate(AppointmentBase):
    """Schema para criação de agendamento"""
    service_id: UUID


class AppointmentUpdate(BaseModel):
    """Schema para atualização de agendamento"""
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_whatsapp: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    client_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validar se end_time é posterior a start_time"""
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError('end_time deve ser posterior a start_time')
        return v


class AppointmentResponse(AppointmentBase):
    """Schema para resposta de agendamento"""
    id: UUID
    service_id: UUID
    user_id: UUID
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentList(BaseModel):
    """Schema para listagem de agendamentos"""
    appointments: list[AppointmentResponse]
    total: int
    page: int
    per_page: int


class AppointmentAvailability(BaseModel):
    """Schema para verificar disponibilidade"""
    service_id: UUID
    date: datetime
    duration: int  # em minutos
