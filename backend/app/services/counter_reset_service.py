"""
Serviço para reset automático de contadores mensais
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class CounterResetService:
    """Serviço para reset automático de contadores"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.running = False
        self.task = None
    
    async def start_monthly_reset_scheduler(self):
        """Iniciar agendador de reset mensal"""
        if not self.redis:
            logger.warning("Redis não disponível, reset automático não será executado")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monthly_reset_loop())
        logger.info("🔄 Agendador de reset mensal iniciado")
    
    async def stop_monthly_reset_scheduler(self):
        """Parar agendador de reset mensal"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Agendador de reset mensal parado")
    
    async def _monthly_reset_loop(self):
        """Loop principal do reset mensal"""
        while self.running:
            try:
                # Calcular próximo reset (primeiro dia do próximo mês às 00:00)
                now = datetime.now()
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Calcular tempo até o próximo reset
                time_until_reset = (next_month - now).total_seconds()
                
                logger.info(f"⏰ Próximo reset agendado para: {next_month}")
                
                # Aguardar até o próximo reset
                await asyncio.sleep(time_until_reset)
                
                if self.running:
                    await self._execute_monthly_reset()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop de reset mensal: {e}")
                await asyncio.sleep(3600)  # Aguardar 1 hora antes de tentar novamente
    
    async def _execute_monthly_reset(self):
        """Executar reset mensal dos contadores"""
        try:
            logger.info("🔄 Iniciando reset mensal dos contadores...")
            
            # Resetar contadores de agendamentos
            appointments_pattern = "usage:*:appointments:*"
            appointments_keys = await self.redis.keys(appointments_pattern)
            
            if appointments_keys:
                await self.redis.delete(*appointments_keys)
                logger.info(f"✅ {len(appointments_keys)} contadores de agendamentos resetados")
            
            # Resetar contadores de mensagens
            messages_pattern = "usage:*:messages:*"
            messages_keys = await self.redis.keys(messages_pattern)
            
            if messages_keys:
                await self.redis.delete(*messages_keys)
                logger.info(f"✅ {len(messages_keys)} contadores de mensagens resetados")
            
            # Resetar contadores de cache de agenda
            agenda_pattern = "agenda:*:*"
            agenda_keys = await self.redis.keys(agenda_pattern)
            
            if agenda_keys:
                await self.redis.delete(*agenda_keys)
                logger.info(f"✅ {len(agenda_keys)} caches de agenda resetados")
            
            # Registrar reset no log
            reset_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "appointments_reset": len(appointments_keys),
                "messages_reset": len(messages_keys),
                "agenda_cache_reset": len(agenda_keys)
            }
            
            await self.redis.lpush("system:monthly_resets", str(reset_log))
            await self.redis.ltrim("system:monthly_resets", 0, 11)  # Manter apenas 12 registros
            
            logger.info("🎉 Reset mensal concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao executar reset mensal: {e}")
    
    async def force_monthly_reset(self):
        """Forçar reset mensal (para testes ou correção)"""
        if not self.redis:
            logger.warning("Redis não disponível, não é possível executar reset")
            return False
        
        try:
            await self._execute_monthly_reset()
            return True
        except Exception as e:
            logger.error(f"Erro ao forçar reset mensal: {e}")
            return False
    
    async def get_reset_history(self, limit: int = 10) -> list:
        """Obter histórico de resets"""
        if not self.redis:
            return []
        
        try:
            history = await self.redis.lrange("system:monthly_resets", 0, limit - 1)
            return [eval(entry) for entry in history]  # Converter strings de volta para dict
        except Exception as e:
            logger.error(f"Erro ao obter histórico de resets: {e}")
            return []
    
    async def get_current_usage_stats(self) -> dict:
        """Obter estatísticas atuais de uso"""
        if not self.redis:
            return {}
        
        try:
            stats = {}
            
            # Contar chaves de uso ativas
            appointments_pattern = "usage:*:appointments:*"
            messages_pattern = "usage:*:messages:*"
            services_pattern = "usage:*:services"
            
            appointments_count = len(await self.redis.keys(appointments_pattern))
            messages_count = len(await self.redis.keys(messages_pattern))
            services_count = len(await self.redis.keys(services_pattern))
            
            stats = {
                "active_appointment_counters": appointments_count,
                "active_message_counters": messages_count,
                "active_service_counters": services_count,
                "total_active_counters": appointments_count + messages_count + services_count
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de uso: {e}")
            return {}


# Instância global do serviço
counter_reset_service = CounterResetService()
