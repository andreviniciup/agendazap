"""
Serviço de Cache Inteligente para AgendaZap
Implementa cache Redis com TTL, invalidação automática e métricas
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError, ConnectionError

from app.config import settings, get_redis_url

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Métricas de performance do cache"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_requests = 0
        self.start_time = time.time()
    
    def record_hit(self):
        """Registra um cache hit"""
        self.hits += 1
        self.total_requests += 1
    
    def record_miss(self):
        """Registra um cache miss"""
        self.misses += 1
        self.total_requests += 1
    
    def record_error(self):
        """Registra um erro de cache"""
        self.errors += 1
        self.total_requests += 1
    
    @property
    def hit_rate(self) -> float:
        """Taxa de acerto do cache"""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100
    
    @property
    def uptime(self) -> float:
        """Tempo de funcionamento em segundos"""
        return time.time() - self.start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas completas"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
            "uptime_seconds": self.uptime
        }


class CacheService:
    """Serviço de cache inteligente com Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.metrics = CacheMetrics()
        self._connect()
    
    def _connect(self):
        """Conecta ao Redis"""
        try:
            redis_url = get_redis_url()
            self.redis_client = redis.from_url(
                redis_url,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Testar conexão
            self.redis_client.ping()
            logger.info("✅ Conexão com Redis estabelecida")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis não disponível: {e}")
            logger.info("💡 Cache funcionará em modo fallback (sem cache)")
            self.redis_client = None
    
    def _is_connected(self) -> bool:
        """Verifica se está conectado ao Redis"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _serialize(self, data: Any) -> str:
        """Serializa dados para JSON"""
        try:
            return json.dumps(data, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao serializar dados: {e}")
            raise
    
    def _deserialize(self, data: str) -> Any:
        """Deserializa dados do JSON"""
        try:
            return json.loads(data)
        except Exception as e:
            logger.error(f"Erro ao deserializar dados: {e}")
            raise
    
    def _get_key(self, prefix: str, user_id: int, *args) -> str:
        """Gera chave de cache padronizada"""
        key_parts = [prefix, str(user_id)] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache com fallback automático"""
        if not self._is_connected():
            self.metrics.record_error()
            logger.warning(f"Redis não conectado - fallback para banco de dados para chave: {key}")
            return None
        
        try:
            data = self.redis_client.get(key)
            if data is not None:
                self.metrics.record_hit()
                logger.debug(f"Cache HIT para chave: {key}")
                return self._deserialize(data)
            else:
                self.metrics.record_miss()
                logger.debug(f"Cache MISS para chave: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter cache para chave {key}: {e}")
            self.metrics.record_error()
            logger.warning(f"Fallback para banco de dados devido a erro no cache para chave: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Define valor no cache com TTL opcional"""
        if not self._is_connected():
            self.metrics.record_error()
            return False
        
        try:
            serialized_data = self._serialize(value)
            
            if ttl:
                result = self.redis_client.setex(key, ttl, serialized_data)
            else:
                result = self.redis_client.set(key, serialized_data)
            
            if result:
                logger.debug(f"Cache SET para chave: {key} (TTL: {ttl})")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Erro ao definir cache para chave {key}: {e}")
            self.metrics.record_error()
            return False
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        if not self._is_connected():
            return False
        
        try:
            result = self.redis_client.delete(key)
            if result:
                logger.debug(f"Cache DELETE para chave: {key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Erro ao deletar cache para chave {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        if not self._is_connected():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                result = self.redis_client.delete(*keys)
                logger.debug(f"Cache DELETE PATTERN: {pattern} ({result} chaves removidas)")
                return result
            return 0
            
        except Exception as e:
            logger.error(f"Erro ao deletar cache por padrão {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        if not self._is_connected():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Erro ao verificar existência da chave {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Retorna TTL restante da chave em segundos"""
        if not self._is_connected():
            return -1
        
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Erro ao obter TTL da chave {key}: {e}")
            return -1
    
    def extend_ttl(self, key: str, ttl: int) -> bool:
        """Estende TTL de uma chave existente"""
        if not self._is_connected():
            return False
        
        try:
            result = self.redis_client.expire(key, ttl)
            if result:
                logger.debug(f"Cache TTL estendido para chave: {key} (TTL: {ttl})")
            return bool(result)
        except Exception as e:
            logger.error(f"Erro ao estender TTL da chave {key}: {e}")
            return False
    
    # Métodos específicos para diferentes tipos de cache
    
    def get_user_agenda(self, user_id: int, date: str) -> Optional[Dict]:
        """Obtém agenda do usuário do cache"""
        key = self._get_key("agenda", user_id, date)
        return self.get(key)
    
    def set_user_agenda(self, user_id: int, date: str, agenda_data: Dict) -> bool:
        """Define agenda do usuário no cache"""
        key = self._get_key("agenda", user_id, date)
        return self.set(key, agenda_data, settings.CACHE_TTL_AGENDA)
    
    def get_user_services(self, user_id: int) -> Optional[List[Dict]]:
        """Obtém serviços do usuário do cache"""
        key = self._get_key("services", user_id)
        return self.get(key)
    
    def set_user_services(self, user_id: int, services_data: List[Dict]) -> bool:
        """Define serviços do usuário no cache"""
        key = self._get_key("services", user_id)
        return self.set(key, services_data, settings.CACHE_TTL_SERVICES)
    
    def get_message_template(self, template_id: str) -> Optional[Dict]:
        """Obtém template de mensagem do cache"""
        key = self._get_key("template", template_id)
        return self.get(key)
    
    def set_message_template(self, template_id: str, template_data: Dict) -> bool:
        """Define template de mensagem no cache"""
        key = self._get_key("template", template_id)
        return self.set(key, template_data, settings.CACHE_TTL_TEMPLATES)
    
    # Métodos de invalidação
    
    def invalidate_user_agenda(self, user_id: int, date: Optional[str] = None) -> int:
        """Invalida cache de agenda do usuário"""
        if date:
            key = self._get_key("agenda", user_id, date)
            return 1 if self.delete(key) else 0
        else:
            pattern = self._get_key("agenda", user_id, "*")
            return self.delete_pattern(pattern)
    
    def invalidate_user_services(self, user_id: int) -> int:
        """Invalida cache de serviços do usuário"""
        key = self._get_key("services", user_id)
        return 1 if self.delete(key) else 0
    
    def invalidate_user_cache(self, user_id: int) -> int:
        """Invalida todo o cache do usuário"""
        pattern = f"*:{user_id}:*"
        return self.delete_pattern(pattern)
    
    def invalidate_template(self, template_id: str) -> int:
        """Invalida cache de template"""
        key = self._get_key("template", template_id)
        return 1 if self.delete(key) else 0
    
    # Métodos de cache warming
    
    def warm_user_cache(self, user_id: int, agenda_data: Dict, services_data: List[Dict]) -> bool:
        """Pré-aquece cache do usuário"""
        try:
            # Cache de serviços
            self.set_user_services(user_id, services_data)
            
            # Cache de agenda para próximos 7 dias
            today = datetime.now().date()
            for i in range(7):
                date = today + timedelta(days=i)
                date_str = date.isoformat()
                if date_str in agenda_data:
                    self.set_user_agenda(user_id, date_str, agenda_data[date_str])
            
            logger.info(f"Cache aquecido para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aquecer cache do usuário {user_id}: {e}")
            return False
    
    # Métodos de métricas e monitoramento
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do cache"""
        return self.metrics.get_stats()
    
    def reset_metrics(self):
        """Reseta métricas do cache"""
        self.metrics = CacheMetrics()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Retorna informações do cache Redis"""
        if not self._is_connected():
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_in_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do Redis: {e}")
            return {"connected": False, "error": str(e)}
    
    def is_cache_healthy(self) -> bool:
        """Verifica se o cache está saudável"""
        return self._is_connected()
    
    def get_fallback_status(self) -> Dict[str, Any]:
        """Retorna status do fallback"""
        return {
            "cache_healthy": self.is_cache_healthy(),
            "fallback_active": not self.is_cache_healthy(),
            "metrics": self.get_metrics(),
            "last_error": "Cache não conectado" if not self.is_cache_healthy() else None
        }
    
    def with_fallback(self, cache_func, fallback_func, *args, **kwargs):
        """Executa função de cache com fallback automático"""
        try:
            if self.is_cache_healthy():
                return cache_func(*args, **kwargs)
            else:
                logger.warning("Cache não disponível, usando fallback")
                return fallback_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erro na função de cache, usando fallback: {e}")
            return fallback_func(*args, **kwargs)


# Instância global do serviço de cache
cache_service = CacheService()
