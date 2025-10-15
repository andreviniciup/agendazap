"""
BotMetrics - Sistema de métricas e monitoramento do bot
Rastreia performance, taxa de sucesso e comportamento
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class BotMetrics:
    """Sistema de métricas para monitorar performance do bot"""
    
    def __init__(self, redis_client=None):
        """
        Args:
            redis_client: Cliente Redis (opcional) para persistência
        """
        self.redis = redis_client
        
        # Métricas em memória
        self._metrics = {
            "total_messages": 0,
            "total_intents": {},
            "total_errors": 0,
            "confidence_sum": 0.0,
            "successful_appointments": 0,
            "failed_appointments": 0,
            "handoffs_to_human": 0,
            "handoff_reasons": {},
            "media_detected": 0,
            "media_types": {},
            "confirmations_sent": 0,
            "confirmations_yes": 0,
            "confirmations_no": 0,
            "feedbacks_received": 0,
            "average_turns_per_appointment": 0.0,
            "intents_by_source": {
                "rule": 0,
                "ml": 0,
                "context": 0,
            },
            "last_reset": datetime.utcnow().isoformat(),
        }
    
    async def record_message(
        self, 
        intent: str, 
        confidence: float, 
        source: str = "rule",
        metadata: Optional[Dict] = None
    ):
        """
        Registrar métrica de mensagem processada
        
        Args:
            intent: Intenção detectada
            confidence: Confiança (0-1)
            source: Fonte da detecção ('rule', 'ml', 'context')
            metadata: Dados adicionais
        """
        self._metrics["total_messages"] += 1
        
        # Contabilizar por intent
        if intent not in self._metrics["total_intents"]:
            self._metrics["total_intents"][intent] = 0
        self._metrics["total_intents"][intent] += 1
        
        # Contabilizar por fonte
        if source in self._metrics["intents_by_source"]:
            self._metrics["intents_by_source"][source] += 1
        
        # Atualizar confiança média (running average)
        self._metrics["confidence_sum"] += confidence
        
        # Persistir no Redis se disponível
        await self._persist()
        
        logger.debug(f"📊 Mensagem registrada - Intent: {intent}, Conf: {confidence:.2%}, Source: {source}")
    
    async def record_error(self, error_type: str = "generic", details: Optional[str] = None):
        """Registrar erro do bot"""
        self._metrics["total_errors"] += 1
        
        # Persistir
        await self._persist()
        
        logger.warning(f"❌ Erro registrado - Tipo: {error_type}, Detalhes: {details}")
    
    async def record_appointment_created(self, turns_count: int = 1):
        """
        Registrar agendamento criado com sucesso
        
        Args:
            turns_count: Número de turnos até criar o agendamento
        """
        self._metrics["successful_appointments"] += 1
        
        # Atualizar média de turnos (running average)
        total = self._metrics["successful_appointments"]
        current_avg = self._metrics["average_turns_per_appointment"]
        self._metrics["average_turns_per_appointment"] = (
            (current_avg * (total - 1) + turns_count) / total
        )
        
        await self._persist()
        
        logger.info(f"✅ Agendamento criado - Turnos: {turns_count}, Média: {self._metrics['average_turns_per_appointment']:.1f}")
    
    async def record_appointment_failed(self):
        """Registrar tentativa de agendamento que falhou"""
        self._metrics["failed_appointments"] += 1
        await self._persist()
        logger.warning(f"❌ Agendamento falhou")
    
    async def record_handoff_to_human(self, reason: str = "generic"):
        """
        Registrar transferência para atendente humano
        
        Args:
            reason: Razão do handoff (human_requested, media, low_confidence, etc)
        """
        self._metrics["handoffs_to_human"] += 1
        
        # Contabilizar por razão
        if reason not in self._metrics["handoff_reasons"]:
            self._metrics["handoff_reasons"][reason] = 0
        self._metrics["handoff_reasons"][reason] += 1
        
        await self._persist()
        logger.info(f"🤝 Transferência para humano registrada - Razão: {reason}")
    
    async def record_media_detected(self, media_type: str):
        """
        Registrar mídia detectada
        
        Args:
            media_type: Tipo de mídia (audio, image, video, document)
        """
        self._metrics["media_detected"] += 1
        
        # Contabilizar por tipo
        if media_type not in self._metrics["media_types"]:
            self._metrics["media_types"][media_type] = 0
        self._metrics["media_types"][media_type] += 1
        
        await self._persist()
        logger.info(f"📎 Mídia detectada - Tipo: {media_type}")
    
    async def record_confirmation_sent(self):
        """Registrar confirmação enviada"""
        self._metrics["confirmations_sent"] += 1
        await self._persist()
        logger.info(f"✉️ Confirmação enviada")
    
    async def record_confirmation_response(self, confirmed: bool):
        """
        Registrar resposta de confirmação
        
        Args:
            confirmed: True se confirmou, False se cancelou
        """
        if confirmed:
            self._metrics["confirmations_yes"] += 1
        else:
            self._metrics["confirmations_no"] += 1
        
        await self._persist()
        logger.info(f"{'✅' if confirmed else '❌'} Confirmação: {'Sim' if confirmed else 'Não'}")
    
    async def record_feedback_received(self):
        """Registrar feedback recebido"""
        self._metrics["feedbacks_received"] += 1
        await self._persist()
        logger.info(f"💬 Feedback recebido")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retornar estatísticas consolidadas
        
        Returns:
            Dict com todas as métricas
        """
        total_msgs = max(1, self._metrics["total_messages"])
        total_confirmations = max(1, self._metrics["confirmations_sent"])
        
        return {
            "total_messages": self._metrics["total_messages"],
            "total_intents": self._metrics["total_intents"],
            "total_errors": self._metrics["total_errors"],
            "average_confidence": round(
                self._metrics["confidence_sum"] / total_msgs, 
                3
            ),
            "successful_appointments": self._metrics["successful_appointments"],
            "failed_appointments": self._metrics["failed_appointments"],
            "handoffs_to_human": self._metrics["handoffs_to_human"],
            "handoff_reasons": self._metrics["handoff_reasons"],
            "media_detected": self._metrics["media_detected"],
            "media_types": self._metrics["media_types"],
            "confirmations_sent": self._metrics["confirmations_sent"],
            "confirmations_yes": self._metrics["confirmations_yes"],
            "confirmations_no": self._metrics["confirmations_no"],
            "confirmation_rate": round(
                (self._metrics["confirmations_yes"] / total_confirmations) * 100,
                2
            ),
            "feedbacks_received": self._metrics["feedbacks_received"],
            "average_turns_per_appointment": round(
                self._metrics["average_turns_per_appointment"], 
                1
            ),
            "error_rate": round(
                (self._metrics["total_errors"] / total_msgs) * 100, 
                2
            ),
            "success_rate": round(
                (self._metrics["successful_appointments"] / max(1, self._metrics["successful_appointments"] + self._metrics["failed_appointments"])) * 100,
                2
            ),
            "intents_by_source": self._metrics["intents_by_source"],
            "last_reset": self._metrics["last_reset"],
        }
    
    async def reset_stats(self):
        """Resetar todas as métricas (útil para períodos)"""
        self._metrics = {
            "total_messages": 0,
            "total_intents": {},
            "total_errors": 0,
            "confidence_sum": 0.0,
            "successful_appointments": 0,
            "failed_appointments": 0,
            "handoffs_to_human": 0,
            "handoff_reasons": {},
            "media_detected": 0,
            "media_types": {},
            "confirmations_sent": 0,
            "confirmations_yes": 0,
            "confirmations_no": 0,
            "feedbacks_received": 0,
            "average_turns_per_appointment": 0.0,
            "intents_by_source": {
                "rule": 0,
                "ml": 0,
                "context": 0,
            },
            "last_reset": datetime.utcnow().isoformat(),
        }
        
        await self._persist()
        logger.info("🔄 Métricas resetadas")
    
    async def _persist(self):
        """Persistir métricas no Redis se disponível"""
        if not self.redis:
            return
        
        try:
            key = "bot:metrics:current"
            value = json.dumps(self._metrics)
            await self.redis.set(key, value)
            # Expirar em 7 dias
            await self.redis.expire(key, 7 * 24 * 3600)
        except Exception as e:
            logger.warning(f"⚠️ Falha ao persistir métricas: {e}")
    
    async def load_from_redis(self):
        """Carregar métricas persistidas do Redis"""
        if not self.redis:
            return
        
        try:
            key = "bot:metrics:current"
            value = await self.redis.get(key)
            
            if value:
                self._metrics = json.loads(value)
                logger.info(f"📊 Métricas carregadas do Redis: {self._metrics['total_messages']} mensagens")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao carregar métricas: {e}")
    
    def get_top_intents(self, limit: int = 5) -> list:
        """Retornar top N intenções mais comuns"""
        intents = self._metrics["total_intents"]
        sorted_intents = sorted(
            intents.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        return sorted_intents[:limit]
    
    def get_ml_usage_percentage(self) -> float:
        """Calcular % de mensagens que usaram ML"""
        total = sum(self._metrics["intents_by_source"].values())
        if total == 0:
            return 0.0
        
        ml_count = self._metrics["intents_by_source"].get("ml", 0)
        return round((ml_count / total) * 100, 2)
    
    def __str__(self) -> str:
        """Representação amigável das métricas"""
        stats = self.get_stats()
        return (
            f"BotMetrics:\n"
            f"  Mensagens: {stats['total_messages']}\n"
            f"  Confiança média: {stats['average_confidence']:.1%}\n"
            f"  Taxa de erro: {stats['error_rate']:.1f}%\n"
            f"  Agendamentos: {stats['successful_appointments']} sucesso, {stats['failed_appointments']} falhas\n"
            f"  Taxa de sucesso: {stats['success_rate']:.1f}%\n"
            f"  Uso de ML: {self.get_ml_usage_percentage():.1f}%\n"
            f"  Top intents: {', '.join(f'{k}({v})' for k, v in self.get_top_intents(3))}"
        )



