"""
Serviço para gerenciar disponibilidade e bloqueios de horários
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.availability import AvailabilityRule, TimeBlock, Holiday
from app.models.user import User

logger = logging.getLogger(__name__)


class AvailabilityService:
    """Serviço para gerenciar disponibilidade de horários"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_availability_rule(self, user_id: str) -> Optional[AvailabilityRule]:
        """Obter regra de disponibilidade do usuário"""
        try:
            return self.db.query(AvailabilityRule).filter(
                AvailabilityRule.user_id == user_id
            ).first()
        except Exception as e:
            logger.error(f"Erro ao obter regra de disponibilidade: {e}")
            return None
    
    def create_default_availability_rule(self, user_id: str) -> AvailabilityRule:
        """Criar regra de disponibilidade padrão para o usuário"""
        try:
            rule = AvailabilityRule(
                user_id=user_id,
                start_hour=8,
                end_hour=18,
                slot_interval=30,
                buffer_time=15,
                monday=True,
                tuesday=True,
                wednesday=True,
                thursday=True,
                friday=True,
                saturday=False,
                sunday=False,
                lunch_start="12:00",
                lunch_end="13:00"
            )
            
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
            
            logger.info(f"Regra de disponibilidade padrão criada para usuário {user_id}")
            return rule
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar regra de disponibilidade: {e}")
            raise
    
    def check_availability(
        self, 
        user_id: str, 
        start_time: datetime, 
        duration_minutes: int,
        service_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Verificar se um horário está disponível"""
        try:
            # Obter regra de disponibilidade
            rule = self.get_user_availability_rule(user_id)
            if not rule:
                rule = self.create_default_availability_rule(user_id)
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # 1. Verificar horário de funcionamento
            if not self._is_within_business_hours(start_time, end_time, rule):
                return False, "Horário fora do expediente de funcionamento"
            
            # 2. Verificar dia da semana
            if not self._is_working_day(start_time.date(), rule):
                return False, "Dia da semana não disponível"
            
            # 3. Verificar horário de almoço
            if self._is_during_lunch_break(start_time, end_time, rule):
                return False, "Horário durante o período de almoço"
            
            # 4. Verificar bloqueios específicos
            if self._has_time_block(start_time, end_time, user_id):
                return False, "Horário bloqueado"
            
            # 5. Verificar feriados
            if self._is_holiday(start_time.date(), user_id):
                return False, "Data é um feriado"
            
            # 6. Verificar buffer time
            if not self._has_sufficient_buffer(start_time, end_time, user_id, rule.buffer_time):
                return False, f"Intervalo insuficiente entre atendimentos (mínimo {rule.buffer_time} minutos)"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return False, "Erro interno ao verificar disponibilidade"
    
    def get_available_slots(
        self, 
        user_id: str, 
        target_date: date, 
        duration_minutes: int = 60
    ) -> List[time]:
        """Obter horários disponíveis para uma data específica"""
        try:
            rule = self.get_user_availability_rule(user_id)
            if not rule:
                rule = self.create_default_availability_rule(user_id)
            
            # Verificar se é dia útil
            if not self._is_working_day(target_date, rule):
                return []
            
            # Verificar se é feriado
            if self._is_holiday(target_date, user_id):
                return []
            
            available_slots = []
            
            # Gerar slots baseado na regra
            for hour in range(rule.start_hour, rule.end_hour):
                for minute in range(0, 60, rule.slot_interval):
                    slot_time = time(hour, minute)
                    slot_datetime = datetime.combine(target_date, slot_time)
                    
                    # Verificar disponibilidade
                    is_available, _ = self.check_availability(
                        user_id, slot_datetime, duration_minutes
                    )
                    
                    if is_available:
                        available_slots.append(slot_time)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Erro ao obter horários disponíveis: {e}")
            return []
    
    def _is_within_business_hours(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        rule: AvailabilityRule
    ) -> bool:
        """Verificar se está dentro do horário de funcionamento"""
        start_hour = start_time.hour
        end_hour = end_time.hour
        
        return start_hour >= rule.start_hour and end_hour <= rule.end_hour
    
    def _is_working_day(self, target_date: date, rule: AvailabilityRule) -> bool:
        """Verificar se é dia útil"""
        weekday = target_date.weekday()  # 0=segunda, 6=domingo
        
        day_mapping = {
            0: rule.monday,
            1: rule.tuesday,
            2: rule.wednesday,
            3: rule.thursday,
            4: rule.friday,
            5: rule.saturday,
            6: rule.sunday
        }
        
        return day_mapping.get(weekday, False)
    
    def _is_during_lunch_break(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        rule: AvailabilityRule
    ) -> bool:
        """Verificar se está durante o horário de almoço"""
        if not rule.lunch_start or not rule.lunch_end:
            return False
        
        try:
            lunch_start = datetime.strptime(rule.lunch_start, "%H:%M").time()
            lunch_end = datetime.strptime(rule.lunch_end, "%H:%M").time()
            
            start_time_only = start_time.time()
            end_time_only = end_time.time()
            
            # Verificar sobreposição com horário de almoço
            return (start_time_only < lunch_end and end_time_only > lunch_start)
            
        except Exception as e:
            logger.error(f"Erro ao verificar horário de almoço: {e}")
            return False
    
    def _has_time_block(self, start_time: datetime, end_time: datetime, user_id: str) -> bool:
        """Verificar se há bloqueio de horário"""
        try:
            rule = self.get_user_availability_rule(user_id)
            if not rule:
                return False
            
            # Verificar bloqueios ativos
            blocks = self.db.query(TimeBlock).filter(
                and_(
                    TimeBlock.availability_rule_id == rule.id,
                    TimeBlock.is_active == True,
                    or_(
                        # Bloqueio engloba o horário solicitado
                        and_(
                            TimeBlock.start_datetime <= start_time,
                            TimeBlock.end_datetime >= end_time
                        ),
                        # Horário solicitado engloba o bloqueio
                        and_(
                            TimeBlock.start_datetime >= start_time,
                            TimeBlock.end_datetime <= end_time
                        ),
                        # Sobreposição parcial
                        and_(
                            TimeBlock.start_datetime < end_time,
                            TimeBlock.end_datetime > start_time
                        )
                    )
                )
            ).first()
            
            return blocks is not None
            
        except Exception as e:
            logger.error(f"Erro ao verificar bloqueios de horário: {e}")
            return False
    
    def _is_holiday(self, target_date: date, user_id: str) -> bool:
        """Verificar se é feriado"""
        try:
            holiday = self.db.query(Holiday).filter(
                and_(
                    Holiday.user_id == user_id,
                    Holiday.is_active == True,
                    Holiday.holiday_date == target_date
                )
            ).first()
            
            return holiday is not None
            
        except Exception as e:
            logger.error(f"Erro ao verificar feriados: {e}")
            return False
    
    def _has_sufficient_buffer(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        user_id: str, 
        buffer_minutes: int
    ) -> bool:
        """Verificar se há buffer suficiente entre atendimentos"""
        try:
            # Verificar se há agendamentos próximos que violariam o buffer
            buffer_start = start_time - timedelta(minutes=buffer_minutes)
            buffer_end = end_time + timedelta(minutes=buffer_minutes)
            
            # Esta verificação seria feita no AppointmentService
            # Aqui apenas retornamos True por enquanto
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar buffer time: {e}")
            return False
    
    def create_time_block(
        self, 
        user_id: str, 
        start_datetime: datetime, 
        end_datetime: datetime,
        title: str,
        description: str = None,
        block_type: str = "personal"
    ) -> TimeBlock:
        """Criar bloqueio de horário"""
        try:
            rule = self.get_user_availability_rule(user_id)
            if not rule:
                rule = self.create_default_availability_rule(user_id)
            
            time_block = TimeBlock(
                availability_rule_id=rule.id,
                block_type=block_type,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                title=title,
                description=description
            )
            
            self.db.add(time_block)
            self.db.commit()
            self.db.refresh(time_block)
            
            logger.info(f"Bloqueio de horário criado: {title} para usuário {user_id}")
            return time_block
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar bloqueio de horário: {e}")
            raise
    
    def create_holiday(
        self, 
        user_id: str, 
        holiday_date: date, 
        title: str,
        description: str = None,
        is_recurring: bool = False
    ) -> Holiday:
        """Criar feriado"""
        try:
            holiday = Holiday(
                user_id=user_id,
                holiday_date=holiday_date,
                title=title,
                description=description,
                is_recurring=is_recurring
            )
            
            self.db.add(holiday)
            self.db.commit()
            self.db.refresh(holiday)
            
            logger.info(f"Feriado criado: {title} para usuário {user_id}")
            return holiday
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar feriado: {e}")
            raise
