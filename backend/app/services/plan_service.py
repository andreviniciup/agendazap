"""
Serviço para gerenciamento de planos e limites
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging
import redis.asyncio as redis

from app.models.user import User
from app.utils.enums import PlanType
from app.config import settings

logger = logging.getLogger(__name__)


class PlanService:
    """Serviço para operações relacionadas a planos e limites"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
    
    def get_plan_limits(self, plan_type: PlanType) -> Dict[str, Any]:
        """Retorna os limites de um plano específico"""
        limits = {
            PlanType.FREE: {
                "appointments_per_month": settings.FREE_APPOINTMENTS_LIMIT,
                "whatsapp_messages_per_month": 0,
                "services_limit": 1,
                "custom_domain": False,
                "analytics": False,
                "price": 0.0
            },
            PlanType.STARTER: {
                "appointments_per_month": -1,  # Ilimitado
                "whatsapp_messages_per_month": settings.STARTER_MESSAGES_LIMIT,
                "services_limit": 5,
                "custom_domain": False,
                "analytics": False,
                "price": 49.90
            },
            PlanType.PRO: {
                "appointments_per_month": -1,  # Ilimitado
                "whatsapp_messages_per_month": settings.PRO_MESSAGES_LIMIT,
                "services_limit": 15,
                "custom_domain": True,
                "analytics": True,
                "price": 99.0
            },
            PlanType.ENTERPRISE: {
                "appointments_per_month": -1,  # Ilimitado
                "whatsapp_messages_per_month": settings.ENTERPRISE_MESSAGES_LIMIT,
                "services_limit": 30,
                "custom_domain": True,
                "analytics": True,
                "price": 197.0
            }
        }
        
        return limits.get(plan_type, limits[PlanType.FREE])
    
    async def get_user_usage(self, user_id: str, month: Optional[str] = None) -> Dict[str, int]:
        """Obter uso atual do usuário para o mês"""
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        usage = {
            "appointments_this_month": 0,
            "whatsapp_messages_this_month": 0,
            "services_count": 0
        }
        
        # Buscar uso no Redis se disponível
        if self.redis:
            try:
                # Contador de agendamentos
                appointments_key = f"usage:{user_id}:appointments:{month}"
                appointments_count = await self.redis.get(appointments_key)
                if appointments_count:
                    usage["appointments_this_month"] = int(appointments_count)
                
                # Contador de mensagens WhatsApp
                messages_key = f"usage:{user_id}:messages:{month}"
                messages_count = await self.redis.get(messages_key)
                if messages_count:
                    usage["whatsapp_messages_this_month"] = int(messages_count)
                
                # Contador de serviços
                services_key = f"usage:{user_id}:services"
                services_count = await self.redis.get(services_key)
                if services_count:
                    usage["services_count"] = int(services_count)
                    
            except Exception as e:
                logger.warning(f"Erro ao buscar uso no Redis: {e}")
        
        # Se Redis não disponível, buscar no banco de dados
        if not self.redis or usage["appointments_this_month"] == 0:
            # TODO: Implementar busca no banco de dados
            # Por enquanto, retornar valores mockados
            pass
        
        return usage
    
    async def check_limit(self, user: User, limit_type: str, increment: int = 1) -> bool:
        """Verificar se o usuário pode realizar uma ação baseada no plano"""
        limits = self.get_plan_limits(user.plan_type)
        usage = await self.get_user_usage(str(user.id))
        
        if limit_type not in limits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de limite inválido: {limit_type}"
            )
        
        limit_value = limits[limit_type]
        
        # -1 significa ilimitado
        if limit_value == -1:
            return True
        
        current_usage = usage.get(limit_type.replace("_limit", "_count"), 0)
        
        if current_usage + increment > limit_value:
            return False
        
        return True
    
    async def increment_usage(self, user_id: str, usage_type: str, increment: int = 1) -> None:
        """Incrementar contador de uso do usuário"""
        if not self.redis:
            logger.warning("Redis não disponível, não é possível incrementar uso")
            return
        
        try:
            month = datetime.now().strftime("%Y-%m")
            
            if usage_type == "appointments":
                key = f"usage:{user_id}:appointments:{month}"
            elif usage_type == "messages":
                key = f"usage:{user_id}:messages:{month}"
            elif usage_type == "services":
                key = f"usage:{user_id}:services"
            else:
                logger.error(f"Tipo de uso inválido: {usage_type}")
                return
            
            # Incrementar contador
            await self.redis.incrby(key, increment)
            
            # Definir TTL para contadores mensais
            if usage_type in ["appointments", "messages"]:
                # TTL até o final do mês
                end_of_month = datetime.now().replace(day=1, month=datetime.now().month + 1) - timedelta(seconds=1)
                ttl = int((end_of_month - datetime.now()).total_seconds())
                await self.redis.expire(key, ttl)
            
            logger.info(f"Uso incrementado: {user_id} - {usage_type} +{increment}")
            
        except Exception as e:
            logger.error(f"Erro ao incrementar uso: {e}")
    
    async def get_usage_percentage(self, user: User, limit_type: str) -> float:
        """Obter porcentagem de uso de um limite específico"""
        limits = self.get_plan_limits(user.plan_type)
        usage = await self.get_user_usage(str(user.id))
        
        if limit_type not in limits:
            return 0.0
        
        limit_value = limits[limit_type]
        
        # -1 significa ilimitado
        if limit_value == -1:
            return 0.0
        
        # Evitar divisão por zero
        if limit_value == 0:
            return 0.0
        
        current_usage = usage.get(limit_type.replace("_limit", "_count"), 0)
        
        return (current_usage / limit_value) * 100
    
    async def check_alert_threshold(self, user: User, limit_type: str, threshold: float = 80.0) -> bool:
        """Verificar se o usuário está próximo do limite (para alertas)"""
        usage_percentage = await self.get_usage_percentage(user, limit_type)
        return usage_percentage >= threshold
    
    async def get_plan_info(self, user: User) -> Dict[str, Any]:
        """Obter informações completas do plano do usuário"""
        limits = self.get_plan_limits(user.plan_type)
        usage = await self.get_user_usage(str(user.id))
        
        # Calcular porcentagens de uso
        usage_percentages = {}
        for limit_type in limits:
            if limit_type.endswith("_limit"):
                usage_percentages[limit_type] = await self.get_usage_percentage(user, limit_type)
        
        return {
            "plan_type": user.plan_type.value,
            "limits": limits,
            "usage": usage,
            "usage_percentages": usage_percentages,
            "alerts": {
                "appointments": await self.check_alert_threshold(user, "appointments_per_month"),
                "messages": await self.check_alert_threshold(user, "whatsapp_messages_per_month"),
                "services": await self.check_alert_threshold(user, "services_limit")
            }
        }
    
    async def reset_monthly_counters(self) -> None:
        """Resetar contadores mensais (executar no início de cada mês)"""
        if not self.redis:
            logger.warning("Redis não disponível, não é possível resetar contadores")
            return
        
        try:
            # Buscar todas as chaves de uso mensal
            pattern = "usage:*:appointments:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                await self.redis.delete(key)
            
            pattern = "usage:*:messages:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                await self.redis.delete(key)
            
            logger.info("Contadores mensais resetados com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao resetar contadores mensais: {e}")
    
    def can_upgrade_plan(self, current_plan: PlanType, target_plan: PlanType) -> bool:
        """Verificar se é possível fazer upgrade para o plano alvo"""
        plan_hierarchy = {
            PlanType.FREE: 0,
            PlanType.STARTER: 1,
            PlanType.PRO: 2,
            PlanType.ENTERPRISE: 3
        }
        
        current_level = plan_hierarchy.get(current_plan, 0)
        target_level = plan_hierarchy.get(target_plan, 0)
        
        return target_level > current_level
