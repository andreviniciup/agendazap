"""
Serviço para gestão de clientes com histórico e métricas
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, extract, desc, asc
from fastapi import HTTPException, status
import logging
from math import ceil

from app.models.client import Client
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.user import User
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientSearch, ClientBulkUpdate,
    ClientHistory, ClientAnalytics
)
from app.utils.enums import AppointmentStatus
from app.services.plan_service import PlanService

logger = logging.getLogger(__name__)


class ClientService:
    """Serviço para operações relacionadas a clientes"""
    
    def __init__(self, db: Session, plan_service: PlanService):
        self.db = db
        self.plan_service = plan_service
    
    async def create_client(self, client_data: ClientCreate, current_user: User) -> Client:
        """Criar novo cliente"""
        try:
            # Verificar se já existe cliente com mesmo WhatsApp
            existing_client = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.whatsapp == client_data.whatsapp
            ).first()
            
            if existing_client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe um cliente com este número de WhatsApp"
                )
            
            # Criar novo cliente
            new_client = Client(
                user_id=current_user.id,
                name=client_data.name,
                whatsapp=client_data.whatsapp,
                email=client_data.email,
                notes=client_data.notes,
                birth_date=client_data.birth_date,
                gender=client_data.gender,
                address=client_data.address,
                city=client_data.city,
                state=client_data.state,
                zip_code=client_data.zip_code,
                communication_preference=client_data.communication_preference or "whatsapp",
                source=client_data.source,
                referral_code=client_data.referral_code,
                tags=client_data.tags,
                custom_fields=client_data.custom_fields
            )
            
            self.db.add(new_client)
            self.db.commit()
            self.db.refresh(new_client)
            
            logger.info(f"Cliente criado: {new_client.name} - usuário {current_user.email}")
            return new_client
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def get_clients(self, current_user: User, search_params: ClientSearch) -> Dict[str, Any]:
        """Obter clientes do usuário com filtros e paginação"""
        try:
            query = self.db.query(Client).filter(Client.user_id == current_user.id)
            
            # Filtros de busca
            if search_params.query:
                query = query.filter(
                    or_(
                        Client.name.ilike(f"%{search_params.query}%"),
                        Client.email.ilike(f"%{search_params.query}%"),
                        Client.whatsapp.ilike(f"%{search_params.query}%")
                    )
                )
            
            if search_params.is_active is not None:
                query = query.filter(Client.is_active == search_params.is_active)
            
            if search_params.is_vip is not None:
                query = query.filter(Client.is_vip == search_params.is_vip)
            
            if search_params.is_regular is not None:
                if search_params.is_regular:
                    query = query.filter(Client.total_appointments >= 3)
                else:
                    query = query.filter(Client.total_appointments < 3)
            
            if search_params.is_frequent is not None:
                if search_params.is_frequent:
                    query = query.filter(Client.frequency_score >= 50.0)
                else:
                    query = query.filter(Client.frequency_score < 50.0)
            
            if search_params.min_appointments is not None:
                query = query.filter(Client.total_appointments >= search_params.min_appointments)
            
            if search_params.max_appointments is not None:
                query = query.filter(Client.total_appointments <= search_params.max_appointments)
            
            if search_params.min_frequency_score is not None:
                query = query.filter(Client.frequency_score >= search_params.min_frequency_score)
            
            if search_params.max_frequency_score is not None:
                query = query.filter(Client.frequency_score <= search_params.max_frequency_score)
            
            if search_params.city:
                query = query.filter(Client.city.ilike(f"%{search_params.city}%"))
            
            if search_params.state:
                query = query.filter(Client.state.ilike(f"%{search_params.state}%"))
            
            if search_params.source:
                query = query.filter(Client.source.ilike(f"%{search_params.source}%"))
            
            if search_params.tags:
                for tag in search_params.tags:
                    query = query.filter(Client.tags.contains([tag]))
            
            if search_params.created_after:
                query = query.filter(Client.created_at >= search_params.created_after)
            
            if search_params.created_before:
                query = query.filter(Client.created_at <= search_params.created_before)
            
            if search_params.last_appointment_after:
                query = query.filter(Client.last_appointment_at >= search_params.last_appointment_after)
            
            if search_params.last_appointment_before:
                query = query.filter(Client.last_appointment_at <= search_params.last_appointment_before)
            
            # Ordenação
            if search_params.sort_by:
                sort_field = getattr(Client, search_params.sort_by, None)
                if sort_field:
                    if search_params.sort_order == "desc":
                        query = query.order_by(desc(sort_field))
                    else:
                        query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(asc(Client.name))
            else:
                query = query.order_by(asc(Client.name))
            
            # Paginação
            total = query.count()
            clients = query.offset((search_params.page - 1) * search_params.per_page).limit(search_params.per_page).all()
            
            total_pages = ceil(total / search_params.per_page) if total > 0 else 1
            
            return {
                "clients": clients,
                "total": total,
                "page": search_params.page,
                "per_page": search_params.per_page,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter clientes: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def get_client(self, client_id: UUID, current_user: User) -> Client:
        """Obter cliente específico"""
        try:
            client = self.db.query(Client).filter(
                Client.id == client_id,
                Client.user_id == current_user.id
            ).first()
            
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente não encontrado"
                )
            
            return client
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def update_client(self, client_id: UUID, client_data: ClientUpdate, current_user: User) -> Client:
        """Atualizar cliente"""
        try:
            client = await self.get_client(client_id, current_user)
            
            # Verificar se WhatsApp já existe em outro cliente
            if client_data.whatsapp and client_data.whatsapp != client.whatsapp:
                existing_client = self.db.query(Client).filter(
                    Client.user_id == current_user.id,
                    Client.whatsapp == client_data.whatsapp,
                    Client.id != client_id
                ).first()
                
                if existing_client:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Já existe um cliente com este número de WhatsApp"
                    )
            
            # Atualizar campos
            update_data = client_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(client, key, value)
            
            client.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(client)
            
            logger.info(f"Cliente atualizado: {client.name} - usuário {current_user.email}")
            return client
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def delete_client(self, client_id: UUID, current_user: User):
        """Deletar cliente (soft delete)"""
        try:
            client = await self.get_client(client_id, current_user)
            
            # Soft delete - marcar como inativo
            client.is_active = False
            client.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Cliente deletado: {client.name} - usuário {current_user.email}")
            return {"message": "Cliente deletado com sucesso"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def get_client_history(self, client_id: UUID, current_user: User) -> ClientHistory:
        """Obter histórico completo do cliente"""
        try:
            client = await self.get_client(client_id, current_user)
            
            # Buscar agendamentos do cliente
            appointments = self.db.query(Appointment).filter(
                Appointment.client_id == client_id,
                Appointment.user_id == current_user.id
            ).order_by(desc(Appointment.start_time)).all()
            
            # Calcular métricas
            total_appointments = len(appointments)
            completed_appointments = len([a for a in appointments if a.status.value == "completed"])
            cancelled_appointments = len([a for a in appointments if a.status.value == "cancelled"])
            no_show_appointments = len([a for a in appointments if a.status.value == "cancelled" and not a.is_confirmed])
            
            # Serviços preferidos
            service_counts = {}
            for appointment in appointments:
                if appointment.service:
                    service_name = appointment.service.name
                    service_counts[service_name] = service_counts.get(service_name, 0) + 1
            
            preferred_services = [
                {"name": name, "count": count} 
                for name, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Dias preferidos
            day_counts = {}
            for appointment in appointments:
                day_name = appointment.start_time.strftime("%A")
                day_counts[day_name] = day_counts.get(day_name, 0) + 1
            
            preferred_days = [
                day for day, count in sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]
            
            # Horários preferidos
            time_counts = {}
            for appointment in appointments:
                time_slot = appointment.start_time.strftime("%H:00")
                time_counts[time_slot] = time_counts.get(time_slot, 0) + 1
            
            preferred_times = [
                time for time, count in sorted(time_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]
            
            # Calcular média de dias entre agendamentos
            if len(appointments) > 1:
                days_between = []
                for i in range(1, len(appointments)):
                    days = (appointments[i-1].start_time - appointments[i].start_time).days
                    days_between.append(days)
                average_days_between = sum(days_between) / len(days_between) if days_between else 0
            else:
                average_days_between = 0
            
            return ClientHistory(
                client_id=client_id,
                appointments=[{
                    "id": a.id,
                    "service_name": a.service.name if a.service else "Serviço não encontrado",
                    "start_time": a.start_time,
                    "status": a.status.value,
                    "notes": a.notes
                } for a in appointments],
                total_appointments=total_appointments,
                completed_appointments=completed_appointments,
                cancelled_appointments=cancelled_appointments,
                no_show_appointments=no_show_appointments,
                first_appointment=appointments[-1].start_time if appointments else None,
                last_appointment=appointments[0].start_time if appointments else None,
                average_days_between=average_days_between,
                preferred_services=preferred_services,
                preferred_days=preferred_days,
                preferred_times=preferred_times
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter histórico do cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def get_client_analytics(self, client_id: UUID, current_user: User) -> ClientAnalytics:
        """Obter analytics avançados do cliente"""
        try:
            client = await self.get_client(client_id, current_user)
            
            # Lifetime Value (simplificado)
            lifetime_value = client.total_spent
            
            # Taxa de retenção (baseada em agendamentos nos últimos 6 meses)
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            recent_appointments = self.db.query(Appointment).filter(
                Appointment.client_id == client_id,
                Appointment.user_id == current_user.id,
                Appointment.start_time >= six_months_ago
            ).count()
            
            retention_rate = (recent_appointments / max(client.total_appointments, 1)) * 100
            
            # Risco de churn
            days_since_last = client.days_since_last_appointment
            if days_since_last > 90:
                churn_risk = "high"
            elif days_since_last > 30:
                churn_risk = "medium"
            else:
                churn_risk = "low"
            
            # Predição do próximo agendamento (simplificada)
            if client.average_days_between_appointments > 0:
                next_appointment_prediction = datetime.utcnow() + timedelta(
                    days=client.average_days_between_appointments
                )
            else:
                next_appointment_prediction = None
            
            # Serviços recomendados (baseado em histórico)
            service_counts = {}
            appointments = self.db.query(Appointment).filter(
                Appointment.client_id == client_id,
                Appointment.user_id == current_user.id
            ).all()
            
            for appointment in appointments:
                if appointment.service:
                    service_name = appointment.service.name
                    service_counts[service_name] = service_counts.get(service_name, 0) + 1
            
            recommended_services = [
                {"name": name, "frequency": count}
                for name, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]
            
            return ClientAnalytics(
                client_id=client_id,
                lifetime_value=lifetime_value,
                retention_rate=retention_rate,
                churn_risk=churn_risk,
                next_appointment_prediction=next_appointment_prediction,
                recommended_services=recommended_services,
                communication_effectiveness={
                    "whatsapp_response_rate": 85.0,  # Placeholder
                    "email_response_rate": 45.0,    # Placeholder
                    "preferred_channel": client.communication_preference
                },
                seasonal_patterns={
                    "busiest_month": "Dezembro",  # Placeholder
                    "quietest_month": "Janeiro",  # Placeholder
                    "seasonal_trend": "Crescente"  # Placeholder
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter analytics do cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def get_client_stats(self, current_user: User) -> Dict[str, Any]:
        """Obter estatísticas de clientes"""
        try:
            # Estatísticas básicas
            total_clients = self.db.query(Client).filter(Client.user_id == current_user.id).count()
            active_clients = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.is_active == True
            ).count()
            
            # Novos clientes este mês
            this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_clients_this_month = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.created_at >= this_month
            ).count()
            
            # Clientes regulares e frequentes
            regular_clients = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.total_appointments >= 3
            ).count()
            
            frequent_clients = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.frequency_score >= 50.0
            ).count()
            
            vip_clients = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.is_vip == True
            ).count()
            
            # Média de agendamentos por cliente
            avg_appointments = self.db.query(func.avg(Client.total_appointments)).filter(
                Client.user_id == current_user.id
            ).scalar() or 0
            
            # Média de score de frequência
            avg_frequency_score = self.db.query(func.avg(Client.frequency_score)).filter(
                Client.user_id == current_user.id
            ).scalar() or 0
            
            # Top serviços
            top_services_query = self.db.query(
                Service.name, func.count(Appointment.id)
            ).join(Appointment, Service.id == Appointment.service_id).filter(
                Appointment.user_id == current_user.id
            ).group_by(Service.name).order_by(desc(func.count(Appointment.id))).limit(5).all()
            
            top_services = [{"name": name, "count": count} for name, count in top_services_query]
            
            # Clientes por fonte
            clients_by_source_query = self.db.query(
                Client.source, func.count(Client.id)
            ).filter(
                Client.user_id == current_user.id,
                Client.source.isnot(None)
            ).group_by(Client.source).all()
            
            clients_by_source = {source: count for source, count in clients_by_source_query}
            
            # Clientes por cidade
            clients_by_city_query = self.db.query(
                Client.city, func.count(Client.id)
            ).filter(
                Client.user_id == current_user.id,
                Client.city.isnot(None)
            ).group_by(Client.city).order_by(desc(func.count(Client.id))).limit(10).all()
            
            clients_by_city = {city: count for city, count in clients_by_city_query}
            
            # Clientes por gênero
            clients_by_gender_query = self.db.query(
                Client.gender, func.count(Client.id)
            ).filter(
                Client.user_id == current_user.id,
                Client.gender.isnot(None)
            ).group_by(Client.gender).all()
            
            clients_by_gender = {gender: count for gender, count in clients_by_gender_query}
            
            # Taxa de no-show e conclusão
            total_appointments = self.db.query(func.sum(Client.total_appointments)).filter(
                Client.user_id == current_user.id
            ).scalar() or 0
            
            total_no_shows = self.db.query(func.sum(Client.no_show_appointments)).filter(
                Client.user_id == current_user.id
            ).scalar() or 0
            
            total_completed = self.db.query(func.sum(Client.completed_appointments)).filter(
                Client.user_id == current_user.id
            ).scalar() or 0
            
            no_show_rate = (total_no_shows / total_appointments * 100) if total_appointments > 0 else 0
            completion_rate = (total_completed / total_appointments * 100) if total_appointments > 0 else 0
            
            return {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "new_clients_this_month": new_clients_this_month,
                "regular_clients": regular_clients,
                "frequent_clients": frequent_clients,
                "vip_clients": vip_clients,
                "average_appointments_per_client": float(avg_appointments),
                "average_frequency_score": float(avg_frequency_score),
                "top_services": top_services,
                "clients_by_source": clients_by_source,
                "clients_by_city": clients_by_city,
                "clients_by_gender": clients_by_gender,
                "no_show_rate": float(no_show_rate),
                "completion_rate": float(completion_rate)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de clientes: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def bulk_update_clients(self, bulk_data: ClientBulkUpdate, current_user: User):
        """Atualização em massa de clientes"""
        try:
            clients = self.db.query(Client).filter(
                Client.id.in_(bulk_data.client_ids),
                Client.user_id == current_user.id
            ).all()
            
            if not clients:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nenhum cliente encontrado"
                )
            
            update_data = bulk_data.model_dump(exclude_unset=True, exclude={"client_ids"})
            
            for client in clients:
                for key, value in update_data.items():
                    setattr(client, key, value)
                client.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Atualização em massa realizada em {len(clients)} clientes - usuário {current_user.email}")
            return {"message": f"{len(clients)} clientes atualizados com sucesso"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro na atualização em massa: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def find_or_create_client(
        self, 
        name: str, 
        whatsapp: str, 
        email: str = None, 
        current_user: User = None
    ) -> Client:
        """Encontrar cliente existente ou criar novo (usado em agendamentos)"""
        try:
            # Buscar cliente existente
            client = self.db.query(Client).filter(
                Client.user_id == current_user.id,
                Client.whatsapp == whatsapp
            ).first()
            
            if client:
                # Atualizar nome se necessário
                if name != client.name:
                    client.name = name
                    client.updated_at = datetime.utcnow()
                    self.db.commit()
                return client
            
            # Criar novo cliente
            new_client = Client(
                user_id=current_user.id,
                name=name,
                whatsapp=whatsapp,
                email=email,
                source="agendamento"
            )
            
            self.db.add(new_client)
            self.db.commit()
            self.db.refresh(new_client)
            
            logger.info(f"Cliente criado automaticamente: {new_client.name} - usuário {current_user.email}")
            return new_client
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao encontrar/criar cliente: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )
    
    async def update_client_metrics(self, client_id: UUID, current_user: User):
        """Atualiza métricas do cliente baseado nos agendamentos"""
        try:
            client = await self.get_client(client_id, current_user)
            
            # Buscar todos os agendamentos do cliente
            appointments = self.db.query(Appointment).filter(
                Appointment.client_id == client_id,
                Appointment.user_id == current_user.id
            ).all()
            
            # Calcular métricas básicas
            total_appointments = len(appointments)
            completed_appointments = len([a for a in appointments if a.status == AppointmentStatus.COMPLETED])
            cancelled_appointments = len([a for a in appointments if a.status == AppointmentStatus.CANCELLED])
            no_show_appointments = len([a for a in appointments if a.status == AppointmentStatus.NO_SHOW])
            
            # Calcular datas importantes
            if appointments:
                first_appointment = min(appointments, key=lambda x: x.start_time)
                last_appointment = max(appointments, key=lambda x: x.start_time)
                client.first_appointment_at = first_appointment.start_time
                client.last_appointment_at = last_appointment.start_time
            else:
                client.first_appointment_at = None
                client.last_appointment_at = None
            
            # Calcular frequência mensal
            now = datetime.utcnow()
            this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
            
            appointments_this_month = len([
                a for a in appointments 
                if a.start_time >= this_month_start and a.status == AppointmentStatus.COMPLETED
            ])
            
            appointments_last_month = len([
                a for a in appointments 
                if a.start_time >= last_month_start and a.start_time < this_month_start and a.status == AppointmentStatus.COMPLETED
            ])
            
            # Calcular score de frequência (0-100)
            if total_appointments > 0:
                # Baseado na frequência mensal e taxa de conclusão
                completion_rate = completed_appointments / total_appointments if total_appointments > 0 else 0
                monthly_frequency = appointments_this_month
                frequency_score = min(100, (completion_rate * 50) + (monthly_frequency * 10))
            else:
                frequency_score = 0.0
            
            # Calcular dias médios entre agendamentos
            if completed_appointments > 1:
                completed_appointments_sorted = sorted([
                    a for a in appointments if a.status == AppointmentStatus.COMPLETED
                ], key=lambda x: x.start_time)
                
                total_days = 0
                for i in range(1, len(completed_appointments_sorted)):
                    days_diff = (completed_appointments_sorted[i].start_time - completed_appointments_sorted[i-1].start_time).days
                    total_days += days_diff
                
                average_days = total_days / (len(completed_appointments_sorted) - 1)
            else:
                average_days = 0.0
            
            # Atualizar campos do cliente
            client.total_appointments = total_appointments
            client.completed_appointments = completed_appointments
            client.cancelled_appointments = cancelled_appointments
            client.no_show_appointments = no_show_appointments
            client.frequency_score = frequency_score
            client.appointments_this_month = appointments_this_month
            client.appointments_last_month = appointments_last_month
            client.average_days_between_appointments = average_days
            
            # Atualizar flags de status
            client.is_regular_customer = total_appointments >= 3
            client.is_frequent_customer = appointments_this_month >= 1
            
            # Calcular dias desde último agendamento
            if client.last_appointment_at:
                client.days_since_last_appointment = (now - client.last_appointment_at).days
            else:
                client.days_since_last_appointment = None
            
            # Calcular lifetime do cliente
            if client.first_appointment_at:
                client.customer_lifetime_days = (now - client.first_appointment_at).days
            else:
                client.customer_lifetime_days = None
            
            # Calcular taxas
            client.no_show_rate = (no_show_appointments / total_appointments * 100) if total_appointments > 0 else 0
            client.completion_rate = (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0
            
            client.updated_at = datetime.utcnow()
            
            self.db.add(client)
            self.db.commit()
            self.db.refresh(client)
            
            logger.info(f"Métricas atualizadas para cliente {client.name}: {total_appointments} agendamentos, score {frequency_score:.1f}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar métricas do cliente {client_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno do servidor"
            )

