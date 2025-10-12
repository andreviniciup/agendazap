"""
Serviço para gerenciamento de agendamentos
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, between
from fastapi import HTTPException, status
import logging
from uuid import UUID
from datetime import datetime, date, time, timedelta

from app.models.appointment import Appointment
from app.models.service import Service
from app.models.user import User
from app.models.client import Client
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentSearch, 
    PublicAppointmentCreate, AppointmentConfirmation, AppointmentCancellation
)
from app.utils.enums import AppointmentStatus
from app.services.plan_service import PlanService
from app.services.queue_service import MessageQueue
from app.services.client_service import ClientService
from app.services.cache_service import cache_service
from app.services.availability_service import AvailabilityService

logger = logging.getLogger(__name__)


class AppointmentService:
    """Serviço para operações relacionadas a agendamentos"""
    
    def __init__(self, db: Session, plan_service: PlanService, message_queue: MessageQueue = None, client_service: ClientService = None, availability_service: AvailabilityService = None):
        self.db = db
        self.plan_service = plan_service
        self.message_queue = message_queue
        self.client_service = client_service
        self.availability_service = availability_service
    
    def check_availability(
        self, 
        user_id: UUID, 
        service_id: UUID, 
        start_time: datetime, 
        duration_minutes: int
    ) -> Tuple[bool, Optional[str]]:
        """Verificar disponibilidade para um agendamento"""
        try:
            # 1. Verificar disponibilidade geral (horários, bloqueios, feriados)
            if self.availability_service:
                is_available, reason = self.availability_service.check_availability(
                    str(user_id), start_time, duration_minutes
                )
                if not is_available:
                    return False, reason
            
            # 2. Verificar conflitos com outros agendamentos
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            conflicting_appointments = self.db.query(Appointment).filter(
                and_(
                    Appointment.user_id == user_id,
                    Appointment.service_id == service_id,
                    Appointment.is_cancelled == False,
                    Appointment.status != AppointmentStatus.CANCELLED,
                    or_(
                        # Conflito: novo agendamento começa durante um existente
                        and_(
                            Appointment.start_time <= start_time,
                            Appointment.end_time > start_time
                        ),
                        # Conflito: novo agendamento termina durante um existente
                        and_(
                            Appointment.start_time < end_time,
                            Appointment.end_time >= end_time
                        ),
                        # Conflito: novo agendamento engloba um existente
                        and_(
                            Appointment.start_time >= start_time,
                            Appointment.end_time <= end_time
                        )
                    )
                )
            ).first()
            
            if conflicting_appointments:
                return False, f"Conflito com agendamento existente de {conflicting_appointments.start_time.strftime('%H:%M')} às {conflicting_appointments.end_time.strftime('%H:%M')}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return False, "Erro interno ao verificar disponibilidade"
    
    def get_available_slots(
        self, 
        user_id: UUID, 
        service_id: UUID, 
        target_date: date,
        duration_minutes: int = 60
    ) -> List[time]:
        """Obter horários disponíveis para uma data específica"""
        try:
            # Usar o serviço de disponibilidade se disponível
            if self.availability_service:
                return self.availability_service.get_available_slots(
                    str(user_id), target_date, duration_minutes
                )
            
            # Fallback para lógica antiga
            start_hour = 8
            end_hour = 18
            slot_interval = 30  # Intervalo de 30 minutos
            
            available_slots = []
            
            # Gerar todos os possíveis horários
            for hour in range(start_hour, end_hour):
                for minute in range(0, 60, slot_interval):
                    slot_time = time(hour, minute)
                    slot_datetime = datetime.combine(target_date, slot_time)
                    
                    # Verificar se o horário está disponível
                    is_available, _ = self.check_availability(
                        user_id, service_id, slot_datetime, duration_minutes
                    )
                    
                    if is_available:
                        available_slots.append(slot_time)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Erro ao obter horários disponíveis: {e}")
            return []
    
    async def create_appointment(
        self, 
        appointment_data: AppointmentCreate, 
        user: User
    ) -> Appointment:
        """Criar novo agendamento"""
        try:
            # Verificar limite de agendamentos
            can_create = await self.plan_service.check_limit(user, "appointments_per_month", 1)
            if not can_create:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Limite de agendamentos do plano atingido"
                )
            
            # Buscar serviço
            service = self.db.query(Service).filter(
                and_(
                    Service.id == appointment_data.service_id,
                    Service.user_id == user.id,
                    Service.is_active == True
                )
            ).first()
            
            if not service:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Serviço não encontrado ou inativo"
                )
            
            # Calcular duração e horário de fim
            duration_minutes = service.duration
            start_time = appointment_data.start_time
            end_time = appointment_data.end_time or (start_time + timedelta(minutes=duration_minutes))
            
            # Verificar disponibilidade
            is_available, conflict_message = self.check_availability(
                user.id, service.id, start_time, duration_minutes
            )
            
            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=conflict_message
                )
            
            # Encontrar ou criar cliente automaticamente
            client = None
            if appointment_data.client_id:
                # Buscar cliente existente se ID fornecido
                client = self.db.query(Client).filter(
                    and_(
                        Client.id == appointment_data.client_id,
                        Client.user_id == user.id
                    )
                ).first()
            elif appointment_data.client_whatsapp and self.client_service:
                # Criar ou encontrar cliente automaticamente pelo WhatsApp
                client = await self.client_service.find_or_create_client(
                    name=appointment_data.client_name,
                    whatsapp=appointment_data.client_whatsapp,
                    email=appointment_data.client_email,
                    current_user=user
                )
            
            # Criar agendamento
            appointment = Appointment(
                service_id=appointment_data.service_id,
                user_id=user.id,
                client_id=client.id if client else None,
                client_name=appointment_data.client_name,
                client_whatsapp=appointment_data.client_whatsapp,
                client_email=appointment_data.client_email,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                notes=appointment_data.notes,
                internal_notes=appointment_data.internal_notes,
                source=appointment_data.source,
                custom_fields=appointment_data.custom_fields,
                status=AppointmentStatus.PENDING
            )
            
            # Atualizar flags de status
            appointment.update_status_flags()
            
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)
            
            # Incrementar contador de uso
            await self.plan_service.increment_usage(str(user.id), "appointments", 1)
            
            # Atualizar métricas do cliente se existir
            if client and self.client_service:
                await self.client_service.update_client_metrics(client.id, user)
            
            # Agendar notificações automáticas
            if self.message_queue:
                await self._schedule_appointment_notifications(appointment, service)
            
            # Invalidar cache de agenda para a data do agendamento
            appointment_date = appointment.start_time.date()
            cache_service.invalidate_user_agenda(user.id, appointment_date.isoformat())
            
            logger.info(f"Agendamento criado: {appointment.client_name} para {appointment.start_time} - usuário {user.email}")
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def create_public_appointment(
        self, 
        appointment_data: PublicAppointmentCreate, 
        user_id: UUID
    ) -> Appointment:
        """Criar agendamento público (via vitrine)"""
        try:
            # Buscar serviço
            service = self.db.query(Service).filter(
                and_(
                    Service.id == appointment_data.service_id,
                    Service.user_id == user_id,
                    Service.is_active == True
                )
            ).first()
            
            if not service:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Serviço não encontrado ou inativo"
                )
            
            # Calcular duração e horário de fim
            duration_minutes = service.duration
            start_time = appointment_data.start_time
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Verificar disponibilidade
            is_available, conflict_message = self.check_availability(
                user_id, service.id, start_time, duration_minutes
            )
            
            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=conflict_message
                )
            
            # Criar agendamento público
            appointment = Appointment(
                service_id=appointment_data.service_id,
                user_id=user_id,
                client_name=appointment_data.client_name,
                client_whatsapp=appointment_data.client_whatsapp,
                client_email=appointment_data.client_email,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                notes=appointment_data.notes,
                source=appointment_data.source,
                status=AppointmentStatus.PENDING
            )
            
            # Atualizar flags de status
            appointment.update_status_flags()
            
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)
            
            # Invalidar cache de agenda para a data do agendamento
            appointment_date = appointment.start_time.date()
            cache_service.invalidate_user_agenda(user_id, appointment_date.isoformat())
            
            logger.info(f"Agendamento público criado: {appointment.client_name} para {appointment.start_time}")
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar agendamento público: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_appointments(
        self, 
        user: User, 
        search_params: Optional[AppointmentSearch] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """Obter agendamentos do usuário com filtros e paginação"""
        try:
            query = self.db.query(Appointment).filter(Appointment.user_id == user.id)
            
            # Aplicar filtros se fornecidos
            if search_params:
                if search_params.query:
                    query = query.filter(
                        or_(
                            Appointment.client_name.ilike(f"%{search_params.query}%"),
                            Appointment.notes.ilike(f"%{search_params.query}%")
                        )
                    )
                
                if search_params.service_id:
                    query = query.filter(Appointment.service_id == search_params.service_id)
                
                if search_params.client_id:
                    query = query.filter(Appointment.client_id == search_params.client_id)
                
                if search_params.status:
                    query = query.filter(Appointment.status == search_params.status)
                
                if search_params.start_date:
                    query = query.filter(Appointment.start_time >= search_params.start_date)
                
                if search_params.end_date:
                    query = query.filter(Appointment.start_time <= search_params.end_date)
                
                if search_params.is_today:
                    today = date.today()
                    query = query.filter(
                        func.date(Appointment.start_time) == today
                    )
                
                if search_params.is_tomorrow:
                    tomorrow = date.today() + timedelta(days=1)
                    query = query.filter(
                        func.date(Appointment.start_time) == tomorrow
                    )
                
                if search_params.is_past:
                    now = datetime.utcnow()
                    query = query.filter(Appointment.end_time < now)
                
                if search_params.is_future:
                    now = datetime.utcnow()
                    query = query.filter(Appointment.start_time > now)
                
                # Ordenação
                sort_field = getattr(Appointment, search_params.sort_by, Appointment.start_time)
                if search_params.sort_order == "desc":
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(Appointment.start_time)
            
            # Contar total
            total = query.count()
            
            # Paginação
            offset = (page - 1) * per_page
            appointments = query.offset(offset).limit(per_page).all()
            
            # Calcular páginas
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "appointments": appointments,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter agendamentos: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_user_agenda(
        self, 
        user: User, 
        target_date: date,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Obter agenda do usuário para uma data específica com cache e fallback"""
        try:
            date_str = target_date.isoformat()
            
            # Função para buscar do banco (fallback)
            def fetch_from_database():
                start_datetime = datetime.combine(target_date, time.min)
                end_datetime = datetime.combine(target_date, time.max)
                
                appointments = self.db.query(Appointment).filter(
                    and_(
                        Appointment.user_id == user.id,
                        Appointment.start_time >= start_datetime,
                        Appointment.start_time <= end_datetime,
                        Appointment.is_cancelled == False
                    )
                ).order_by(Appointment.start_time).all()
                
                # Organizar agenda por horário
                agenda_data = {
                    "date": date_str,
                    "appointments": [],
                    "total_appointments": len(appointments),
                    "available_slots": self.get_available_slots(
                        user.id, None, target_date
                    ) if appointments else []
                }
                
                for appointment in appointments:
                    agenda_data["appointments"].append({
                        "id": str(appointment.id),
                        "client_name": appointment.client_name,
                        "client_whatsapp": appointment.client_whatsapp,
                        "service_name": appointment.service.name if appointment.service else "Serviço removido",
                        "start_time": appointment.start_time.isoformat(),
                        "end_time": appointment.end_time.isoformat(),
                        "duration_minutes": appointment.duration_minutes,
                        "status": appointment.status.value,
                        "notes": appointment.notes,
                        "is_confirmed": appointment.is_confirmed
                    })
                
                return agenda_data
            
            # Tentar obter do cache primeiro
            if use_cache:
                cached_agenda = cache_service.get_user_agenda(user.id, date_str)
                if cached_agenda:
                    logger.debug(f"Agenda obtida do cache para usuário {user.id} na data {date_str}")
                    return cached_agenda
            
            # Se não está no cache, buscar do banco
            agenda_data = fetch_from_database()
            
            # Salvar no cache se disponível
            if use_cache and cache_service.is_cache_healthy():
                cache_service.set_user_agenda(user.id, date_str, agenda_data)
                logger.debug(f"Agenda salva no cache para usuário {user.id} na data {date_str}")
            
            return agenda_data
            
        except Exception as e:
            logger.error(f"Erro ao obter agenda do usuário: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_user_agenda_range(
        self, 
        user: User, 
        start_date: date, 
        end_date: date,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Obter agenda do usuário para um período com cache"""
        try:
            agenda_range = {}
            current_date = start_date
            
            while current_date <= end_date:
                agenda_data = self.get_user_agenda(user, current_date, use_cache)
                agenda_range[current_date.isoformat()] = agenda_data
                current_date += timedelta(days=1)
            
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "agenda": agenda_range,
                "total_days": len(agenda_range)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter agenda do usuário para período: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_appointment(self, appointment_id: UUID, user: User) -> Appointment:
        """Obter agendamento específico"""
        try:
            appointment = self.db.query(Appointment).filter(
                and_(
                    Appointment.id == appointment_id,
                    Appointment.user_id == user.id
                )
            ).first()
            
            if not appointment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agendamento não encontrado"
                )
            
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def update_appointment(
        self, 
        appointment_id: UUID, 
        appointment_data: AppointmentUpdate, 
        user: User
    ) -> Appointment:
        """Atualizar agendamento"""
        try:
            appointment = self.get_appointment(appointment_id, user)
            
            # Se está alterando horário, verificar disponibilidade
            if appointment_data.start_time and appointment_data.start_time != appointment.start_time:
                duration = appointment_data.duration_minutes or appointment.duration_minutes
                is_available, conflict_message = self.check_availability(
                    user.id, appointment.service_id, appointment_data.start_time, duration
                )
                
                if not is_available:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=conflict_message
                    )
            
            # Atualizar campos
            update_data = appointment_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(appointment, field, value)
            
            # Recalcular end_time se necessário
            if appointment_data.start_time:
                appointment.end_time = appointment.calculate_end_time()
            
            # Atualizar flags de status se status foi alterado
            if appointment_data.status:
                appointment.update_status_flags()
            
            self.db.commit()
            self.db.refresh(appointment)
            
            # Invalidar cache de agenda para as datas afetadas
            old_date = appointment.start_time.date()
            if appointment_data.start_time and appointment_data.start_time != appointment.start_time:
                new_date = appointment_data.start_time.date()
                cache_service.invalidate_user_agenda(user.id, old_date.isoformat())
                cache_service.invalidate_user_agenda(user.id, new_date.isoformat())
            else:
                cache_service.invalidate_user_agenda(user.id, old_date.isoformat())
            
            logger.info(f"Agendamento atualizado: {appointment.id} para usuário {user.email}")
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def confirm_appointment(
        self, 
        appointment_id: UUID, 
        confirmation_data: AppointmentConfirmation, 
        user: User
    ) -> Appointment:
        """Confirmar agendamento"""
        try:
            appointment = self.get_appointment(appointment_id, user)
            
            if appointment.status == AppointmentStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é possível confirmar um agendamento cancelado"
                )
            
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.is_confirmed = True
            appointment.confirmation_sent = True
            
            if confirmation_data.confirmation_notes:
                appointment.internal_notes = confirmation_data.confirmation_notes
            
            self.db.commit()
            self.db.refresh(appointment)
            
            logger.info(f"Agendamento confirmado: {appointment.id} para usuário {user.email}")
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao confirmar agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def cancel_appointment(
        self, 
        appointment_id: UUID, 
        cancellation_data: AppointmentCancellation, 
        user: User
    ) -> Appointment:
        """Cancelar agendamento"""
        try:
            appointment = self.get_appointment(appointment_id, user)
            
            if appointment.status == AppointmentStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agendamento já está cancelado"
                )
            
            appointment.status = AppointmentStatus.CANCELLED
            appointment.is_cancelled = True
            
            if cancellation_data.cancellation_reason:
                appointment.internal_notes = cancellation_data.cancellation_reason
            
            self.db.commit()
            self.db.refresh(appointment)
            
            # Invalidar cache de agenda para a data do agendamento
            appointment_date = appointment.start_time.date()
            cache_service.invalidate_user_agenda(user.id, appointment_date.isoformat())
            
            # Agendar notificação de cancelamento
            if self.message_queue and appointment.service:
                # Executar de forma assíncrona
                import asyncio
                asyncio.create_task(self.schedule_cancellation_notification(
                    appointment, 
                    appointment.service, 
                    cancellation_data.cancellation_reason
                ))
            
            logger.info(f"Agendamento cancelado: {appointment.id} para usuário {user.email}")
            return appointment
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao cancelar agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def delete_appointment(self, appointment_id: UUID, user: User) -> None:
        """Deletar agendamento (soft delete)"""
        try:
            appointment = self.get_appointment(appointment_id, user)
            
            # Soft delete - marcar como cancelado
            appointment.status = AppointmentStatus.CANCELLED
            appointment.is_cancelled = True
            self.db.commit()
            
            # Invalidar cache de agenda para a data do agendamento
            appointment_date = appointment.start_time.date()
            cache_service.invalidate_user_agenda(user.id, appointment_date.isoformat())
            
            logger.info(f"Agendamento deletado: {appointment.id} para usuário {user.email}")
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar agendamento: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    def get_appointment_stats(self, user: User) -> Dict[str, Any]:
        """Obter estatísticas dos agendamentos do usuário"""
        try:
            now = datetime.utcnow()
            today = now.date()
            tomorrow = today + timedelta(days=1)
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            stats = self.db.query(
                func.count(Appointment.id).label('total_appointments'),
                func.count(Appointment.id).filter(Appointment.status == AppointmentStatus.PENDING).label('pending_appointments'),
                func.count(Appointment.id).filter(Appointment.status == AppointmentStatus.CONFIRMED).label('confirmed_appointments'),
                func.count(Appointment.id).filter(Appointment.status == AppointmentStatus.CANCELLED).label('cancelled_appointments'),
                func.count(Appointment.id).filter(Appointment.status == AppointmentStatus.COMPLETED).label('completed_appointments'),
                func.count(Appointment.id).filter(func.date(Appointment.start_time) == today).label('today_appointments'),
                func.count(Appointment.id).filter(func.date(Appointment.start_time) == tomorrow).label('tomorrow_appointments'),
                func.count(Appointment.id).filter(func.date(Appointment.start_time) >= week_start).label('this_week_appointments'),
                func.count(Appointment.id).filter(func.date(Appointment.start_time) >= month_start).label('this_month_appointments'),
                func.avg(Appointment.duration_minutes).label('average_duration')
            ).filter(Appointment.user_id == user.id).first()
            
            # Serviço mais popular
            most_popular_service = self.db.query(
                Service.name,
                func.count(Appointment.id).label('appointment_count')
            ).join(Appointment, Service.id == Appointment.service_id)\
            .filter(Appointment.user_id == user.id)\
            .group_by(Service.id, Service.name)\
            .order_by(desc('appointment_count'))\
            .first()
            
            return {
                "total_appointments": stats.total_appointments or 0,
                "pending_appointments": stats.pending_appointments or 0,
                "confirmed_appointments": stats.confirmed_appointments or 0,
                "cancelled_appointments": stats.cancelled_appointments or 0,
                "completed_appointments": stats.completed_appointments or 0,
                "today_appointments": stats.today_appointments or 0,
                "tomorrow_appointments": stats.tomorrow_appointments or 0,
                "this_week_appointments": stats.this_week_appointments or 0,
                "this_month_appointments": stats.this_month_appointments or 0,
                "average_duration": float(stats.average_duration or 0),
                "most_popular_service": {
                    "name": most_popular_service[0],
                    "appointment_count": most_popular_service[1]
                } if most_popular_service else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de agendamentos: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def _schedule_appointment_notifications(self, appointment: Appointment, service: Service):
        """Agendar notificações automáticas para o agendamento"""
        try:
            if not self.message_queue:
                return
            
            # Agendar confirmação imediata
            await self.message_queue.schedule_appointment_confirmation(
                appointment.id,
                appointment.client_name,
                appointment.client_whatsapp,
                service.name,
                appointment.start_time,
                delay_seconds=0
            )
            
            # Agendar lembrete 24h antes
            await self.message_queue.schedule_appointment_reminder(
                appointment.id,
                appointment.client_name,
                appointment.client_whatsapp,
                service.name,
                appointment.start_time,
                reminder_hours=24
            )
            
            # Agendar follow-up 24h depois
            await self.message_queue.schedule_appointment_follow_up(
                appointment.id,
                appointment.client_name,
                appointment.client_whatsapp,
                service.name,
                appointment.start_time,
                follow_up_hours=24
            )
            
            logger.info(f"Notificações agendadas para agendamento {appointment.id}")
            
        except Exception as e:
            logger.error(f"Erro ao agendar notificações para agendamento {appointment.id}: {e}")
    
    async def schedule_cancellation_notification(self, appointment: Appointment, service: Service, cancellation_reason: str = None):
        """Agendar notificação de cancelamento"""
        try:
            if not self.message_queue:
                return
            
            await self.message_queue.schedule_appointment_cancellation(
                appointment.id,
                appointment.client_name,
                appointment.client_whatsapp,
                service.name,
                appointment.start_time,
                cancellation_reason
            )
            
            logger.info(f"Notificação de cancelamento agendada para agendamento {appointment.id}")
            
        except Exception as e:
            logger.error(f"Erro ao agendar notificação de cancelamento para agendamento {appointment.id}: {e}")
