"""
Modelo de cliente
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    """Modelo de cliente"""
    
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    whatsapp = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    appointment_history = Column(ARRAY(UUID), nullable=True)  # IDs dos agendamentos
    frequency = Column(Integer, default=0, nullable=False)  # frequência de agendamentos
    preferred_services = Column(ARRAY(UUID), nullable=True)  # IDs dos serviços preferidos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="clients")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, whatsapp={self.whatsapp})>"
