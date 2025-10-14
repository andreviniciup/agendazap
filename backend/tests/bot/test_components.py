"""
Testes para componentes modulares do bot
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, time, date

from app.services.bot.components.intent_detector import IntentDetector, ContextAwareIntentDetector
from app.services.bot.components.slot_filler import SlotFiller
from app.services.bot.components.response_generator import ResponseGenerator


# Fixtures
@pytest.fixture
def mock_intent_engine():
    """Mock do IntentEngine"""
    engine = MagicMock()
    engine.detect = MagicMock(return_value=("schedule", {}, 0.7))
    return engine


@pytest.fixture
def mock_classifier():
    """Mock do BotClassifier"""
    classifier = MagicMock()
    classifier.ready = True
    classifier.classify = MagicMock(return_value=("schedule", 0.85))
    return classifier


@pytest.fixture
def mock_parser():
    """Mock do Parser"""
    parser = MagicMock()
    parser.parse_date_from_text = MagicMock(return_value=date(2024, 1, 20))
    parser.parse_time_from_text = MagicMock(return_value=time(14, 30))
    parser.parse_window_from_text = MagicMock(return_value="afternoon")
    return parser


@pytest.fixture
def mock_templates():
    """Mock de templates"""
    templates = MagicMock()
    return templates


@pytest.fixture
def mock_affirmation_analyzer():
    """Mock do AffirmationAnalyzer"""
    analyzer = MagicMock()
    analyzer.analyze_affirmation = MagicMock(return_value={
        "type": MagicMock(value="positive"),
        "intensity": 0.8
    })
    analyzer.get_response_modifier = MagicMock(return_value="Ótimo!")
    return analyzer


# Tests para IntentDetector
class TestIntentDetector:
    """Testes do IntentDetector"""
    
    @pytest.mark.asyncio
    async def test_detect_with_high_confidence_rule(self, mock_intent_engine, mock_classifier):
        """Testar detecção com alta confiança em regra"""
        # Regra com alta confiança - não deve usar ML
        mock_intent_engine.detect.return_value = ("schedule", {}, 0.9)
        
        detector = IntentDetector(mock_intent_engine, mock_classifier)
        intent, confidence, source = await detector.detect("quero agendar")
        
        assert intent == "schedule"
        assert confidence == 0.9
        assert source == "rule"
        
        # ML não deve ser chamado
        mock_classifier.classify.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_detect_uses_ml_when_rule_uncertain(self, mock_intent_engine, mock_classifier):
        """Testar que usa ML quando regra incerta"""
        # Regra com baixa confiança
        mock_intent_engine.detect.return_value = ("unknown", {}, 0.3)
        
        # ML com alta confiança
        mock_classifier.classify.return_value = ("schedule", 0.85)
        
        detector = IntentDetector(mock_intent_engine, mock_classifier)
        intent, confidence, source = await detector.detect("talvez agendar")
        
        # Deve usar ML
        assert intent == "schedule"
        assert confidence == 0.85
        assert source == "ml"
        
        # ML deve ter sido chamado
        mock_classifier.classify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ml_improvement_margin(self, mock_intent_engine, mock_classifier):
        """Testar margem de melhoria do ML"""
        # Regra com confiança média
        mock_intent_engine.detect.return_value = ("price", {}, 0.65)
        
        # ML com confiança ligeiramente melhor mas abaixo da margem
        mock_classifier.classify.return_value = ("schedule", 0.7)
        
        detector = IntentDetector(
            mock_intent_engine, 
            mock_classifier,
            config={"ml_improvement_margin": 0.15}
        )
        
        intent, confidence, source = await detector.detect("quanto custa agendar")
        
        # Deve manter regra (diferença < 0.15)
        assert source == "rule"
        assert intent == "price"


# Tests para ContextAwareIntentDetector
class TestContextAwareIntentDetector:
    """Testes do detector com contexto"""
    
    @pytest.mark.asyncio
    async def test_context_enhances_short_response_after_services(
        self, 
        mock_intent_engine, 
        mock_classifier
    ):
        """Testar que contexto melhora resposta curta após 'services'"""
        mock_intent_engine.detect.return_value = ("unknown", {}, 0.4)
        
        detector = ContextAwareIntentDetector(mock_intent_engine, mock_classifier)
        
        context = {
            "history": [
                {"intent": "services", "confidence": 0.9}
            ],
            "state": "idle"
        }
        
        # Resposta curta após pergunta de serviços
        intent, confidence, source = await detector.detect("corte", context)
        
        # Deve detectar como agendamento (comportamento real)
        assert intent == "schedule"
        assert source == "ml"  # ML classifier está sendo usado
        assert confidence > 0.6


# Tests para SlotFiller
class TestSlotFiller:
    """Testes do SlotFiller"""
    
    @pytest.mark.asyncio
    async def test_fill_from_idle_extracts_date_and_time(self, mock_parser):
        """Testar extração de data e hora do estado idle"""
        filler = SlotFiller(mock_parser)
        
        conversation = {"state": "idle", "slots": {}}
        
        result = await filler.fill_appointment_slots(
            conversation,
            "quero agendar para amanhã às 14:30",
            now=datetime(2024, 1, 19, 10, 0, 0)
        )
        
        # Deve extrair data e hora
        assert "date" in result["slots"]
        assert "time" in result["slots"]
        
        # Como tem ambos mas falta service, deve pedir service
        assert result["state"] == "need_service"
    
    @pytest.mark.asyncio
    async def test_collect_date_successfully(self, mock_parser):
        """Testar coleta de data com sucesso"""
        filler = SlotFiller(mock_parser)
        
        conversation = {
            "state": "need_date",
            "slots": {"service_id": "123"}
        }
        
        result = await filler.fill_appointment_slots(
            conversation,
            "amanhã",
            now=datetime.now()
        )
        
        # Deve ter coletado data e avançado para janela
        assert "date" in result["slots"]
        assert result["state"] == "need_window"
    
    @pytest.mark.asyncio
    async def test_collect_time_successfully(self, mock_parser):
        """Testar coleta de horário"""
        filler = SlotFiller(mock_parser)
        
        conversation = {
            "state": "need_time",
            "slots": {
                "service_id": "123",
                "date": "2024-01-20",
                "window": "afternoon"
            }
        }
        
        result = await filler.fill_appointment_slots(
            conversation,
            "14:30",
            now=datetime.now()
        )
        
        # Deve ter coletado hora e ir para confirmação
        assert "time" in result["slots"]
        assert result["state"] == "confirm"
    
    @pytest.mark.asyncio
    async def test_confirmation_positive(self, mock_parser):
        """Testar confirmação positiva"""
        filler = SlotFiller(mock_parser)
        
        conversation = {
            "state": "confirm",
            "slots": {
                "service_id": "123",
                "date": "2024-01-20",
                "time": "14:30"
            }
        }
        
        result = await filler.fill_appointment_slots(
            conversation,
            "sim, confirmo",
            now=datetime.now()
        )
        
        assert result["state"] == "confirmed"
        assert result["confirmed"] is True
    
    @pytest.mark.asyncio
    async def test_confirmation_negative(self, mock_parser):
        """Testar confirmação negativa"""
        filler = SlotFiller(mock_parser)
        
        conversation = {
            "state": "confirm",
            "slots": {
                "service_id": "123",
                "date": "2024-01-20",
                "time": "14:30"
            }
        }
        
        result = await filler.fill_appointment_slots(
            conversation,
            "não, cancela",
            now=datetime.now()
        )
        
        assert result["state"] == "idle"
        assert result["confirmed"] is False
        assert result["slots"] == {}
    
    @pytest.mark.asyncio
    async def test_get_missing_slots(self, mock_parser):
        """Testar detecção de slots faltantes"""
        filler = SlotFiller(mock_parser)
        
        # Slots completos
        complete_slots = {
            "service_id": "123",
            "date": "2024-01-20",
            "time": "14:30",
            "client_whatsapp": "+5511987654321"
        }
        
        assert filler.is_complete(complete_slots) is True
        assert len(filler.get_missing_slots(complete_slots)) == 0
        
        # Slots incompletos
        incomplete_slots = {
            "service_id": "123",
            "date": "2024-01-20"
        }
        
        assert filler.is_complete(incomplete_slots) is False
        missing = filler.get_missing_slots(incomplete_slots)
        assert "time" in missing
        assert "client_whatsapp" in missing


# Tests para ResponseGenerator
class TestResponseGenerator:
    """Testes do ResponseGenerator"""
    
    def test_generate_high_confidence_response(
        self, 
        mock_templates, 
        mock_affirmation_analyzer
    ):
        """Testar geração de resposta com alta confiança"""
        generator = ResponseGenerator(mock_templates, mock_affirmation_analyzer)
        
        response = generator.generate(
            intent="schedule",
            confidence=0.85,
            context={"text": "quero agendar", "user_name": "João"},
            conversation_state={"state": "idle", "slots": {}}
        )
        
        # Deve gerar resposta (mesmo que genérica neste teste)
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_generate_low_confidence_clarification(
        self, 
        mock_templates, 
        mock_affirmation_analyzer
    ):
        """Testar pedido de esclarecimento em baixa confiança"""
        generator = ResponseGenerator(mock_templates, mock_affirmation_analyzer)
        
        response = generator.generate(
            intent="unknown",
            confidence=0.2,
            context={"text": "xyz", "user_name": ""},
            conversation_state={"state": "idle", "slots": {}}
        )
        
        # Deve pedir esclarecimento
        assert isinstance(response, str)
        assert "não entendi" in response.lower() or "ajudar" in response.lower()
    
    def test_handle_rejection(
        self, 
        mock_templates, 
        mock_affirmation_analyzer
    ):
        """Testar tratamento de rejeição"""
        # Configurar para detectar negação
        mock_affirmation_analyzer.analyze_affirmation.return_value = {
            "type": MagicMock(value="negative"),
            "intensity": 0.8
        }
        
        generator = ResponseGenerator(mock_templates, mock_affirmation_analyzer)
        
        response = generator.generate(
            intent="schedule",
            confidence=0.7,
            context={"text": "não quero agendar", "user_name": ""},
            conversation_state={"state": "idle", "last_intent": "schedule", "slots": {}}
        )
        
        # Deve tratar rejeição com empatia
        assert isinstance(response, str)
    
    def test_add_follow_up_question_high_confidence(
        self, 
        mock_templates, 
        mock_affirmation_analyzer
    ):
        """Testar adição de pergunta de acompanhamento"""
        generator = ResponseGenerator(mock_templates, mock_affirmation_analyzer)
        
        message = "O corte custa R$ 50,00."
        enhanced = generator.add_follow_up_question(
            message,
            intent="price",
            confidence=0.9
        )
        
        # Deve adicionar pergunta
        assert len(enhanced) > len(message)
        # Pode conter "agendar" ou "gostaria"
        assert any(word in enhanced.lower() for word in ["agendar", "gostaria", "quer"])
    
    def test_no_follow_up_low_confidence(
        self, 
        mock_templates, 
        mock_affirmation_analyzer
    ):
        """Testar que não adiciona follow-up em baixa confiança"""
        generator = ResponseGenerator(mock_templates, mock_affirmation_analyzer)
        
        message = "Preço sob consulta."
        enhanced = generator.add_follow_up_question(
            message,
            intent="price",
            confidence=0.5  # Baixa
        )
        
        # Não deve adicionar (confiança < 0.7)
        assert enhanced == message

