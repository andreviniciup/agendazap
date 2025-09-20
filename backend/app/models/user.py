"""
Modelo de usuário (provedor de serviços)
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.enums import TemplateType, PlanType


class User(Base):
    """Modelo de usuário (provedor de serviços)"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    template_type = Column(Enum(TemplateType), nullable=False)
    whatsapp_number = Column(String(20), nullable=True)
    plan_type = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    is_active = Column(String(1), default='Y', nullable=False)  # Y/N para compatibilidade
    is_verified = Column(String(1), default='N', nullable=False)  # Y/N para compatibilidade
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    services = relationship("Service", back_populates="user", cascade="all, delete-orphan")
    service_categories = relationship("ServiceCategory", back_populates="user", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, template_type={self.template_type})>"
    
    @property
    def is_active_bool(self) -> bool:
        """Retorna se o usuário está ativo como boolean"""
        return self.is_active == 'Y'
    
    @is_active_bool.setter
    def is_active_bool(self, value: bool):
        """Define se o usuário está ativo"""
        self.is_active = 'Y' if value else 'N'
    
    @property
    def is_verified_bool(self) -> bool:
        """Retorna se o usuário está verificado como boolean"""
        return self.is_verified == 'Y'
    
    @is_verified_bool.setter
    def is_verified_bool(self, value: bool):
        """Define se o usuário está verificado"""
        self.is_verified = 'Y' if value else 'N'
