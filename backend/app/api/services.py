"""
Endpoints de serviços
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.database import get_db
from app.dependencies import get_current_active_user, get_service_service, get_service_category_service
from app.schemas.service import (
    ServiceCreate, ServiceUpdate, ServiceResponse, ServiceList, ServiceStats,
    ServiceSearch, ServiceBulkUpdate, ServiceTemplateValidation
)
from app.schemas.service_category import (
    ServiceCategoryCreate, ServiceCategoryUpdate, ServiceCategoryResponse,
    ServiceCategoryList, ServiceCategoryStats
)
from app.models.user import User
from app.services.service_service import ServiceService
from app.services.service_category_service import ServiceCategoryService
from app.utils.enums import TemplateType

router = APIRouter()
logger = logging.getLogger(__name__)


# Endpoints de Serviços

@router.get("/", response_model=ServiceList)
async def get_services(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    query: str = Query(None, description="Termo de busca"),
    category_id: UUID = Query(None, description="Filtrar por categoria"),
    is_active: bool = Query(None, description="Filtrar por status ativo"),
    is_featured: bool = Query(None, description="Filtrar por serviços em destaque"),
    sort_by: str = Query("name", description="Campo para ordenação"),
    sort_order: str = Query("asc", description="Ordem da ordenação"),
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Obter serviços do usuário com filtros e paginação"""
    try:
        # Criar parâmetros de busca
        search_params = ServiceSearch(
            query=query,
            category_id=category_id,
            is_active=is_active,
            is_featured=is_featured,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        result = service_service.get_services(current_user, search_params, page, per_page)
        
        # Converter serviços para response
        services_response = []
        for service in result["services"]:
            service_dict = {
                "id": service.id,
                "user_id": service.user_id,
                "category_id": service.category_id,
                "name": service.name,
                "description": service.description,
                "duration": service.duration,
                "price": service.price,
                "images": service.images,
                "credentials": service.credentials,
                "promotions": service.promotions,
                "custom_fields": service.custom_fields,
                "is_active": service.is_active,
                "is_featured": service.is_featured,
                "sort_order": service.sort_order,
                "created_at": service.created_at,
                "updated_at": service.updated_at,
                "category": None
            }
            
            # Adicionar informações da categoria se existir
            if service.category:
                service_dict["category"] = {
                    "id": service.category.id,
                    "name": service.category.name,
                    "color": service.category.color,
                    "icon": service.category.icon
                }
            
            services_response.append(service_dict)
        
        return ServiceList(
            services=services_response,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"]
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter serviços: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/", response_model=ServiceResponse)
async def create_service(
    service_data: ServiceCreate,
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Criar novo serviço"""
    try:
        service = await service_service.create_service(service_data, current_user)
        
        # Converter para response
        service_response = {
            "id": service.id,
            "user_id": service.user_id,
            "category_id": service.category_id,
            "name": service.name,
            "description": service.description,
            "duration": service.duration,
            "price": service.price,
            "images": service.images,
            "credentials": service.credentials,
            "promotions": service.promotions,
            "custom_fields": service.custom_fields,
            "is_active": service.is_active,
            "is_featured": service.is_featured,
            "sort_order": service.sort_order,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "category": None
        }
        
        return service_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar serviço: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Obter serviço específico"""
    try:
        service = service_service.get_service(service_id, current_user)
        
        # Converter para response
        service_response = {
            "id": service.id,
            "user_id": service.user_id,
            "category_id": service.category_id,
            "name": service.name,
            "description": service.description,
            "duration": service.duration,
            "price": service.price,
            "images": service.images,
            "credentials": service.credentials,
            "promotions": service.promotions,
            "custom_fields": service.custom_fields,
            "is_active": service.is_active,
            "is_featured": service.is_featured,
            "sort_order": service.sort_order,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "category": None
        }
        
        # Adicionar informações da categoria se existir
        if service.category:
            service_response["category"] = {
                "id": service.category.id,
                "name": service.category.name,
                "color": service.category.color,
                "icon": service.category.icon
            }
        
        return service_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter serviço: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    service_data: ServiceUpdate,
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Atualizar serviço"""
    try:
        service = service_service.update_service(service_id, service_data, current_user)
        
        # Converter para response
        service_response = {
            "id": service.id,
            "user_id": service.user_id,
            "category_id": service.category_id,
            "name": service.name,
            "description": service.description,
            "duration": service.duration,
            "price": service.price,
            "images": service.images,
            "credentials": service.credentials,
            "promotions": service.promotions,
            "custom_fields": service.custom_fields,
            "is_active": service.is_active,
            "is_featured": service.is_featured,
            "sort_order": service.sort_order,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "category": None
        }
        
        return service_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar serviço: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/{service_id}")
async def delete_service(
    service_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Deletar serviço"""
    try:
        service_service.delete_service(service_id, current_user)
        return {"message": "Serviço deletado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar serviço: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/stats/overview", response_model=ServiceStats)
async def get_service_stats(
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Obter estatísticas dos serviços"""
    try:
        stats = service_service.get_service_stats(current_user)
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de serviços: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/template/validation", response_model=ServiceTemplateValidation)
async def get_template_validation(
    current_user: User = Depends(get_current_active_user),
    service_service: ServiceService = Depends(get_service_service)
):
    """Obter regras de validação baseadas no template do usuário"""
    try:
        rules = service_service.get_template_validation_rules(current_user.template_type)
        
        return ServiceTemplateValidation(
            template_type=current_user.template_type,
            requires_price=rules["requires_price"],
            requires_images=rules["requires_images"],
            requires_credentials=rules["requires_credentials"],
            max_images=rules["max_images"],
            custom_fields_schema=rules.get("custom_fields")
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter validação de template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


# Endpoints de Categorias de Serviços

@router.get("/categories/", response_model=ServiceCategoryList)
async def get_categories(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    include_inactive: bool = Query(False, description="Incluir categorias inativas"),
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Obter categorias de serviços do usuário"""
    try:
        result = category_service.get_categories(current_user, include_inactive, page, per_page)
        
        # Converter categorias para response
        categories_response = []
        for category in result["categories"]:
            category_dict = {
                "id": category.id,
                "user_id": category.user_id,
                "name": category.name,
                "description": category.description,
                "color": category.color,
                "icon": category.icon,
                "is_active": category.is_active,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "services_count": getattr(category, 'services_count', 0)
            }
            categories_response.append(category_dict)
        
        return ServiceCategoryList(
            categories=categories_response,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"]
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter categorias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/categories/", response_model=ServiceCategoryResponse)
async def create_category(
    category_data: ServiceCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Criar nova categoria de serviço"""
    try:
        category = category_service.create_category(category_data, current_user)
        
        return ServiceCategoryResponse(
            id=category.id,
            user_id=category.user_id,
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
            services_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/categories/{category_id}", response_model=ServiceCategoryResponse)
async def get_category(
    category_id: UUID,
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Obter categoria específica"""
    try:
        category = category_service.get_category(category_id, current_user)
        
        return ServiceCategoryResponse(
            id=category.id,
            user_id=category.user_id,
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
            services_count=getattr(category, 'services_count', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.put("/categories/{category_id}", response_model=ServiceCategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: ServiceCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Atualizar categoria"""
    try:
        category = category_service.update_category(category_id, category_data, current_user)
        
        return ServiceCategoryResponse(
            id=category.id,
            user_id=category.user_id,
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
            services_count=getattr(category, 'services_count', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Deletar categoria"""
    try:
        category_service.delete_category(category_id, current_user)
        return {"message": "Categoria deletada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar categoria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/categories/stats/overview", response_model=ServiceCategoryStats)
async def get_category_stats(
    current_user: User = Depends(get_current_active_user),
    category_service: ServiceCategoryService = Depends(get_service_category_service)
):
    """Obter estatísticas das categorias"""
    try:
        stats = category_service.get_category_stats(current_user)
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de categorias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )