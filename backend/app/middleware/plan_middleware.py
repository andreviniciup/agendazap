"""
Middleware para verificação de limites de planos
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Callable

from app.dependencies import get_current_user
from app.services.plan_service import PlanService
from app.database import get_db
from app.dependencies import get_redis

logger = logging.getLogger(__name__)


class PlanLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para verificar limites de planos em tempo real"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Interceptar requisições e verificar limites"""
        
        # Lista de endpoints que precisam verificação de limites
        protected_endpoints = [
            "/api/services",
            "/api/appointments",
            "/api/webhooks/message"
        ]
        
        # Verificar se o endpoint precisa de verificação
        needs_check = any(request.url.path.startswith(endpoint) for endpoint in protected_endpoints)
        
        if not needs_check:
            return await call_next(request)
        
        # Verificar se é uma requisição que incrementa uso
        increment_endpoints = {
            "POST /api/services": "services",
            "POST /api/appointments": "appointments",
            "POST /api/webhooks/message": "messages"
        }
        
        endpoint_key = f"{request.method} {request.url.path}"
        usage_type = increment_endpoints.get(endpoint_key)
        
        try:
            # Obter usuário atual (se autenticado)
            # Nota: Em um middleware, não temos acesso direto às dependências
            # Por isso, vamos fazer a verificação nos endpoints específicos
            # Este middleware serve mais como um ponto de extensão futuro
            
            response = await call_next(request)
            
            # Se a resposta foi bem-sucedida e há um tipo de uso, incrementar
            if response.status_code in [200, 201] and usage_type:
                # TODO: Implementar incremento de uso aqui
                # Por enquanto, apenas log
                logger.info(f"Uso detectado: {usage_type} - {request.url.path}")
            
            return response
            
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Limite do plano atingido",
                        "message": "Você atingiu o limite do seu plano atual. Faça upgrade para continuar usando.",
                        "upgrade_url": "/api/users/upgrade"
                    }
                )
            raise e
        except Exception as e:
            logger.error(f"Erro no middleware de planos: {e}")
            return await call_next(request)


async def check_plan_limit(
    user,
    limit_type: str,
    increment: int = 1,
    db=None,
    redis_client=None
) -> bool:
    """Função auxiliar para verificar limites de plano"""
    try:
        plan_service = PlanService(db, redis_client)
        can_proceed = await plan_service.check_limit(user, limit_type, increment)
        
        if not can_proceed:
            limits = plan_service.get_plan_limits(user.plan_type)
            limit_value = limits.get(limit_type, 0)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Limite do plano atingido",
                    "message": f"Você atingiu o limite de {limit_type} do seu plano atual ({limit_value}).",
                    "current_plan": user.plan_type.value,
                    "limit_type": limit_type,
                    "limit_value": limit_value,
                    "upgrade_url": "/api/users/upgrade"
                }
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar limite do plano: {e}")
        # Em caso de erro, permitir a operação
        return True


async def increment_usage_after_success(
    user,
    usage_type: str,
    increment: int = 1,
    db=None,
    redis_client=None
) -> None:
    """Função auxiliar para incrementar uso após operação bem-sucedida"""
    try:
        plan_service = PlanService(db, redis_client)
        await plan_service.increment_usage(str(user.id), usage_type, increment)
        
    except Exception as e:
        logger.error(f"Erro ao incrementar uso: {e}")
        # Não falhar a operação principal por erro no contador
