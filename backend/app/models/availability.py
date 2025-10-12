"""
Modelo para gerenciar disponibilidade e bloqueios de horários
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, time
from uuid import uuid4

from app.database import Base


class AvailabilityRule(Base):
    """Regras de disponibilidade para usuários"""
    __tablename__ = "availability_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Configurações de horário de funcionamento
    start_hour = Column(Integer, default=8, nullable=False)  # 8h
    end_hour = Column(Integer, default=18, nullable=False)   # 18h
    slot_interval = Column(Integer, default=30, nullable=False)  # 30 minutos
    buffer_time = Column(Integer, default=15, nullable=False)  # 15 minutos entre atendimentos
    
    # Dias da semana (0=segunda, 6=domingo)
    monday = Column(Boolean, default=True, nullable=False)
    tuesday = Column(Boolean, default=True, nullable=False)
    wednesday = Column(Boolean, default=True, nullable=False)
    thursday = Column(Boolean, default=True, nullable=False)
    friday = Column(Boolean, default=True, nullable=False)
    saturday = Column(Boolean, default=False, nullable=False)
    sunday = Column(Boolean, default=False, nullable=False)
    
    # Configurações especiais
    lunch_start = Column(String(5), nullable=True)  # "12:00"
    lunch_end = Column(String(5), nullable=True)    # "13:00"
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="availability_rule")
    time_blocks = relationship("TimeBlock", back_populates="availability_rule", cascade="all, delete-orphan")


class TimeBlock(Base):
    """Bloqueios de horário específicos"""
    __tablename__ = "time_blocks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    availability_rule_id = Column(UUID(as_uuid=True), ForeignKey("availability_rules.id"), nullable=False)
    
    # Tipo de bloqueio
    block_type = Column(String(20), nullable=False)  # "holiday", "maintenance", "personal", "recurring"
    
    # Período do bloqueio
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    
    # Configurações
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurring_pattern = Column(String(50), nullable=True)  # "daily", "weekly", "monthly"
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    availability_rule = relationship("AvailabilityRule", back_populates="time_blocks")


class Holiday(Base):
    """Feriados e datas especiais"""
    __tablename__ = "holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Data do feriado
    holiday_date = Column(DateTime, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configurações
    is_recurring = Column(Boolean, default=False, nullable=False)  # Feriado recorrente (ex: Natal)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="holidays")
