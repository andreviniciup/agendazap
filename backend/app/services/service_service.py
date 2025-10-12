"""
Serviço para gerenciamento de serviços
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from fastapi import HTTPException, status
import logging
from uuid import UUID

from app.models.service import Service, ServiceCategory
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceSearch
from app.schemas.service_category import ServiceCategoryCreate, ServiceCategoryUpdate
from app.utils.enums import TemplateType
from app.services.plan_service import PlanService
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class ServiceService:
    """Serviço para operações relacionadas a serviços"""
    
    def __init__(self, db: Session, plan_service: PlanService):
        self.db = db
        self.plan_service = plan_service
    
    def get_template_validation_rules(self, template_type: TemplateType) -> Dict[str, Any]:
        """Obter regras de validação baseadas no template"""
        rules = {
            TemplateType.CONSULTATION: {
                "requires_price": False,
                "requires_images": False,
                "requires_credentials": True,
                "max_images": 0,
                "custom_fields": ["specialization", "approach", "languages"]
            },
            TemplateType.SERVICE_TABLE: {
                "requires_price": True,
                "requires_images": True,
                "requires_credentials": False,
                "max_images": 5,
                "custom_fields": ["materials", "equipment", "warranty"]
            }
        }
        
        return rules.get(template_type, rules[TemplateType.CONSULTATION])
    
    def validate_service_for_template(self, service_data: ServiceCreate, user: User) -> None:
        """Validar serviço baseado no template do usuário"""
        rules = self.get_template_validation_rules(user.template_type)
        
        # Validar preço
        if rules["requires_price"] and not service_data.price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preço é obrigatório para este tipo de template"
            )
        
        # Validar imagens
        if rules["requires_images"] and not service_data.images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pelo menos uma imagem é obrigatória para este tipo de template"
            )
        
        if service_data.images and len(service_data.images) > rules["max_images"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Máximo de {rules['max_images']} imagens permitidas para este template"
            )
        
        # Validar credenciais
        if rules["requires_credentials"] and not service_data.credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais são obrigatórias para este tipo de template"
            )
    
    async def check_service_limit(self, user: User) -> bool:
        """Verificar se o usuário pode criar mais serviços"""
        try:
            can_create = await self.plan_service.check_limit(user, "services_limit", 1)
            return can_create
        except Exception as e:
            logger.error(f"Erro ao verificar limite de serviços: {e}")
            return True  # Em caso de erro, permitir criação
    
    async def create_service(self, service_data: ServiceCreate, user: User) -> Service:
        """Criar novo serviço"""
        try:
            # Verificar limite de serviços
            can_create = await self.check_service_limit(user)
            if not can_create:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Limite de serviços do plano atingido"
                )
            
            # Validar baseado no template
            self.validate_service_for_template(service_data, user)
            
            # Verificar se a categoria pertence ao usuário
            if service_data.category_id:
                category = self.db.query(ServiceCategory).filter(
                    and_(
                        ServiceCategory.id == service_data.category_id,
                        ServiceCategory.user_id == user.id
                    )
                ).first()
                
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Categoria não encontrada ou não pertence ao usuário"
                    )
            
            # Criar serviço
            service = Service(
                user_id=user.id,
                category_id=service_data.category_id,
                name=service_data.name,
                description=service_data.description,
                duration=service_data.duration,
                price=service_data.price,
                images=service_data.images,
                credentials=service_data.credentials,
                promotions=service_data.promotions,
                custom_fields=service_data.custom_fields
            )
            
            self.db.add(service)
            self.db.commit()
            self.db.refresh(service)
            
            # Incrementar contador de uso
            await self.plan_service.increment_usage(str(user.id), "services", 1)
            
            # Invalidar cache de serviços do usuário
            cache_service.invalidate_user_services(user.id)
            
            logger.info(f"Serviço criado: {service.name} para usuário {user.email}")
            return service
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar serviço: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_services(
        self, 
        user: User, 
        search_params: Optional[ServiceSearch] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """Obter serviços do usuário com filtros e paginação"""
        try:
            query = self.db.query(Service).filter(Service.user_id == user.id)
            
            # Aplicar filtros se fornecidos
            if search_params:
                if search_params.query:
                    query = query.filter(
                        or_(
                            Service.name.ilike(f"%{search_params.query}%"),
                            Service.description.ilike(f"%{search_params.query}%")
                        )
                    )
                
                if search_params.category_id:
                    query = query.filter(Service.category_id == search_params.category_id)
                
                if search_params.min_price is not None:
                    query = query.filter(Service.price >= search_params.min_price)
                
                if search_params.max_price is not None:
                    query = query.filter(Service.price <= search_params.max_price)
                
                if search_params.min_duration is not None:
                    query = query.filter(Service.duration >= search_params.min_duration)
                
                if search_params.max_duration is not None:
                    query = query.filter(Service.duration <= search_params.max_duration)
                
                if search_params.is_active is not None:
                    query = query.filter(Service.is_active == search_params.is_active)
                
                if search_params.is_featured is not None:
                    query = query.filter(Service.is_featured == search_params.is_featured)
                
                # Ordenação
                sort_field = getattr(Service, search_params.sort_by, Service.name)
                if search_params.sort_order == "desc":
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(Service.sort_order, Service.name)
            
            # Contar total
            total = query.count()
            
            # Paginação
            offset = (page - 1) * per_page
            services = query.offset(offset).limit(per_page).all()
            
            # Calcular páginas
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "services": services,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter serviços: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_user_services(
        self, 
        user: User, 
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Obter todos os serviços ativos do usuário com cache e fallback"""
        try:
            # Função para buscar do banco (fallback)
            def fetch_from_database():
                services = self.db.query(Service).filter(
                    and_(
                        Service.user_id == user.id,
                        Service.is_active == True
                    )
                ).order_by(Service.sort_order, Service.name).all()
                
                # Serializar serviços para cache
                services_data = []
                for service in services:
                    service_data = {
                        "id": str(service.id),
                        "name": service.name,
                        "description": service.description,
                        "duration": service.duration,
                        "price": float(service.price) if service.price else None,
                        "images": service.images or [],
                        "credentials": service.credentials or [],
                        "promotions": service.promotions or [],
                        "custom_fields": service.custom_fields or {},
                        "is_featured": service.is_featured,
                        "category_id": str(service.category_id) if service.category_id else None,
                        "category_name": service.category.name if service.category else None,
                        "created_at": service.created_at.isoformat(),
                        "updated_at": service.updated_at.isoformat()
                    }
                    services_data.append(service_data)
                
                return services_data
            
            # Tentar obter do cache primeiro
            if use_cache:
                cached_services = cache_service.get_user_services(user.id)
                if cached_services:
                    logger.debug(f"Serviços obtidos do cache para usuário {user.id}")
                    return cached_services
            
            # Se não está no cache, buscar do banco
            services_data = fetch_from_database()
            
            # Salvar no cache se disponível
            if use_cache and cache_service.is_cache_healthy():
                cache_service.set_user_services(user.id, services_data)
                logger.debug(f"Serviços salvos no cache para usuário {user.id}")
            
            return services_data
            
        except Exception as e:
            logger.error(f"Erro ao obter serviços do usuário: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_user_services_by_category(
        self, 
        user: User, 
        category_id: Optional[UUID] = None,
        use_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Obter serviços do usuário agrupados por categoria com cache"""
        try:
            all_services = self.get_user_services(user, use_cache)
            
            # Agrupar por categoria
            services_by_category = {}
            for service in all_services:
                category_key = service.get("category_name") or "Sem categoria"
                if category_key not in services_by_category:
                    services_by_category[category_key] = []
                services_by_category[category_key].append(service)
            
            return services_by_category
            
        except Exception as e:
            logger.error(f"Erro ao obter serviços por categoria: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_service(self, service_id: UUID, user: User) -> Service:
        """Obter serviço específico"""
        try:
            service = self.db.query(Service).filter(
                and_(
                    Service.id == service_id,
                    Service.user_id == user.id
                )
            ).first()
            
            if not service:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Serviço não encontrado"
                )
            
            return service
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter serviço: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def update_service(self, service_id: UUID, service_data: ServiceUpdate, user: User) -> Service:
        """Atualizar serviço"""
        try:
            service = self.get_service(service_id, user)
            
            # Verificar se a categoria pertence ao usuário
            if service_data.category_id:
                category = self.db.query(ServiceCategory).filter(
                    and_(
                        ServiceCategory.id == service_data.category_id,
                        ServiceCategory.user_id == user.id
                    )
                ).first()
                
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Categoria não encontrada ou não pertence ao usuário"
                    )
            
            # Atualizar campos
            update_data = service_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(service, field, value)
            
            self.db.commit()
            self.db.refresh(service)
            
            # Invalidar cache de serviços do usuário
            cache_service.invalidate_user_services(user.id)
            
            logger.info(f"Serviço atualizado: {service.name} para usuário {user.email}")
            return service
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar serviço: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def delete_service(self, service_id: UUID, user: User) -> None:
        """Deletar serviço (soft delete)"""
        try:
            service = self.get_service(service_id, user)
            
            # Soft delete
            service.is_active = False
            self.db.commit()
            
            # Invalidar cache de serviços do usuário
            cache_service.invalidate_user_services(user.id)
            
            logger.info(f"Serviço deletado: {service.name} para usuário {user.email}")
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar serviço: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_service_stats(self, user: User) -> Dict[str, Any]:
        """Obter estatísticas dos serviços do usuário"""
        try:
            stats = self.db.query(
                func.count(Service.id).label('total_services'),
                func.count(Service.id).filter(Service.is_active == True).label('active_services'),
                func.count(Service.id).filter(Service.is_active == False).label('inactive_services'),
                func.count(Service.id).filter(Service.is_featured == True).label('featured_services'),
                func.count(Service.id).filter(Service.images.isnot(None)).label('services_with_images'),
                func.count(Service.id).filter(Service.promotions.isnot(None)).label('services_with_promotions'),
                func.avg(Service.duration).label('average_duration'),
                func.avg(Service.price).label('average_price')
            ).filter(Service.user_id == user.id).first()
            
            return {
                "total_services": stats.total_services or 0,
                "active_services": stats.active_services or 0,
                "inactive_services": stats.inactive_services or 0,
                "featured_services": stats.featured_services or 0,
                "services_with_images": stats.services_with_images or 0,
                "services_with_promotions": stats.services_with_promotions or 0,
                "average_duration": float(stats.average_duration or 0),
                "average_price": float(stats.average_price or 0) if stats.average_price else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de serviços: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )

