"""
Gerenciamento de estado de conversa no Redis com timeout automático
"""

from typing import Optional, Dict, Any
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ConversationState:
    """
    Gerenciador de estado de conversa com suporte a:
    - Timeout automático (reset após inatividade)
    - Histórico de mensagens
    - Persistência em Redis
    """
    
    def __init__(
        self, 
        redis_client, 
        ttl_seconds: int = 24 * 3600,
        state_timeout_seconds: int = 5 * 60
    ) -> None:
        """
        Args:
            redis_client: Cliente Redis
            ttl_seconds: Tempo de vida total da conversa (padrão: 24h)
            state_timeout_seconds: Timeout para estados 'asking_*' (padrão: 5min)
        """
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.state_timeout = state_timeout_seconds

    def _key(self, wa_number: str) -> str:
        return f"conversation:{wa_number}"

    async def load(self, wa_number: str) -> Dict[str, Any]:
        """
        Carregar estado da conversa com validação de timeout
        
        Args:
            wa_number: Número do WhatsApp
            
        Returns:
            Estado da conversa (com reset automático se timeout)
        """
        raw = await self.redis.get(self._key(wa_number)) if self.redis else None
        
        if not raw:
            return self._default_state()
        
        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Estado corrompido para {wa_number}, resetando")
            return self._default_state()
        
        # Verificar timeout para estados de coleta (asking_*)
        current_state = state.get("state", "idle")
        
        if current_state.startswith("asking_") or current_state.startswith("need_"):
            last_update_str = state.get("last_update")
            
            if last_update_str:
                try:
                    last_update = datetime.fromisoformat(last_update_str)
                    time_diff = (datetime.utcnow() - last_update).total_seconds()
                    
                    if time_diff > self.state_timeout:
                        logger.info(
                            f"⏰ Timeout de conversa para {wa_number} "
                            f"(inativo por {int(time_diff/60)} minutos)"
                        )
                        # Reset para idle mas manter histórico
                        state["state"] = "idle"
                        state["slots"] = {}
                        state["fail_count"] = 0
                        state["timeout_occurred"] = True
                        state["timeout_at"] = datetime.utcnow().isoformat()
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Timestamp inválido, resetando estado")
                    state = self._default_state()
        
        return state

    async def save(self, wa_number: str, data: Dict[str, Any]) -> None:
        """
        Salvar estado da conversa com timestamp
        
        Args:
            wa_number: Número do WhatsApp
            data: Dados para salvar
        """
        if not self.redis:
            return
        
        # Adicionar timestamp de última atualização
        data["last_update"] = datetime.utcnow().isoformat()
        
        # Limitar histórico a últimos 10 turnos
        if "history" in data and len(data["history"]) > 10:
            data["history"] = data["history"][-10:]
        
        try:
            await self.redis.set(self._key(wa_number), json.dumps(data))
            await self.redis.expire(self._key(wa_number), self.ttl)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado: {e}")

    async def reset(self, wa_number: str) -> None:
        """
        Resetar completamente o estado da conversa
        
        Args:
            wa_number: Número do WhatsApp
        """
        if not self.redis:
            return
        
        try:
            await self.redis.delete(self._key(wa_number))
            logger.info(f"🔄 Estado resetado para {wa_number}")
        except Exception as e:
            logger.error(f"❌ Erro ao resetar estado: {e}")
    
    async def add_to_history(
        self, 
        wa_number: str, 
        intent: str, 
        confidence: float,
        text: str,
        response: str
    ) -> None:
        """
        Adicionar interação ao histórico
        
        Args:
            wa_number: Número do WhatsApp
            intent: Intenção detectada
            confidence: Confiança
            text: Texto do usuário
            response: Resposta do bot
        """
        state = await self.load(wa_number)
        
        if "history" not in state:
            state["history"] = []
        
        state["history"].append({
            "intent": intent,
            "confidence": confidence,
            "text": text[:100],  # Primeiros 100 caracteres
            "response": response[:100],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Manter apenas últimos 10 turnos
        state["history"] = state["history"][-10:]
        
        await self.save(wa_number, state)
    
    def _default_state(self) -> Dict[str, Any]:
        """Estado padrão para nova conversa"""
        return {
            "state": "idle",
            "last_intent": None,
            "slots": {},
            "fail_count": 0,
            "history": [],
            "last_update": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
    
    async def get_timeout_status(self, wa_number: str) -> Dict[str, Any]:
        """
        Verificar status de timeout sem modificar estado
        
        Args:
            wa_number: Número do WhatsApp
            
        Returns:
            Dict com: is_timeout, seconds_since_update, current_state
        """
        raw = await self.redis.get(self._key(wa_number)) if self.redis else None
        
        if not raw:
            return {
                "is_timeout": False,
                "seconds_since_update": 0,
                "current_state": "idle",
            }
        
        try:
            state = json.loads(raw)
            last_update_str = state.get("last_update")
            current_state = state.get("state", "idle")
            
            if not last_update_str:
                return {
                    "is_timeout": False,
                    "seconds_since_update": 0,
                    "current_state": current_state,
                }
            
            last_update = datetime.fromisoformat(last_update_str)
            seconds_diff = (datetime.utcnow() - last_update).total_seconds()
            
            is_timeout = (
                current_state.startswith("asking_") or current_state.startswith("need_")
            ) and seconds_diff > self.state_timeout
            
            return {
                "is_timeout": is_timeout,
                "seconds_since_update": int(seconds_diff),
                "current_state": current_state,
            }
        except Exception as e:
            logger.error(f"❌ Erro ao verificar timeout: {e}")
            return {
                "is_timeout": False,
                "seconds_since_update": 0,
                "current_state": "unknown",
            }



