"""
Testes para ConversationState com timeout
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.services.bot.conversation_state import ConversationState
import json


@pytest.fixture
def mock_redis():
    """Mock do Redis"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def conversation_state(mock_redis):
    """Fixture para ConversationState"""
    return ConversationState(
        redis_client=mock_redis,
        ttl_seconds=24 * 3600,
        state_timeout_seconds=5 * 60  # 5 minutos
    )


class TestConversationState:
    """Testes de gerenciamento de estado"""
    
    @pytest.mark.asyncio
    async def test_load_new_conversation(self, conversation_state):
        """Testar carregamento de nova conversa"""
        state = await conversation_state.load("+5511987654321")
        
        # Deve retornar estado padrão
        assert state["state"] == "idle"
        assert state["slots"] == {}
        assert state["fail_count"] == 0
        assert "history" in state
        assert "last_update" in state
    
    @pytest.mark.asyncio
    async def test_save_conversation(self, conversation_state, mock_redis):
        """Testar salvamento de conversa"""
        wa_number = "+5511987654321"
        data = {
            "state": "asking_date",
            "slots": {"service_id": "123"},
            "fail_count": 0,
        }
        
        await conversation_state.save(wa_number, data)
        
        # Verificar que chamou set e expire
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        # Verificar que adicionou last_update
        call_args = mock_redis.set.call_args
        saved_data = json.loads(call_args[0][1])
        assert "last_update" in saved_data
    
    @pytest.mark.asyncio
    async def test_timeout_detection(self, conversation_state, mock_redis):
        """Testar detecção de timeout"""
        wa_number = "+5511987654321"
        
        # Criar estado com timestamp antigo (10 minutos atrás)
        old_timestamp = datetime.utcnow() - timedelta(minutes=10)
        old_state = {
            "state": "asking_date",
            "slots": {"service_id": "123"},
            "fail_count": 0,
            "history": [],
            "last_update": old_timestamp.isoformat(),
        }
        
        # Configurar mock para retornar estado antigo
        mock_redis.get.return_value = json.dumps(old_state)
        
        # Carregar estado - deve detectar timeout
        state = await conversation_state.load(wa_number)
        
        # Estado deve ter sido resetado para idle
        assert state["state"] == "idle"
        assert state["slots"] == {}
        assert "timeout_occurred" in state
        assert state["timeout_occurred"] is True
    
    @pytest.mark.asyncio
    async def test_no_timeout_recent_update(self, conversation_state, mock_redis):
        """Testar que não há timeout com atualização recente"""
        wa_number = "+5511987654321"
        
        # Estado com timestamp recente (1 minuto atrás)
        recent_timestamp = datetime.utcnow() - timedelta(minutes=1)
        recent_state = {
            "state": "asking_date",
            "slots": {"service_id": "123"},
            "fail_count": 0,
            "history": [],
            "last_update": recent_timestamp.isoformat(),
        }
        
        mock_redis.get.return_value = json.dumps(recent_state)
        
        # Carregar estado - NÃO deve detectar timeout
        state = await conversation_state.load(wa_number)
        
        # Estado deve permanecer como estava
        assert state["state"] == "asking_date"
        assert state["slots"]["service_id"] == "123"
    
    @pytest.mark.asyncio
    async def test_timeout_only_for_asking_states(self, conversation_state, mock_redis):
        """Testar que timeout só afeta estados 'asking_*'"""
        wa_number = "+5511987654321"
        
        # Estado idle com timestamp antigo
        old_timestamp = datetime.utcnow() - timedelta(minutes=10)
        idle_state = {
            "state": "idle",
            "slots": {},
            "fail_count": 0,
            "history": [],
            "last_update": old_timestamp.isoformat(),
        }
        
        mock_redis.get.return_value = json.dumps(idle_state)
        
        # Carregar estado - NÃO deve resetar (idle não tem timeout)
        state = await conversation_state.load(wa_number)
        
        # Estado deve permanecer idle
        assert state["state"] == "idle"
        assert "timeout_occurred" not in state
    
    @pytest.mark.asyncio
    async def test_add_to_history(self, conversation_state, mock_redis):
        """Testar adição ao histórico"""
        wa_number = "+5511987654321"
        
        # Carregar estado inicial
        mock_redis.get.return_value = None
        
        # Adicionar ao histórico
        await conversation_state.add_to_history(
            wa_number=wa_number,
            intent="schedule",
            confidence=0.85,
            text="quero agendar",
            response="Claro! Que dia?"
        )
        
        # Verificar que salvou
        assert mock_redis.set.called
        
        # Verificar dados salvos
        call_args = mock_redis.set.call_args
        saved_data = json.loads(call_args[0][1])
        
        assert "history" in saved_data
        assert len(saved_data["history"]) == 1
        assert saved_data["history"][0]["intent"] == "schedule"
        assert saved_data["history"][0]["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_history_limit(self, conversation_state, mock_redis):
        """Testar limite de histórico (10 turnos)"""
        wa_number = "+5511987654321"
        
        # Criar estado com 12 entradas no histórico
        history = [
            {
                "intent": f"intent_{i}",
                "confidence": 0.8,
                "text": f"text {i}",
                "response": f"response {i}",
                "timestamp": datetime.utcnow().isoformat(),
            }
            for i in range(12)
        ]
        
        state = {
            "state": "idle",
            "slots": {},
            "fail_count": 0,
            "history": history,
            "last_update": datetime.utcnow().isoformat(),
        }
        
        # Salvar estado
        await conversation_state.save(wa_number, state)
        
        # Verificar que limitou a 10
        call_args = mock_redis.set.call_args
        saved_data = json.loads(call_args[0][1])
        
        assert len(saved_data["history"]) == 10
        # Deve manter os últimos 10
        assert saved_data["history"][0]["intent"] == "intent_2"
        assert saved_data["history"][-1]["intent"] == "intent_11"
    
    @pytest.mark.asyncio
    async def test_reset_conversation(self, conversation_state, mock_redis):
        """Testar reset completo"""
        wa_number = "+5511987654321"
        
        await conversation_state.reset(wa_number)
        
        # Deve ter deletado a chave
        mock_redis.delete.assert_called_once_with(f"conversation:{wa_number}")
    
    @pytest.mark.asyncio
    async def test_get_timeout_status(self, conversation_state, mock_redis):
        """Testar verificação de status de timeout"""
        wa_number = "+5511987654321"
        
        # Estado com timeout
        old_timestamp = datetime.utcnow() - timedelta(minutes=10)
        state = {
            "state": "asking_date",
            "slots": {},
            "last_update": old_timestamp.isoformat(),
        }
        
        mock_redis.get.return_value = json.dumps(state)
        
        # Verificar status
        status = await conversation_state.get_timeout_status(wa_number)
        
        assert status["is_timeout"] is True
        assert status["current_state"] == "asking_date"
        assert status["seconds_since_update"] >= 600  # 10 minutos




