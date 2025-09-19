"""
Dependências globais da aplicação
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import redis.asyncio as redis
import logging

from app.database import get_db
from app.config import settings, get_redis_url

logger = logging.getLogger(__name__)

# Configurar Redis
redis_client: Optional[redis.Redis] = None

# Security scheme
security = HTTPBearer()


async def get_redis() -> redis.Redis:
    """Dependency para obter cliente Redis"""
    global redis_client
    
    if redis_client is None:
        try:
            redis_client = redis.from_url(
                get_redis_url(),
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Testar conexão
            await redis_client.ping()
            logger.info("✅ Conexão com Redis estabelecida")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis não disponível: {e}")
            logger.info("💡 Para desenvolvimento, o servidor continuará sem cache")
            logger.info("💡 Para usar o Redis: docker-compose up -d redis")
            # Retornar um mock do Redis para desenvolvimento
            return None
    
    return redis_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Dependency para obter usuário atual autenticado"""
    from app.services.auth_service import AuthService
    
    try:
        # Extrair token do header Authorization
        token = credentials.credentials
        
        # Criar serviço de autenticação
        auth_service = AuthService(db, redis_client)
        
        # Obter usuário atual
        user = await auth_service.get_current_user(token)
        
        return user
        
    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


async def get_current_active_user(current_user = Depends(get_current_user)):
    """Dependency para obter usuário ativo"""
    if not current_user.is_active_bool:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    return current_user


def get_plan_limits(plan_type: str) -> dict:
    """Retorna limites baseados no plano do usuário"""
    limits = {
        "free": {
            "appointments_per_month": settings.FREE_APPOINTMENTS_LIMIT,
            "whatsapp_messages_per_month": 0,
            "services_limit": 1,
            "custom_domain": False,
            "analytics": False
        },
        "starter": {
            "appointments_per_month": -1,  # Ilimitado
            "whatsapp_messages_per_month": settings.STARTER_MESSAGES_LIMIT,
            "services_limit": 5,
            "custom_domain": False,
            "analytics": False
        },
        "pro": {
            "appointments_per_month": -1,  # Ilimitado
            "whatsapp_messages_per_month": settings.PRO_MESSAGES_LIMIT,
            "services_limit": 15,
            "custom_domain": True,
            "analytics": True
        },
        "enterprise": {
            "appointments_per_month": -1,  # Ilimitado
            "whatsapp_messages_per_month": settings.ENTERPRISE_MESSAGES_LIMIT,
            "services_limit": 30,
            "custom_domain": True,
            "analytics": True
        }
    }
    
    return limits.get(plan_type, limits["free"])


async def get_plan_service(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Dependency para obter serviço de planos"""
    from app.services.plan_service import PlanService
    return PlanService(db, redis_client)


async def check_plan_limit(
    user_plan: str,
    limit_type: str,
    current_usage: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verifica se o usuário pode realizar uma ação baseada no plano"""
    limits = get_plan_limits(user_plan)
    
    if limit_type not in limits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de limite inválido: {limit_type}"
        )
    
    limit_value = limits[limit_type]
    
    # -1 significa ilimitado
    if limit_value == -1:
        return True
    
    if current_usage >= limit_value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite do plano atingido para {limit_type}. Limite: {limit_value}"
        )
    
    return True


async def rate_limit_check(
    identifier: str,
    limit: int = settings.RATE_LIMIT_REQUESTS,
    window: int = settings.RATE_LIMIT_WINDOW,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verifica rate limiting"""
    try:
        key = f"rate_limit:{identifier}"
        current = await redis_client.incr(key)
        
        if current == 1:
            await redis_client.expire(key, window)
        
        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições. Tente novamente mais tarde."
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        # Em caso de erro no Redis, permite a requisição
        return True


# Dependency para verificar se o serviço está saudável
async def health_check_dependency():
    """Verifica se todos os serviços estão funcionando"""
    from app.database import check_db_connection
    
    # Verificar banco de dados
    if not check_db_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível"
        )
    
    # Verificar Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache indisponível"
        )
    
    return True
