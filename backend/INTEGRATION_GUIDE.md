# 🔧 Guia de Integração - Melhorias do Bot

## 📋 Visão Geral

Este guia mostra como integrar os novos componentes modulares ao `bot_service.py` existente.

## ⚡ Quick Start

### Opção 1: Usar Componentes Diretamente (Recomendado)

Substitua o processamento atual do bot pelos novos componentes:

```python
# backend/app/services/bot/bot_service.py

from app.services.bot.components import IntentDetector, SlotFiller, ResponseGenerator
from app.services.bot.enhanced_parser import EnhancedParser
from app.services.bot.bot_metrics import BotMetrics
from app.services.bot.conversation_state import ConversationState

class BotService:
    def __init__(self, redis_client) -> None:
        # Estado e parser
        self.state = ConversationState(redis_client, state_timeout_seconds=5*60)
        self.parser = EnhancedParser()
        
        # Componentes de intenção
        self.intent_engine = IntentEngine()
        self.classifier = BotClassifier()
        self.intent_detector = IntentDetector(
            self.intent_engine, 
            self.classifier,
            config={
                "rule_confidence_threshold": 0.8,
                "ml_min_confidence": 0.6,
            }
        )
        
        # Componentes de processamento
        self.slot_filler = SlotFiller(self.parser)
        self.affirmation_analyzer = AffirmationAnalyzer()
        self.response_generator = ResponseGenerator(
            templates, 
            self.affirmation_analyzer
        )
        
        # Métricas
        self.metrics = BotMetrics(redis_client)
        
        # Coletor de dados (existente)
        self.collector = DataCollector()

    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Processar mensagem usando componentes modulares"""
        
        # 1. NORMALIZAR ENTRADA
        wa_number = payload.get("from")
        text = self._extract_text(payload)
        now = datetime.utcnow()
        
        # 2. CARREGAR ESTADO (agora com timeout automático!)
        conversation = await self.state.load(wa_number)
        
        # Preparar contexto
        context = {
            "text": text,
            "user_name": conversation.get("slots", {}).get("first_name", ""),
            "history": conversation.get("history", []),
            "state": conversation.get("state", "idle"),
        }
        
        # 3. DETECTAR INTENÇÃO (híbrido: regras + ML + contexto)
        intent, confidence, source = await self.intent_detector.detect(text, context)
        
        # 4. REGISTRAR MÉTRICA
        await self.metrics.record_message(intent, confidence, source)
        
        # 5. COLETAR DADOS (se necessário)
        self.collector.log_interaction(
            text=text,
            intent=intent,
            confidence=confidence,
            label_quality=self._get_label_quality(confidence),
            user_whatsapp=wa_number,
            context=context,
            resolved=False
        )
        
        # 6. PREENCHER SLOTS (máquina de estados)
        slot_result = await self.slot_filler.fill_appointment_slots(
            conversation,
            text,
            now
        )
        
        # Atualizar conversa com novos slots
        conversation["slots"] = slot_result["slots"]
        conversation["state"] = slot_result.get("state", "idle")
        
        # 7. VERIFICAR SE DEVE CRIAR AGENDAMENTO
        if slot_result.get("confirmed"):
            created_msg = await self._try_create_appointment(
                slot_result["slots"], 
                "day"  # ou "night" baseado em hora
            )
            
            if created_msg:
                await self.metrics.record_appointment_created(
                    turns_count=len(conversation.get("history", []))
                )
                response_text = created_msg
            else:
                await self.metrics.record_appointment_failed()
                response_text = "Desculpe, não consegui criar o agendamento. Tente novamente."
        
        # 8. GERAR RESPOSTA
        else:
            # Usar prompt do slot filler se houver
            if slot_result.get("next_prompt"):
                response_text = slot_result["next_prompt"]
            else:
                # Gerar resposta inteligente
                response_text = self.response_generator.generate(
                    intent=intent,
                    confidence=confidence,
                    context=context,
                    conversation_state=conversation
                )
                
                # Adicionar follow-up se alta confiança
                if confidence > 0.8:
                    response_text = self.response_generator.add_follow_up_question(
                        response_text,
                        intent,
                        confidence
                    )
        
        # 9. SALVAR ESTADO
        await self.state.save(wa_number, conversation)
        
        # 10. ADICIONAR AO HISTÓRICO
        await self.state.add_to_history(
            wa_number, intent, confidence, text, response_text
        )
        
        # 11. RETORNAR RESPOSTA
        return {
            "to_number": wa_number,
            "message": response_text
        }
    
    def _extract_text(self, payload: Dict[str, Any]) -> str:
        """Extrair texto de diferentes formatos de payload"""
        if "text" in payload:
            return payload.get("text", "").strip()
        elif "messages" in payload and payload["messages"]:
            return payload["messages"][0].get("text", {}).get("body", "").strip()
        return ""
    
    def _get_label_quality(self, confidence: float) -> str:
        """Determinar qualidade de etiqueta para ML"""
        if confidence > 0.8:
            return LabelQuality.CONFIDENT.value
        elif confidence < 0.3:
            return LabelQuality.UNCERTAIN.value
        else:
            return LabelQuality.UNCERTAIN.value
```

### Opção 2: Migração Gradual

Se preferir migrar gradualmente, pode usar componentes específicos:

#### Apenas Melhorar Parser

```python
# Trocar parser antigo pelo EnhancedParser
from app.services.bot.enhanced_parser import EnhancedParser

parser = EnhancedParser()

# Uso
date = parser.parse_date("próxima segunda")
time = parser.parse_time("final da tarde")
entities = parser.extract_entities("quero agendar amanhã às 14h")
```

#### Apenas Adicionar Métricas

```python
from app.services.bot.bot_metrics import BotMetrics

# No __init__
self.metrics = BotMetrics(redis_client)

# Ao processar mensagem
await self.metrics.record_message(intent, confidence, source)

# Ao criar agendamento
await self.metrics.record_appointment_created(turns_count=3)

# Ver estatísticas
stats = self.metrics.get_stats()
print(f"Taxa de sucesso: {stats['success_rate']}%")
```

#### Apenas Melhorar Estado

```python
# Já está usando ConversationState? Apenas atualize!
# Agora tem timeout automático de 5 minutos

# Verificar timeout
status = await self.state.get_timeout_status(wa_number)
if status["is_timeout"]:
    print("Conversa expirou!")

# Adicionar ao histórico
await self.state.add_to_history(
    wa_number, intent, confidence, text, response
)
```

---

## 🔄 Compatibilidade com Código Existente

Os componentes foram projetados para serem **compatíveis** com o código existente:

### Parser

```python
# Código antigo ainda funciona!
from app.services.bot import parser

date = parser.parse_date_from_text("amanhã")
time = parser.parse_time_from_text("14h")
window = parser.parse_window_from_text("manhã")

# Mas agora há um parser muito melhor:
from app.services.bot.enhanced_parser import EnhancedParser
parser = EnhancedParser()
date = parser.parse_date("próxima segunda")  # Muito mais capaz!
```

### ConversationState

```python
# Interface mantida, só melhorada internamente
state = await self.state.load(wa_number)  # Agora com timeout automático!
await self.state.save(wa_number, state)    # Agora com timestamp
```

---

## 📊 Monitoramento

### Ver Estatísticas do Bot

```python
# Em qualquer lugar do código
stats = bot_service.metrics.get_stats()

print(f"""
Bot Statistics:
- Total mensagens: {stats['total_messages']}
- Confiança média: {stats['average_confidence']:.1%}
- Taxa de erro: {stats['error_rate']:.1f}%
- Agendamentos: {stats['successful_appointments']} ✅ / {stats['failed_appointments']} ❌
- Taxa de sucesso: {stats['success_rate']:.1f}%
- Uso de ML: {bot_service.metrics.get_ml_usage_percentage():.1f}%
""")

# Top intents
for intent, count in bot_service.metrics.get_top_intents(5):
    print(f"  {intent}: {count} vezes")
```

### Criar Endpoint de Métricas

```python
# backend/app/api/admin.py

from fastapi import APIRouter
from app.dependencies import get_redis
from app.services.bot.bot_metrics import BotMetrics

router = APIRouter()

@router.get("/bot/metrics")
async def get_bot_metrics():
    """Endpoint para visualizar métricas do bot"""
    redis_client = await get_redis()
    metrics = BotMetrics(redis_client)
    await metrics.load_from_redis()
    
    return metrics.get_stats()
```

---

## 🧪 Testar Componentes

### Rodar Testes

```bash
# Todos os testes
pytest backend/tests/bot/ -v

# Teste específico
pytest backend/tests/bot/test_intent_detection.py::TestIntentDetection::test_schedule_intent_variations -v

# Com cobertura
pytest backend/tests/bot/ --cov=app.services.bot --cov-report=html
open htmlcov/index.html  # Ver relatório
```

### Testar Manualmente

```python
# backend/test_bot_manual.py

from app.services.bot.enhanced_parser import EnhancedParser
from datetime import datetime

parser = EnhancedParser()

# Testar datas
test_cases = [
    "hoje",
    "amanhã",
    "próxima segunda",
    "23 de março",
    "15/12",
]

for text in test_cases:
    result = parser.parse_date(text, datetime.now())
    print(f"{text:20} → {result}")

# Testar horários
time_cases = ["10h", "14:30", "manhã", "final da tarde"]
for text in time_cases:
    result = parser.parse_time(text)
    print(f"{text:20} → {result}")
```

---

## 🚨 Troubleshooting

### Parser não reconhece data

**Problema:** `parser.parse_date("amanhã")` retorna `None`

**Solução:** Verificar se está usando `EnhancedParser`:

```python
# ❌ Errado
from app.services.bot import parser
result = parser.parse_date_from_text("amanhã")  # Antigo

# ✅ Correto
from app.services.bot.enhanced_parser import EnhancedParser
parser = EnhancedParser()
result = parser.parse_date("amanhã")  # Novo
```

### Timeout não funciona

**Problema:** Estado não reseta após 5 minutos

**Solução:** Verificar se está usando `ConversationState` melhorado:

```python
# Verificar parâmetros
state = ConversationState(
    redis_client=redis,
    state_timeout_seconds=5 * 60  # ← Importante!
)

# Verificar se estado é "asking_*"
# Timeout só funciona em estados: asking_date, asking_time, need_*, etc.
```

### Métricas não persistem

**Problema:** Métricas zeradas após restart

**Solução:** Passar `redis_client` ao criar:

```python
# ❌ Sem Redis (apenas memória)
metrics = BotMetrics(redis_client=None)

# ✅ Com Redis (persistente)
redis_client = await get_redis()
metrics = BotMetrics(redis_client=redis_client)
await metrics.load_from_redis()  # Carregar dados anteriores
```

---

## 📝 Checklist de Integração

- [ ] **Parser:** Trocar `parser.py` por `EnhancedParser`
- [ ] **Estado:** `ConversationState` já tem timeout automático
- [ ] **Intenção:** Usar `IntentDetector` (híbrido regras+ML)
- [ ] **Slots:** Usar `SlotFiller` (máquina de estados)
- [ ] **Respostas:** Usar `ResponseGenerator` (contextual)
- [ ] **Métricas:** Adicionar `BotMetrics` ao processo
- [ ] **Testes:** Rodar `pytest tests/bot/` e verificar
- [ ] **Monitoramento:** Criar endpoint `/bot/metrics`
- [ ] **Logs:** Adicionar logging estruturado
- [ ] **Documentação:** Atualizar README do projeto

---

## 🎯 Exemplo Completo de Uso

```python
# backend/test_full_integration.py

import asyncio
from datetime import datetime
from app.dependencies import get_redis
from app.services.bot.bot_service import BotService

async def main():
    # Setup
    redis = await get_redis()
    bot = BotService(redis)
    
    # Simular conversação
    payloads = [
        {"from": "+5511987654321", "text": "oi"},
        {"from": "+5511987654321", "text": "quero agendar"},
        {"from": "+5511987654321", "text": "amanhã"},
        {"from": "+5511987654321", "text": "de tarde"},
        {"from": "+5511987654321", "text": "14h"},
        {"from": "+5511987654321", "text": "sim, confirma"},
    ]
    
    for i, payload in enumerate(payloads):
        print(f"\n{'='*60}")
        print(f"TURNO {i+1}")
        print(f"{'='*60}")
        print(f"USER: {payload['text']}")
        
        result = await bot.process(payload)
        
        print(f"BOT:  {result['message']}")
    
    # Mostrar métricas
    print(f"\n{'='*60}")
    print("MÉTRICAS FINAIS")
    print(f"{'='*60}")
    stats = bot.metrics.get_stats()
    print(f"Total mensagens: {stats['total_messages']}")
    print(f"Confiança média: {stats['average_confidence']:.1%}")
    print(f"Agendamentos: {stats['successful_appointments']}")
    print(f"Top intents: {bot.metrics.get_top_intents(3)}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Rodar:**

```bash
cd backend
python test_full_integration.py
```

---

## 🔗 Links Úteis

- [BOT_IMPROVEMENTS.md](./BOT_IMPROVEMENTS.md) - Documentação completa
- [tests/bot/](./tests/bot/) - Exemplos de uso nos testes
- [Componentes](./app/services/bot/components/) - Código fonte

---

## 🤝 Suporte

Dúvidas? Consulte:

1. Este guia (você está aqui!)
2. `BOT_IMPROVEMENTS.md` - Documentação técnica
3. Testes unitários - Exemplos práticos
4. Docstrings do código - Documentação inline

---

**Boa sorte com a integração! 🚀**

