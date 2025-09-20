"""
Modelo de cliente com histórico e métricas completas
"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Date, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    """Modelo de cliente com histórico e métricas completas"""
    
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Informações básicas
    name = Column(String(255), nullable=False)
    whatsapp = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Status e controle
    is_active = Column(Boolean, default=True, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)  # Cliente VIP
    
    # Histórico de agendamentos
    first_appointment_at = Column(DateTime, nullable=True)  # Primeiro agendamento
    last_appointment_at = Column(DateTime, nullable=True)   # Último agendamento
    total_appointments = Column(Integer, default=0, nullable=False)
    completed_appointments = Column(Integer, default=0, nullable=False)
    cancelled_appointments = Column(Integer, default=0, nullable=False)
    no_show_appointments = Column(Integer, default=0, nullable=False)
    
    # Métricas de frequência
    frequency_score = Column(Float, default=0.0, nullable=False)  # Score de frequência (0-100)
    appointments_this_month = Column(Integer, default=0, nullable=False)
    appointments_last_month = Column(Integer, default=0, nullable=False)
    appointments_this_year = Column(Integer, default=0, nullable=False)
    average_days_between_appointments = Column(Float, default=0.0, nullable=False)
    
    # Preferências e comportamento
    preferred_services = Column(ARRAY(UUID), nullable=True)  # IDs dos serviços preferidos
    preferred_days = Column(ARRAY(String), nullable=True)    # Dias da semana preferidos
    preferred_times = Column(ARRAY(String), nullable=True)   # Horários preferidos
    communication_preference = Column(String(20), default="whatsapp", nullable=False)  # whatsapp, email, sms
    
    # Dados demográficos (opcionais)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    
    # Métricas financeiras
    total_spent = Column(Float, default=0.0, nullable=False)
    average_ticket = Column(Float, default=0.0, nullable=False)
    last_payment_at = Column(DateTime, nullable=True)
    
    # Dados de marketing
    source = Column(String(100), nullable=True)  # Como conheceu o negócio
    referral_code = Column(String(50), nullable=True)  # Código de indicação
    tags = Column(ARRAY(String), nullable=True)  # Tags personalizadas
    
    # Metadados
    custom_fields = Column(JSON, nullable=True)  # Campos customizados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, whatsapp={self.whatsapp})>"
    
    @property
    def is_regular_customer(self) -> bool:
        """Verifica se é um cliente regular (mais de 3 agendamentos)"""
        return self.total_appointments >= 3
    
    @property
    def is_frequent_customer(self) -> bool:
        """Verifica se é um cliente frequente (mais de 1 agendamento por mês)"""
        return self.frequency_score >= 50.0
    
    @property
    def days_since_last_appointment(self) -> int:
        """Dias desde o último agendamento"""
        if not self.last_appointment_at:
            return 0
        return (datetime.utcnow() - self.last_appointment_at).days
    
    @property
    def customer_lifetime_days(self) -> int:
        """Dias desde o primeiro agendamento"""
        if not self.first_appointment_at:
            return 0
        return (datetime.utcnow() - self.first_appointment_at).days
    
    @property
    def no_show_rate(self) -> float:
        """Taxa de no-show (não comparecimento)"""
        if self.total_appointments == 0:
            return 0.0
        return (self.no_show_appointments / self.total_appointments) * 100
    
    @property
    def completion_rate(self) -> float:
        """Taxa de conclusão de agendamentos"""
        if self.total_appointments == 0:
            return 0.0
        return (self.completed_appointments / self.total_appointments) * 100
    
    def update_frequency_score(self):
        """Atualiza o score de frequência baseado no comportamento"""
        if self.total_appointments == 0:
            self.frequency_score = 0.0
            return
        
        # Fatores que influenciam o score
        appointments_factor = min(self.total_appointments * 10, 50)  # Máximo 50 pontos
        recency_factor = max(0, 30 - self.days_since_last_appointment)  # Máximo 30 pontos
        consistency_factor = 20 if self.is_regular_customer else 0  # 20 pontos para clientes regulares
        
        self.frequency_score = min(appointments_factor + recency_factor + consistency_factor, 100.0)
    
    def add_appointment(self, appointment_type: str = "completed"):
        """Adiciona um agendamento e atualiza métricas"""
        self.total_appointments += 1
        
        if appointment_type == "completed":
            self.completed_appointments += 1
        elif appointment_type == "cancelled":
            self.cancelled_appointments += 1
        elif appointment_type == "no_show":
            self.no_show_appointments += 1
        
        # Atualizar datas
        now = datetime.utcnow()
        if not self.first_appointment_at:
            self.first_appointment_at = now
        self.last_appointment_at = now
        
        # Atualizar score de frequência
        self.update_frequency_score()
        
        # Atualizar timestamp
        self.updated_at = now