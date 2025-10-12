"""
Serviço de Cache Warming Automático
Pré-aquece cache para usuários ativos
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.database import SessionLocal
from app.models.user import User
from app.models.appointment import Appointment
from app.services.cache_service import cache_service
from app.services.appointment_service import AppointmentService
from app.services.service_service import ServiceService
from app.services.plan_service import PlanService

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """Serviço para aquecimento automático de cache"""
    
    def __init__(self):
        self.is_running = False
        self.warming_interval = 300  # 5 minutos
    
    async def start_warming_service(self):
        """Iniciar serviço de aquecimento automático"""
        if self.is_running:
            logger.warning("Serviço de cache warming já está rodando")
            return
        
        self.is_running = True
        logger.info("🚀 Serviço de cache warming iniciado")
        
        while self.is_running:
            try:
                await self.warm_active_users_cache()
                await asyncio.sleep(self.warming_interval)
            except Exception as e:
                logger.error(f"Erro no serviço de cache warming: {e}")
                await asyncio.sleep(60)  # Aguardar 1 minuto em caso de erro
    
    def stop_warming_service(self):
        """Parar serviço de aquecimento automático"""
        self.is_running = False
        logger.info("🛑 Serviço de cache warming parado")
    
    async def warm_active_users_cache(self):
        """Aquecer cache para usuários ativos"""
        try:
            db = SessionLocal()
            try:
                # Buscar usuários ativos (com agendamentos recentes ou futuros)
                active_users = self._get_active_users(db)
                
                logger.info(f"🔥 Aquecendo cache para {len(active_users)} usuários ativos")
                
                for user in active_users:
                    try:
                        await self._warm_user_cache(user, db)
                    except Exception as e:
                        logger.error(f"Erro ao aquecer cache do usuário {user.id}: {e}")
                        continue
                
                logger.info(f"✅ Cache aquecido para {len(active_users)} usuários")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erro ao aquecer cache de usuários ativos: {e}")
    
    def _get_active_users(self, db: Session) -> List[User]:
        """Obter usuários ativos baseado em agendamentos recentes"""
        try:
            # Buscar usuários com agendamentos nos últimos 7 dias ou próximos 30 dias
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            thirty_days_future = datetime.utcnow() + timedelta(days=30)
            
            active_user_ids = db.query(Appointment.user_id).filter(
                and_(
                    Appointment.start_time >= seven_days_ago,
                    Appointment.start_time <= thirty_days_future,
                    Appointment.is_cancelled == False
                )
            ).distinct().all()
            
            # Buscar usuários
            user_ids = [user_id[0] for user_id in active_user_ids]
            if not user_ids:
                return []
            
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return users
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuários ativos: {e}")
            return []
    
    async def _warm_user_cache(self, user: User, db: Session):
        """Aquecer cache de um usuário específico"""
        try:
            plan_service = PlanService()
            appointment_service = AppointmentService(db, plan_service)
            service_service = ServiceService(db, plan_service)
            
            # Aquecer cache de serviços
            services_data = service_service.get_user_services(user, use_cache=False)
            
            # Aquecer cache de agenda para próximos 7 dias
            agenda_data = {}
            today = date.today()
            
            for i in range(7):
                target_date = today + timedelta(days=i)
                try:
                    agenda = appointment_service.get_user_agenda(user, target_date, use_cache=False)
                    agenda_data[target_date.isoformat()] = agenda
                except Exception as e:
                    logger.warning(f"Erro ao obter agenda para {target_date}: {e}")
                    agenda_data[target_date.isoformat()] = {
                        "date": target_date.isoformat(),
                        "appointments": [],
                        "total_appointments": 0,
                        "available_slots": []
                    }
            
            # Aquecer cache usando o serviço de cache
            success = cache_service.warm_user_cache(
                user.id, 
                agenda_data, 
                services_data
            )
            
            if success:
                logger.debug(f"Cache aquecido para usuário {user.id}")
            else:
                logger.warning(f"Falha ao aquecer cache para usuário {user.id}")
                
        except Exception as e:
            logger.error(f"Erro ao aquecer cache do usuário {user.id}: {e}")
    
    async def warm_specific_user_cache(self, user_id: str) -> bool:
        """Aquecer cache de um usuário específico por ID"""
        try:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.warning(f"Usuário {user_id} não encontrado")
                    return False
                
                await self._warm_user_cache(user, db)
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erro ao aquecer cache do usuário {user_id}: {e}")
            return False
    
    async def warm_high_priority_users(self):
        """Aquecer cache para usuários de alta prioridade (planos pagos)"""
        try:
            db = SessionLocal()
            try:
                # Buscar usuários com planos pagos
                high_priority_users = db.query(User).filter(
                    User.plan_type.in_(['starter', 'pro', 'enterprise'])
                ).all()
                
                logger.info(f"🔥 Aquecendo cache para {len(high_priority_users)} usuários de alta prioridade")
                
                for user in high_priority_users:
                    try:
                        await self._warm_user_cache(user, db)
                    except Exception as e:
                        logger.error(f"Erro ao aquecer cache do usuário {user.id}: {e}")
                        continue
                
                logger.info(f"✅ Cache aquecido para {len(high_priority_users)} usuários de alta prioridade")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erro ao aquecer cache de usuários de alta prioridade: {e}")
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do serviço de warming"""
        return {
            "is_running": self.is_running,
            "warming_interval": self.warming_interval,
            "cache_metrics": cache_service.get_metrics(),
            "cache_info": cache_service.get_cache_info()
        }


# Instância global do serviço de warming
cache_warming_service = CacheWarmingService()


async def start_cache_warming():
    """Função para iniciar o serviço de warming"""
    await cache_warming_service.start_warming_service()


def stop_cache_warming():
    """Função para parar o serviço de warming"""
    cache_warming_service.stop_warming_service()



