"""
Modelo de agendamento
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.enums import AppointmentStatus


class Appointment(Base):
    """Modelo de agendamento"""
    
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Informações do cliente (podem ser diferentes do cliente cadastrado)
    client_name = Column(String(255), nullable=False)
    client_whatsapp = Column(String(20), nullable=False)
    client_email = Column(String(255), nullable=True)
    
    # Horários
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)  # Duração em minutos
    
    # Status e controle
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING, nullable=False, index=True)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    # Informações adicionais
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)  # Notas internas do profissional
    reminder_sent = Column(Boolean, default=False, nullable=False)
    confirmation_sent = Column(Boolean, default=False, nullable=False)
    
    # Metadados
    source = Column(String(50), default="web", nullable=False)  # web, api, whatsapp, etc.
    custom_fields = Column(JSONB, nullable=True)  # Campos customizados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    service = relationship("Service", back_populates="appointments")
    user = relationship("User", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, client_name={self.client_name}, start_time={self.start_time})>"
    
    @property
    def is_available(self) -> bool:
        """Verifica se o agendamento está disponível (não cancelado)"""
        return not self.is_cancelled and self.status != AppointmentStatus.CANCELLED
    
    @property
    def is_past(self) -> bool:
        """Verifica se o agendamento já passou"""
        return self.end_time < datetime.utcnow()
    
    @property
    def is_today(self) -> bool:
        """Verifica se o agendamento é hoje"""
        today = datetime.utcnow().date()
        return self.start_time.date() == today
    
    @property
    def is_tomorrow(self) -> bool:
        """Verifica se o agendamento é amanhã"""
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        return self.start_time.date() == tomorrow
    
    def calculate_end_time(self) -> datetime:
        """Calcula o horário de fim baseado na duração do serviço"""
        if self.service and self.service.duration:
            return self.start_time + timedelta(minutes=self.service.duration)
        elif self.duration_minutes:
            return self.start_time + timedelta(minutes=self.duration_minutes)
        return self.end_time
    
    def update_status_flags(self):
        """Atualiza as flags de status baseado no status principal"""
        if self.status == AppointmentStatus.CONFIRMED:
            self.is_confirmed = True
            self.is_cancelled = False
            self.is_completed = False
        elif self.status == AppointmentStatus.CANCELLED:
            self.is_confirmed = False
            self.is_cancelled = True
            self.is_completed = False
        elif self.status == AppointmentStatus.COMPLETED:
            self.is_confirmed = True
            self.is_cancelled = False
            self.is_completed = True
        else:  # PENDING
            self.is_confirmed = False
            self.is_cancelled = False
            self.is_completed = False
