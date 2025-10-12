"""
Serviço de autenticação
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from app.models.user import User
from app.schemas.auth import Token, LoginResponse, RegisterResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_tokens,
    verify_token
)
from app.dependencies import get_redis
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class AuthService:
    """Serviço para operações de autenticação"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
    
    async def register_user(self, user_data: UserCreate) -> RegisterResponse:
        """Registrar novo usuário"""
        # Verificar se email já existe
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está em uso"
            )
        
        # Criar hash da senha
        hashed_password = get_password_hash(user_data.password)
        
        # Criar usuário
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            template_type=user_data.template_type,
            whatsapp_number=user_data.whatsapp_number,
            is_active_bool=True,
            is_verified_bool=False
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Novo usuário registrado: {db_user.email}")
        
        return RegisterResponse(
            user=UserResponse.from_orm(db_user),
            message="Usuário registrado com sucesso"
        )
    
    async def authenticate_user(self, login_data: UserLogin) -> LoginResponse:
        """Autenticar usuário e retornar tokens com proteção contra timing attacks"""
        # Buscar usuário por email
        user = self.db.query(User).filter(User.email == login_data.email).first()
        
        # Proteção contra timing attacks:
        # Sempre fazer hash da senha mesmo se usuário não existir
        # Isso mantém o tempo de resposta consistente
        if user:
            password_valid = verify_password(login_data.password, user.password_hash)
        else:
            # Fazer hash dummy para manter timing consistente
            # Usa um hash bcrypt válido aleatório para simular a verificação
            dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5jtRfxkR4dYhi"
            verify_password(login_data.password, dummy_hash)
            password_valid = False
        
        # Validar credenciais (após ambos os caminhos terem executado)
        if not user or not password_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        # Verificar se usuário está ativo
        if not user.is_active_bool:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo"
            )
        
        # Criar tokens
        tokens = create_tokens(str(user.id), user.email)
        
        # Armazenar refresh token no Redis (opcional, para logout)
        if self.redis:
            try:
                await self.redis.setex(
                    f"refresh_token:{user.id}",
                    timedelta(days=7).total_seconds(),
                    tokens["refresh_token"]
                )
            except Exception as e:
                logger.warning(f"Erro ao armazenar refresh token no Redis: {e}")
        
        logger.info(f"Usuário autenticado: {user.email}")
        
        return LoginResponse(
            user=UserResponse.from_orm(user),
            tokens=Token(**tokens),
            message="Login realizado com sucesso"
        )
    
    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Renovar token de acesso usando refresh token"""
        # Verificar refresh token
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )
        
        # Verificar se usuário ainda existe e está ativo
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active_bool:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo"
            )
        
        # Verificar se refresh token está no Redis (se disponível)
        if self.redis:
            try:
                stored_token = await self.redis.get(f"refresh_token:{user_id}")
                if stored_token != refresh_token:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token inválido"
                    )
            except Exception as e:
                logger.warning(f"Erro ao verificar refresh token no Redis: {e}")
        
        # Criar novos tokens
        tokens = create_tokens(str(user.id), user.email)
        
        # Atualizar refresh token no Redis
        if self.redis:
            try:
                await self.redis.setex(
                    f"refresh_token:{user_id}",
                    timedelta(days=7).total_seconds(),
                    tokens["refresh_token"]
                )
            except Exception as e:
                logger.warning(f"Erro ao atualizar refresh token no Redis: {e}")
        
        logger.info(f"Token renovado para usuário: {user.email}")
        
        return Token(**tokens)
    
    async def logout_user(self, user_id: str, access_token: Optional[str] = None) -> Dict[str, str]:
        """Fazer logout do usuário (invalidar tokens)"""
        # Remover refresh token do Redis e adicionar access token ao blacklist
        if self.redis:
            try:
                # Remover refresh token
                await self.redis.delete(f"refresh_token:{user_id}")
                
                # Adicionar access token ao blacklist (válido até expirar - 30 min)
                if access_token:
                    await self.redis.setex(
                        f"token_blacklist:{user_id}",
                        timedelta(minutes=30).total_seconds(),
                        access_token
                    )
                
                logger.info(f"Logout realizado para usuário: {user_id}")
            except Exception as e:
                logger.warning(f"Erro ao invalidar tokens no Redis: {e}")
        
        return {"message": "Logout realizado com sucesso"}
    
    async def get_current_user(self, token: str) -> User:
        """Obter usuário atual a partir do token com verificação de blacklist"""
        # Verificar token
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        # Verificar se token está na blacklist (foi feito logout)
        if self.redis:
            try:
                is_blacklisted = await self.redis.exists(f"token_blacklist:{user_id}")
                if is_blacklisted:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token foi revogado. Faça login novamente"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Erro ao verificar blacklist no Redis: {e}")
        
        # Buscar usuário
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )
        
        if not user.is_active_bool:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo"
            )
        
        return user
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> Dict[str, str]:
        """Alterar senha do usuário"""
        # Buscar usuário
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Verificar senha atual
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta"
            )
        
        # Atualizar senha
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Senha alterada para usuário: {user.email}")
        
        return {"message": "Senha alterada com sucesso"}

