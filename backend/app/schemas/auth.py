"""
Schemas Pydantic para autenticação
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID

from app.schemas.user import UserResponse


class Token(BaseModel):
    """Schema para token de acesso"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class TokenData(BaseModel):
    """Schema para dados do token"""
    user_id: Optional[UUID] = None
    email: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Schema para requisição de refresh token"""
    refresh_token: str


class LoginResponse(BaseModel):
    """Schema para resposta de login"""
    user: UserResponse
    tokens: Token
    message: str = "Login realizado com sucesso"


class RegisterResponse(BaseModel):
    """Schema para resposta de registro"""
    user: UserResponse
    message: str = "Usuário registrado com sucesso"


class LogoutResponse(BaseModel):
    """Schema para resposta de logout"""
    message: str = "Logout realizado com sucesso"


class PasswordChange(BaseModel):
    """Schema para mudança de senha"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    def validate_new_password(self):
        """Validar força da nova senha"""
        if len(self.new_password) < 8:
            raise ValueError('Nova senha deve ter pelo menos 8 caracteres')
        if not any(c.isupper() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos um número')
        return True


class PasswordResetRequest(BaseModel):
    """Schema para solicitação de reset de senha"""
    email: str


class PasswordReset(BaseModel):
    """Schema para reset de senha"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    def validate_new_password(self):
        """Validar força da nova senha"""
        if len(self.new_password) < 8:
            raise ValueError('Nova senha deve ter pelo menos 8 caracteres')
        if not any(c.isupper() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError('Nova senha deve conter pelo menos um número')
        return True
