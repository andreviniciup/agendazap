"""
Schemas Pydantic para agendamentos
"""

from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, model_validator
from uuid import UUID
from decimal import Decimal

from app.utils.enums import AppointmentStatus


class AppointmentBase(BaseModel):
    """Schema base para agendamento"""
    service_id: UUID
    client_id: Optional[UUID] = None
    client_name: str = Field(..., min_length=1, max_length=255)
    client_whatsapp: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    client_email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)
    internal_notes: Optional[str] = Field(None, max_length=1000)
    source: str = Field("web", max_length=50)
    custom_fields: Optional[Dict[str, Any]] = None


class AppointmentCreate(AppointmentBase):
    """Schema para criação de agendamento"""
    
    @model_validator(mode='after')
    def validate_times(self):
        """Validar horários e calcular end_time se necessário"""
        if not self.start_time:
            raise ValueError('start_time é obrigatório')
        
        # Se end_time não foi fornecido, será calculado automaticamente
        if not self.end_time:
            # O end_time será calculado no service baseado na duração do serviço
            pass
        elif self.end_time <= self.start_time:
            raise ValueError('end_time deve ser posterior a start_time')
        
        return self


class AppointmentUpdate(BaseModel):
    """Schema para atualização de agendamento"""
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_whatsapp: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    client_email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)
    internal_notes: Optional[str] = Field(None, max_length=1000)
    custom_fields: Optional[Dict[str, Any]] = None


class AppointmentResponse(AppointmentBase):
    """Schema para resposta de agendamento"""
    id: UUID
    user_id: UUID
    duration_minutes: int
    status: AppointmentStatus
    is_confirmed: bool
    is_cancelled: bool
    is_completed: bool
    reminder_sent: bool
    confirmation_sent: bool
    created_at: datetime
    updated_at: datetime
    service: Optional[Dict[str, Any]] = None
    client: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class AppointmentList(BaseModel):
    """Schema para listagem de agendamentos"""
    appointments: List[AppointmentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AppointmentAvailability(BaseModel):
    """Schema para disponibilidade de agendamento"""
    date: date
    available_slots: List[time]
    service_id: UUID
    service_name: str
    duration_minutes: int


class AppointmentConflict(BaseModel):
    """Schema para conflito de agendamento"""
    conflicting_appointment_id: UUID
    conflicting_start_time: datetime
    conflicting_end_time: datetime
    conflict_type: str  # overlap, same_time, etc.


class AppointmentStats(BaseModel):
    """Schema para estatísticas de agendamentos"""
    total_appointments: int
    pending_appointments: int
    confirmed_appointments: int
    cancelled_appointments: int
    completed_appointments: int
    today_appointments: int
    tomorrow_appointments: int
    this_week_appointments: int
    this_month_appointments: int
    average_duration: float
    most_popular_service: Optional[Dict[str, Any]] = None


class AppointmentSearch(BaseModel):
    """Schema para busca de agendamentos"""
    query: Optional[str] = Field(None, max_length=255, description="Termo de busca")
    service_id: Optional[UUID] = Field(None, description="Filtrar por serviço")
    client_id: Optional[UUID] = Field(None, description="Filtrar por cliente")
    status: Optional[AppointmentStatus] = Field(None, description="Filtrar por status")
    start_date: Optional[date] = Field(None, description="Data inicial")
    end_date: Optional[date] = Field(None, description="Data final")
    is_today: Optional[bool] = Field(None, description="Apenas agendamentos de hoje")
    is_tomorrow: Optional[bool] = Field(None, description="Apenas agendamentos de amanhã")
    is_past: Optional[bool] = Field(None, description="Apenas agendamentos passados")
    is_future: Optional[bool] = Field(None, description="Apenas agendamentos futuros")
    sort_by: Optional[str] = Field("start_time", description="Campo para ordenação")
    sort_order: Optional[str] = Field("asc", description="Ordem da ordenação")
    page: int = Field(1, ge=1, description="Página")
    per_page: int = Field(10, ge=1, le=100, description="Itens por página")


class PublicAppointmentCreate(BaseModel):
    """Schema para criação de agendamento público (via vitrine)"""
    service_id: UUID
    client_name: str = Field(..., min_length=1, max_length=255)
    client_whatsapp: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    client_email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    start_time: datetime
    notes: Optional[str] = Field(None, max_length=1000)
    source: str = Field("public", max_length=50)


class AppointmentReminder(BaseModel):
    """Schema para lembrete de agendamento"""
    appointment_id: UUID
    reminder_type: str  # confirmation, reminder, follow_up
    scheduled_time: datetime
    message: str
    sent: bool = False


class AppointmentBulkUpdate(BaseModel):
    """Schema para atualização em lote de agendamentos"""
    appointment_ids: List[UUID] = Field(..., min_items=1, description="IDs dos agendamentos")
    updates: Dict[str, Any] = Field(..., description="Campos para atualizar")


class AppointmentConfirmation(BaseModel):
    """Schema para confirmação de agendamento"""
    appointment_id: UUID
    confirmed: bool
    confirmation_notes: Optional[str] = Field(None, max_length=500)


class AppointmentCancellation(BaseModel):
    """Schema para cancelamento de agendamento"""
    appointment_id: UUID
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    notify_client: bool = True