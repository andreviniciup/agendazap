"""
Modelo de serviço
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ServiceCategory(Base):
    """Modelo de categoria de serviços"""
    
    __tablename__ = "service_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # código hexadecimal da cor
    icon = Column(String(50), nullable=True)  # nome do ícone
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="service_categories")
    services = relationship("Service", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ServiceCategory(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Service(Base):
    """Modelo de serviço oferecido pelo usuário"""
    
    __tablename__ = "services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=False)  # duração em minutos
    price = Column(Numeric(10, 2), nullable=True)  # preço opcional para consulta
    images = Column(ARRAY(String), nullable=True)  # URLs das imagens, até 5 para tabela
    credentials = Column(String(255), nullable=True)  # credenciais opcionais para consulta
    promotions = Column(Text, nullable=True)  # promoções opcionais para tabela
    custom_fields = Column(JSONB, nullable=True)  # campos customizados baseados no template
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)  # serviço em destaque
    sort_order = Column(Integer, default=0, nullable=False)  # ordem de exibição
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="services")
    category = relationship("ServiceCategory", back_populates="services")
    appointments = relationship("Appointment", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name}, user_id={self.user_id})>"
    
    @property
    def is_active_bool(self) -> bool:
        """Retorna se o serviço está ativo como boolean"""
        return self.is_active
    
    @is_active_bool.setter
    def is_active_bool(self, value: bool):
        """Define se o serviço está ativo"""
        self.is_active = value
