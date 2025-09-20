"""
Schemas Pydantic para serviços
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.utils.enums import TemplateType


class ServiceBase(BaseModel):
    """Schema base para serviço"""
    name: str = Field(..., min_length=1, max_length=255, description="Nome do serviço")
    description: Optional[str] = Field(None, max_length=1000, description="Descrição do serviço")
    duration: int = Field(..., ge=1, le=1440, description="Duração em minutos (1-1440)")
    price: Optional[Decimal] = Field(None, ge=0, description="Preço do serviço")
    images: Optional[List[str]] = Field(None, max_items=5, description="URLs das imagens (máximo 5)")
    credentials: Optional[str] = Field(None, max_length=255, description="Credenciais profissionais")
    promotions: Optional[str] = Field(None, max_length=500, description="Promoções e ofertas")
    category_id: Optional[UUID] = Field(None, description="ID da categoria do serviço")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Campos customizados baseados no template")


class ServiceCreate(ServiceBase):
    """Schema para criação de serviço"""
    
    @validator('images')
    def validate_images(cls, v):
        """Validar imagens"""
        if v and len(v) > 5:
            raise ValueError('Máximo de 5 imagens permitidas')
        return v
    
    @validator('duration')
    def validate_duration(cls, v):
        """Validar duração"""
        if v < 1 or v > 1440:  # máximo 24 horas
            raise ValueError('Duração deve estar entre 1 e 1440 minutos')
        return v


class ServiceUpdate(BaseModel):
    """Schema para atualização de serviço"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    duration: Optional[int] = Field(None, ge=1, le=1440)
    price: Optional[Decimal] = Field(None, ge=0)
    images: Optional[List[str]] = Field(None, max_items=5)
    credentials: Optional[str] = Field(None, max_length=255)
    promotions: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


class ServiceResponse(ServiceBase):
    """Schema para resposta de serviço"""
    id: UUID
    user_id: UUID
    is_active: bool
    is_featured: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    category: Optional[Dict[str, Any]] = Field(None, description="Informações da categoria")
    
    class Config:
        from_attributes = True


class ServiceList(BaseModel):
    """Schema para lista de serviços"""
    services: List[ServiceResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ServiceStats(BaseModel):
    """Schema para estatísticas de serviços"""
    total_services: int
    active_services: int
    inactive_services: int
    featured_services: int
    services_with_images: int
    services_with_promotions: int
    average_duration: float
    average_price: Optional[Decimal] = None


class ServiceSearch(BaseModel):
    """Schema para busca de serviços"""
    query: Optional[str] = Field(None, max_length=255, description="Termo de busca")
    category_id: Optional[UUID] = Field(None, description="Filtrar por categoria")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Preço mínimo")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Preço máximo")
    min_duration: Optional[int] = Field(None, ge=1, description="Duração mínima")
    max_duration: Optional[int] = Field(None, ge=1, description="Duração máxima")
    is_active: Optional[bool] = Field(None, description="Filtrar por status ativo")
    is_featured: Optional[bool] = Field(None, description="Filtrar por serviços em destaque")
    sort_by: Optional[str] = Field("name", description="Campo para ordenação")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Ordem da ordenação")
    page: int = Field(1, ge=1, description="Página")
    per_page: int = Field(10, ge=1, le=100, description="Itens por página")


class ServiceBulkUpdate(BaseModel):
    """Schema para atualização em lote de serviços"""
    service_ids: List[UUID] = Field(..., min_items=1, description="IDs dos serviços")
    updates: Dict[str, Any] = Field(..., description="Campos para atualizar")


class ServiceTemplateValidation(BaseModel):
    """Schema para validação baseada no template"""
    template_type: TemplateType
    requires_price: bool
    requires_images: bool
    requires_credentials: bool
    max_images: int
    custom_fields_schema: Optional[Dict[str, Any]] = None