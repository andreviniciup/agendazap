"""
Modelo de serviço
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class Service(Base):
    """Modelo de serviço oferecido pelo usuário"""
    
    __tablename__ = "services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=False)  # duração em minutos
    price = Column(Numeric(10, 2), nullable=True)  # preço opcional para consulta
    images = Column(ARRAY(String), nullable=True)  # URLs das imagens, até 5 para tabela
    credentials = Column(String(255), nullable=True)  # credenciais opcionais para consulta
    promotions = Column(Text, nullable=True)  # promoções opcionais para tabela
    is_active = Column(String(1), default='Y', nullable=False)  # Y/N
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="services")
    appointments = relationship("Appointment", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name}, user_id={self.user_id})>"
    
    @property
    def is_active_bool(self) -> bool:
        """Retorna se o serviço está ativo como boolean"""
        return self.is_active == 'Y'
    
    @is_active_bool.setter
    def is_active_bool(self, value: bool):
        """Define se o serviço está ativo"""
        self.is_active = 'Y' if value else 'N'
