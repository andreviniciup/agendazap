"""
Schemas Pydantic para serviços
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from uuid import UUID
from decimal import Decimal

from app.utils.enums import TemplateType


class ServiceBase(BaseModel):
    """Schema base para serviço"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    duration: int = Field(..., gt=0, le=480)  # máximo 8 horas
    price: Optional[Decimal] = Field(None, ge=0)
    images: Optional[List[str]] = Field(None, max_items=5)
    credentials: Optional[str] = None
    promotions: Optional[str] = None


class ServiceCreate(ServiceBase):
    """Schema para criação de serviço"""
    
    @validator('images')
    def validate_images(cls, v, values):
        """Validar imagens baseado no template do usuário"""
        if v and len(v) > 5:
            raise ValueError('Máximo de 5 imagens permitidas')
        return v
    
    @validator('price')
    def validate_price_for_template(cls, v, values):
        """Validar preço baseado no template"""
        # Esta validação será feita no service layer
        # onde temos acesso ao template_type do usuário
        return v


class ServiceUpdate(BaseModel):
    """Schema para atualização de serviço"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration: Optional[int] = Field(None, gt=0, le=480)
    price: Optional[Decimal] = Field(None, ge=0)
    images: Optional[List[str]] = Field(None, max_items=5)
    credentials: Optional[str] = None
    promotions: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    """Schema para resposta de serviço"""
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ServiceList(BaseModel):
    """Schema para listagem de serviços"""
    services: List[ServiceResponse]
    total: int
    page: int
    per_page: int
