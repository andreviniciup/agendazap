"""
Serviço para gerenciamento de categorias de serviços
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc
from fastapi import HTTPException, status
import logging
from uuid import UUID

from app.models.service import ServiceCategory, Service
from app.models.user import User
from app.schemas.service_category import ServiceCategoryCreate, ServiceCategoryUpdate

logger = logging.getLogger(__name__)


class ServiceCategoryService:
    """Serviço para operações relacionadas a categorias de serviços"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_category(self, category_data: ServiceCategoryCreate, user: User) -> ServiceCategory:
        """Criar nova categoria de serviço"""
        try:
            # Verificar se já existe categoria com o mesmo nome
            existing_category = self.db.query(ServiceCategory).filter(
                and_(
                    ServiceCategory.user_id == user.id,
                    ServiceCategory.name == category_data.name
                )
            ).first()
            
            if existing_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe uma categoria com este nome"
                )
            
            # Criar categoria
            category = ServiceCategory(
                user_id=user.id,
                name=category_data.name,
                description=category_data.description,
                color=category_data.color,
                icon=category_data.icon
            )
            
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            
            logger.info(f"Categoria criada: {category.name} para usuário {user.email}")
            return category
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar categoria: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_categories(
        self, 
        user: User, 
        include_inactive: bool = False,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """Obter categorias do usuário"""
        try:
            query = self.db.query(ServiceCategory).filter(ServiceCategory.user_id == user.id)
            
            if not include_inactive:
                query = query.filter(ServiceCategory.is_active == True)
            
            # Ordenar por nome
            query = query.order_by(ServiceCategory.name)
            
            # Contar total
            total = query.count()
            
            # Paginação
            offset = (page - 1) * per_page
            categories = query.offset(offset).limit(per_page).all()
            
            # Adicionar contagem de serviços para cada categoria
            for category in categories:
                services_count = self.db.query(Service).filter(
                    and_(
                        Service.category_id == category.id,
                        Service.is_active == True
                    )
                ).count()
                category.services_count = services_count
            
            # Calcular páginas
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "categories": categories,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter categorias: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_category(self, category_id: UUID, user: User) -> ServiceCategory:
        """Obter categoria específica"""
        try:
            category = self.db.query(ServiceCategory).filter(
                and_(
                    ServiceCategory.id == category_id,
                    ServiceCategory.user_id == user.id
                )
            ).first()
            
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoria não encontrada"
                )
            
            # Adicionar contagem de serviços
            services_count = self.db.query(Service).filter(
                and_(
                    Service.category_id == category.id,
                    Service.is_active == True
                )
            ).count()
            category.services_count = services_count
            
            return category
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter categoria: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def update_category(self, category_id: UUID, category_data: ServiceCategoryUpdate, user: User) -> ServiceCategory:
        """Atualizar categoria"""
        try:
            category = self.get_category(category_id, user)
            
            # Verificar se o novo nome já existe (se foi alterado)
            if category_data.name and category_data.name != category.name:
                existing_category = self.db.query(ServiceCategory).filter(
                    and_(
                        ServiceCategory.user_id == user.id,
                        ServiceCategory.name == category_data.name,
                        ServiceCategory.id != category_id
                    )
                ).first()
                
                if existing_category:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Já existe uma categoria com este nome"
                    )
            
            # Atualizar campos
            update_data = category_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(category, field, value)
            
            self.db.commit()
            self.db.refresh(category)
            
            logger.info(f"Categoria atualizada: {category.name} para usuário {user.email}")
            return category
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar categoria: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def delete_category(self, category_id: UUID, user: User) -> None:
        """Deletar categoria (soft delete)"""
        try:
            category = self.get_category(category_id, user)
            
            # Verificar se há serviços usando esta categoria
            services_count = self.db.query(Service).filter(
                and_(
                    Service.category_id == category_id,
                    Service.is_active == True
                )
            ).count()
            
            if services_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não é possível deletar categoria com {services_count} serviços ativos"
                )
            
            # Soft delete
            category.is_active = False
            self.db.commit()
            
            logger.info(f"Categoria deletada: {category.name} para usuário {user.email}")
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar categoria: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_category_stats(self, user: User) -> Dict[str, Any]:
        """Obter estatísticas das categorias do usuário"""
        try:
            stats = self.db.query(
                func.count(ServiceCategory.id).label('total_categories'),
                func.count(ServiceCategory.id).filter(ServiceCategory.is_active == True).label('active_categories'),
                func.count(ServiceCategory.id).filter(ServiceCategory.is_active == False).label('inactive_categories')
            ).filter(ServiceCategory.user_id == user.id).first()
            
            # Categoria mais usada
            most_used_category = self.db.query(
                ServiceCategory,
                func.count(Service.id).label('services_count')
            ).join(Service, ServiceCategory.id == Service.category_id, isouter=True)\
            .filter(ServiceCategory.user_id == user.id)\
            .group_by(ServiceCategory.id)\
            .order_by(desc('services_count'))\
            .first()
            
            # Categorias com serviços
            categories_with_services = self.db.query(ServiceCategory).join(
                Service, ServiceCategory.id == Service.category_id
            ).filter(
                and_(
                    ServiceCategory.user_id == user.id,
                    Service.is_active == True
                )
            ).distinct().count()
            
            return {
                "total_categories": stats.total_categories or 0,
                "active_categories": stats.active_categories or 0,
                "inactive_categories": stats.inactive_categories or 0,
                "categories_with_services": categories_with_services,
                "most_used_category": most_used_category[0] if most_used_category else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de categorias: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )




