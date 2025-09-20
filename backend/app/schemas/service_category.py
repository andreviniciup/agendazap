"""
Schemas Pydantic para categorias de serviços
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class ServiceCategoryBase(BaseModel):
    """Schema base para categoria de serviço"""
    name: str = Field(..., min_length=1, max_length=100, description="Nome da categoria")
    description: Optional[str] = Field(None, max_length=500, description="Descrição da categoria")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Cor da categoria em hexadecimal")
    icon: Optional[str] = Field(None, max_length=50, description="Nome do ícone")


class ServiceCategoryCreate(ServiceCategoryBase):
    """Schema para criação de categoria de serviço"""
    pass


class ServiceCategoryUpdate(BaseModel):
    """Schema para atualização de categoria de serviço"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class ServiceCategoryResponse(ServiceCategoryBase):
    """Schema para resposta de categoria de serviço"""
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    services_count: Optional[int] = Field(None, description="Número de serviços nesta categoria")
    
    class Config:
        from_attributes = True


class ServiceCategoryList(BaseModel):
    """Schema para lista de categorias de serviços"""
    categories: List[ServiceCategoryResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ServiceCategoryStats(BaseModel):
    """Schema para estatísticas de categorias"""
    total_categories: int
    active_categories: int
    inactive_categories: int
    categories_with_services: int
    most_used_category: Optional[ServiceCategoryResponse] = None
