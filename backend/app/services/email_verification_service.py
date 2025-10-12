"""
Serviço para verificação de email
"""

from datetime import timedelta
from typing import Optional, Dict
import secrets
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Serviço para gerenciar verificação de email"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
    
    async def generate_verification_token(self, user_id: str) -> str:
        """Gerar token de verificação de email"""
        # Gerar token seguro
        token = secrets.token_urlsafe(32)
        
        # Armazenar no Redis com expiração de 24 horas
        if self.redis:
            try:
                await self.redis.setex(
                    f"email_verification:{token}",
                    timedelta(hours=24).total_seconds(),
                    user_id
                )
                logger.info(f"Token de verificação gerado para usuário: {user_id}")
                return token
            except Exception as e:
                logger.error(f"Erro ao armazenar token de verificação no Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erro ao gerar token de verificação"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de verificação de email indisponível"
            )
    
    async def verify_email_token(self, token: str) -> Dict[str, str]:
        """Verificar token e ativar email do usuário"""
        if not self.redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de verificação de email indisponível"
            )
        
        try:
            # Buscar user_id pelo token
            user_id = await self.redis.get(f"email_verification:{token}")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token inválido ou expirado"
                )
            
            # Decodificar se necessário
            if isinstance(user_id, bytes):
                user_id = user_id.decode('utf-8')
            
            # Buscar usuário no banco
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )
            
            # Verificar se já está verificado
            if user.is_verified_bool:
                return {
                    "message": "Email já estava verificado",
                    "user_id": str(user.id)
                }
            
            # Atualizar usuário
            user.is_verified_bool = True
            self.db.commit()
            
            # Deletar token do Redis
            await self.redis.delete(f"email_verification:{token}")
            
            logger.info(f"Email verificado para usuário: {user.email}")
            
            return {
                "message": "Email verificado com sucesso",
                "user_id": str(user.id)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao verificar email: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao verificar email"
            )
    
    async def resend_verification_email(self, user_id: str) -> str:
        """Reenviar email de verificação"""
        # Buscar usuário
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Verificar se já está verificado
        if user.is_verified_bool:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está verificado"
            )
        
        # Gerar novo token
        token = await self.generate_verification_token(str(user.id))
        
        logger.info(f"Token de verificação reenviado para usuário: {user.email}")
        
        return token
    
    async def check_verification_required(self, user: User) -> bool:
        """Verificar se verificação de email é obrigatória"""
        # Em produção, exigir verificação
        # Em desenvolvimento, pode ser opcional
        from app.config import settings
        
        if settings.ENVIRONMENT == "production":
            if not user.is_verified_bool:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email não verificado. Por favor, verifique seu email antes de continuar."
                )
        
        return user.is_verified_bool
    
    def get_verification_status(self, user: User) -> Dict[str, bool]:
        """Obter status de verificação do usuário"""
        return {
            "is_verified": user.is_verified_bool,
            "email": user.email,
            "requires_verification": user.is_verified_bool is False
        }

