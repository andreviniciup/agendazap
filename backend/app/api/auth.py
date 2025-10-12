"""
Endpoints de autenticação
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.dependencies import get_redis, get_current_active_user
from app.schemas.user import UserCreate, UserLogin
from app.schemas.auth import (
    RefreshTokenRequest,
    LoginResponse,
    RegisterResponse,
    LogoutResponse,
    Token
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService
from app.models.user import User

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Registrar novo usuário"""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.register_user(user_data)
        
        logger.info(f"Novo usuário registrado: {user_data.email}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Login do usuário"""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.authenticate_user(login_data)
        
        logger.info(f"Login realizado: {login_data.email}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Renovar token de acesso"""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.refresh_access_token(refresh_data.refresh_token)
        
        logger.info("Token renovado com sucesso")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na renovação do token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Logout do usuário"""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.logout_user(str(current_user.id))
        
        logger.info(f"Logout realizado: {current_user.email}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Obter informações do usuário atual"""
    return UserResponse.from_orm(current_user)


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Verificar email do usuário através do token"""
    try:
        verification_service = EmailVerificationService(db, redis_client)
        result = await verification_service.verify_email_token(token)
        
        logger.info(f"Email verificado para usuário: {result.get('user_id')}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na verificação de email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/resend-verification")
async def resend_verification(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Reenviar email de verificação"""
    try:
        verification_service = EmailVerificationService(db, redis_client)
        token = await verification_service.resend_verification_email(str(current_user.id))
        
        logger.info(f"Email de verificação reenviado para: {current_user.email}")
        
        # Em produção, aqui você enviaria um email real com o link de verificação
        # Por enquanto, retornar o token (apenas para desenvolvimento)
        return {
            "message": "Email de verificação enviado",
            "token": token  # REMOVER EM PRODUÇÃO - token deve ser enviado por email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao reenviar verificação: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/verification-status")
async def get_verification_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Verificar status de verificação do email"""
    try:
        verification_service = EmailVerificationService(db, redis_client)
        status_info = verification_service.get_verification_status(current_user)
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status de verificação: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
