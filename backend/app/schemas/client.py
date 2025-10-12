"""
Schemas para gestão de clientes
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID


class ClientBase(BaseModel):
    """Schema base para cliente"""
    name: str = Field(..., min_length=1, max_length=255, description="Nome do cliente")
    whatsapp: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$', description="Número de WhatsApp do cliente")
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$', description="Email do cliente")
    notes: Optional[str] = Field(None, description="Notas sobre o cliente")
    
    # Dados demográficos
    birth_date: Optional[date] = Field(None, description="Data de nascimento")
    gender: Optional[str] = Field(None, max_length=20, description="Gênero")
    address: Optional[str] = Field(None, description="Endereço")
    city: Optional[str] = Field(None, max_length=100, description="Cidade")
    state: Optional[str] = Field(None, max_length=50, description="Estado")
    zip_code: Optional[str] = Field(None, max_length=20, description="CEP")
    
    # Preferências
    communication_preference: Optional[str] = Field("whatsapp", max_length=20, description="Preferência de comunicação")
    source: Optional[str] = Field(None, max_length=100, description="Como conheceu o negócio")
    referral_code: Optional[str] = Field(None, max_length=50, description="Código de indicação")
    tags: Optional[List[str]] = Field(None, description="Tags personalizadas")
    
    # Campos customizados
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Campos customizados")

    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        """Validar formato do WhatsApp e adicionar +55 se necessário"""
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
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_vip: Optional[bool] = None
    
    # Dados demográficos
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    
    # Preferências
    communication_preference: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=100)
    referral_code: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    
    # Campos customizados
    custom_fields: Optional[Dict[str, Any]] = None

    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        """Validar formato do WhatsApp e adicionar +55 se necessário"""
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
    is_active: bool
    is_vip: bool
    
    # Histórico de agendamentos
    first_appointment_at: Optional[datetime] = None
    last_appointment_at: Optional[datetime] = None
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    
    # Métricas de frequência
    frequency_score: float
    appointments_this_month: int
    appointments_last_month: int
    appointments_this_year: int
    average_days_between_appointments: float
    
    # Preferências e comportamento
    preferred_services: Optional[List[UUID]] = None
    preferred_days: Optional[List[str]] = None
    preferred_times: Optional[List[str]] = None
    
    # Métricas financeiras
    total_spent: float
    average_ticket: float
    last_payment_at: Optional[datetime] = None
    
    # Propriedades calculadas
    is_regular_customer: bool
    is_frequent_customer: bool
    days_since_last_appointment: int
    customer_lifetime_days: int
    no_show_rate: float
    completion_rate: float
    
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
    total_pages: int


class ClientStats(BaseModel):
    """Schema para estatísticas de clientes"""
    total_clients: int
    active_clients: int
    new_clients_this_month: int
    regular_clients: int
    frequent_clients: int
    vip_clients: int
    average_appointments_per_client: float
    average_frequency_score: float
    top_services: List[dict]
    clients_by_source: dict
    clients_by_city: dict
    clients_by_gender: dict
    no_show_rate: float
    completion_rate: float


class ClientSearch(BaseModel):
    """Schema para busca e filtros de clientes"""
    query: Optional[str] = Field(
        None, 
        max_length=100,
        pattern=r'^[a-zA-Z0-9\s\-\.\@\+áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]*$',
        description="Termo de busca no nome, email ou WhatsApp (apenas caracteres seguros)"
    )
    is_active: Optional[bool] = Field(None, description="Filtrar por status ativo")
    is_vip: Optional[bool] = Field(None, description="Filtrar por clientes VIP")
    is_regular: Optional[bool] = Field(None, description="Filtrar por clientes regulares")
    is_frequent: Optional[bool] = Field(None, description="Filtrar por clientes frequentes")
    min_appointments: Optional[int] = Field(None, ge=0, description="Mínimo de agendamentos")
    max_appointments: Optional[int] = Field(None, ge=0, description="Máximo de agendamentos")
    min_frequency_score: Optional[float] = Field(None, ge=0, le=100, description="Score mínimo de frequência")
    max_frequency_score: Optional[float] = Field(None, ge=0, le=100, description="Score máximo de frequência")
    city: Optional[str] = Field(None, description="Filtrar por cidade")
    state: Optional[str] = Field(None, description="Filtrar por estado")
    source: Optional[str] = Field(None, description="Filtrar por fonte")
    tags: Optional[List[str]] = Field(None, description="Filtrar por tags")
    created_after: Optional[date] = Field(None, description="Clientes criados após esta data")
    created_before: Optional[date] = Field(None, description="Clientes criados antes desta data")
    last_appointment_after: Optional[date] = Field(None, description="Último agendamento após esta data")
    last_appointment_before: Optional[date] = Field(None, description="Último agendamento antes desta data")
    sort_by: Optional[str] = Field("name", description="Campo para ordenação")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Ordem da ordenação")
    page: int = Field(1, ge=1, description="Página")
    per_page: int = Field(10, ge=1, le=100, description="Itens por página")


class ClientBulkUpdate(BaseModel):
    """Schema para atualização em massa de clientes"""
    client_ids: List[UUID]
    is_active: Optional[bool] = None
    is_vip: Optional[bool] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class ClientHistory(BaseModel):
    """Schema para histórico de agendamentos do cliente"""
    client_id: UUID
    appointments: List[dict]
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    first_appointment: Optional[datetime] = None
    last_appointment: Optional[datetime] = None
    average_days_between: float
    preferred_services: List[dict]
    preferred_days: List[str]
    preferred_times: List[str]


class ClientAnalytics(BaseModel):
    """Schema para analytics avançados do cliente"""
    client_id: UUID
    lifetime_value: float
    retention_rate: float
    churn_risk: str  # low, medium, high
    next_appointment_prediction: Optional[datetime] = None
    recommended_services: List[dict]
    communication_effectiveness: dict
    seasonal_patterns: dict