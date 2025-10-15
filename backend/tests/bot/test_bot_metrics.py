"""
Testes para BotMetrics
"""

import pytest
from app.services.bot.bot_metrics import BotMetrics


@pytest.fixture
def metrics():
    """Fixture para métricas (sem Redis)"""
    return BotMetrics(redis_client=None)


class TestBotMetrics:
    """Testes de métricas do bot"""
    
    @pytest.mark.asyncio
    async def test_record_message(self, metrics):
        """Testar registro de mensagem"""
        await metrics.record_message("schedule", 0.85, "rule")
        
        stats = metrics.get_stats()
        assert stats["total_messages"] == 1
        assert stats["total_intents"]["schedule"] == 1
        assert stats["average_confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_record_multiple_messages(self, metrics):
        """Testar múltiplas mensagens"""
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("price", 0.9, "ml")
        await metrics.record_message("schedule", 0.7, "rule")
        
        stats = metrics.get_stats()
        assert stats["total_messages"] == 3
        assert stats["total_intents"]["schedule"] == 2
        assert stats["total_intents"]["price"] == 1
        
        # Confiança média = (0.8 + 0.9 + 0.7) / 3 = 0.8
        assert abs(stats["average_confidence"] - 0.8) < 0.01
    
    @pytest.mark.asyncio
    async def test_record_error(self, metrics):
        """Testar registro de erro"""
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_error("timeout")
        
        stats = metrics.get_stats()
        assert stats["total_errors"] == 1
        assert stats["error_rate"] == 100.0  # 1 erro em 1 mensagem
    
    @pytest.mark.asyncio
    async def test_record_appointment(self, metrics):
        """Testar registro de agendamento"""
        await metrics.record_appointment_created(turns_count=3)
        await metrics.record_appointment_created(turns_count=5)
        
        stats = metrics.get_stats()
        assert stats["successful_appointments"] == 2
        assert stats["average_turns_per_appointment"] == 4.0  # (3 + 5) / 2
    
    @pytest.mark.asyncio
    async def test_success_rate(self, metrics):
        """Testar taxa de sucesso"""
        await metrics.record_appointment_created(turns_count=1)
        await metrics.record_appointment_created(turns_count=1)
        await metrics.record_appointment_failed()
        
        stats = metrics.get_stats()
        assert stats["successful_appointments"] == 2
        assert stats["failed_appointments"] == 1
        assert abs(stats["success_rate"] - 66.67) < 0.1  # 2/(2+1) = 66.67%
    
    @pytest.mark.asyncio
    async def test_handoff_to_human(self, metrics):
        """Testar transferência para humano"""
        await metrics.record_handoff_to_human()
        await metrics.record_handoff_to_human()
        
        stats = metrics.get_stats()
        assert stats["handoffs_to_human"] == 2
    
    @pytest.mark.asyncio
    async def test_intents_by_source(self, metrics):
        """Testar contagem por fonte"""
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("price", 0.9, "ml")
        await metrics.record_message("services", 0.7, "rule")
        await metrics.record_message("about", 0.85, "context")
        
        stats = metrics.get_stats()
        assert stats["intents_by_source"]["rule"] == 2
        assert stats["intents_by_source"]["ml"] == 1
        assert stats["intents_by_source"]["context"] == 1
    
    @pytest.mark.asyncio
    async def test_top_intents(self, metrics):
        """Testar top intents"""
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("price", 0.9, "ml")
        await metrics.record_message("price", 0.9, "ml")
        await metrics.record_message("services", 0.7, "rule")
        
        top_intents = metrics.get_top_intents(limit=3)
        
        # Deve retornar: [("schedule", 3), ("price", 2), ("services", 1)]
        assert len(top_intents) == 3
        assert top_intents[0] == ("schedule", 3)
        assert top_intents[1] == ("price", 2)
        assert top_intents[2] == ("services", 1)
    
    @pytest.mark.asyncio
    async def test_ml_usage_percentage(self, metrics):
        """Testar percentual de uso de ML"""
        # 2 rule, 1 ml, 1 context = 25% ML
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_message("price", 0.9, "ml")
        await metrics.record_message("services", 0.7, "rule")
        await metrics.record_message("about", 0.85, "context")
        
        ml_percentage = metrics.get_ml_usage_percentage()
        assert ml_percentage == 25.0
    
    @pytest.mark.asyncio
    async def test_reset_stats(self, metrics):
        """Testar reset de estatísticas"""
        await metrics.record_message("schedule", 0.8, "rule")
        await metrics.record_appointment_created(turns_count=3)
        
        # Verificar que tem dados
        stats_before = metrics.get_stats()
        assert stats_before["total_messages"] == 1
        
        # Resetar
        await metrics.reset_stats()
        
        # Verificar que foi resetado
        stats_after = metrics.get_stats()
        assert stats_after["total_messages"] == 0
        assert stats_after["successful_appointments"] == 0
    
    def test_str_representation(self, metrics):
        """Testar representação em string"""
        result = str(metrics)
        
        # Deve conter informações chave
        assert "BotMetrics" in result
        assert "Mensagens:" in result
        assert "Confiança média:" in result




