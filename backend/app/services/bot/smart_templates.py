"""
Templates inteligentes para o bot com ML
"""

import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class Intent(Enum):
    GREETING = "greeting"
    SCHEDULE = "schedule"
    AVAILABILITY = "availability"
    PRICE = "price"
    SERVICES = "services"
    ABOUT = "about"
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"
    BUSINESS_HOURS = "business_hours"
    ADDRESS = "address"
    PAYMENT = "payment"
    HUMAN = "human"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    HIGH = "high"      # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


def get_greeting_prefix(now: datetime) -> str:
    """Retorna prefixo de cumprimento baseado na hora"""
    hour = now.hour
    if 5 <= hour < 12:
        return "Bom dia"
    elif 12 <= hour < 18:
        return "Boa tarde"
    return "Boa noite"


def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """Determina nível de confiança"""
    if confidence > 0.8:
        return ConfidenceLevel.HIGH
    elif confidence > 0.5:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


# Templates inteligentes baseados em intenção e confiança
SMART_TEMPLATES = {
    Intent.GREETING: {
        ConfidenceLevel.HIGH: [
            "{prefix}! Como posso ajudar você hoje?",
            "{prefix}! Posso te ajudar com agendamentos, preços ou informações?",
            "{prefix}! O que você gostaria de saber?",
            "{prefix}! Estou aqui para ajudar!",
        ],
        ConfidenceLevel.MEDIUM: [
            "{prefix}! Acredito que você quer me cumprimentar. Como posso ajudar?",
            "{prefix}! Oi! Posso te ajudar com algo específico?",
        ],
        ConfidenceLevel.LOW: [
            "{prefix}! Não tenho certeza do que você quer. Pode me explicar melhor?",
            "{prefix}! Como posso te ajudar hoje?",
        ]
    },
    
    Intent.SCHEDULE: {
        ConfidenceLevel.HIGH: [
            "Perfeito! Vou te ajudar a agendar. Que tipo de serviço você precisa?",
            "Ótimo! Para qual serviço você gostaria de agendar?",
            "Vamos agendar! Qual procedimento você tem interesse?",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer agendar algo. Que serviço você precisa?",
            "Parece que você quer marcar um horário. Qual serviço?",
        ],
        ConfidenceLevel.LOW: [
            "Não tenho certeza se você quer agendar. Pode me explicar melhor?",
            "Você gostaria de agendar algum serviço?",
        ]
    },
    
    Intent.AVAILABILITY: {
        ConfidenceLevel.HIGH: [
            "Vou verificar nossa disponibilidade para você!",
            "Deixe-me ver os horários disponíveis...",
            "Perfeito! Vou te mostrar os horários livres.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber sobre horários. Vou verificar!",
            "Parece que você quer ver disponibilidade. Deixe-me ver...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de ver nossos horários disponíveis?",
            "Quer saber sobre nossa disponibilidade?",
        ]
    },
    
    Intent.PRICE: {
        ConfidenceLevel.HIGH: [
            "Vou te mostrar nossos preços!",
            "Deixe-me buscar os valores para você...",
            "Perfeito! Vou te passar nossa tabela de preços.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber sobre preços. Vou te mostrar!",
            "Parece que você quer ver valores. Deixe-me buscar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de saber nossos preços?",
            "Quer ver nossa tabela de valores?",
        ]
    },
    
    Intent.SERVICES: {
        ConfidenceLevel.HIGH: [
            "Vou te mostrar todos os nossos serviços!",
            "Deixe-me listar o que oferecemos...",
            "Perfeito! Aqui estão nossos procedimentos.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber sobre nossos serviços. Vou te mostrar!",
            "Parece que você quer ver o que oferecemos. Deixe-me listar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de conhecer nossos serviços?",
            "Quer ver o que oferecemos?",
        ]
    },
    
    Intent.ABOUT: {
        ConfidenceLevel.HIGH: [
            "Vou te explicar como funcionamos!",
            "Deixe-me te contar sobre nosso trabalho...",
            "Perfeito! Vou te explicar nosso processo.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber como funcionamos. Vou te explicar!",
            "Parece que você quer entender nosso processo. Deixe-me explicar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de saber como funcionamos?",
            "Quer entender nosso processo?",
        ]
    },
    
    Intent.CANCEL: {
        ConfidenceLevel.HIGH: [
            "Entendo que você quer cancelar. Vou te ajudar!",
            "Vou te ajudar a cancelar seu agendamento.",
            "Perfeito! Vamos cancelar seu horário.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer cancelar algo. Vou te ajudar!",
            "Parece que você quer cancelar. Deixe-me ajudar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de cancelar algum agendamento?",
            "Quer cancelar seu horário?",
        ]
    },
    
    Intent.RESCHEDULE: {
        ConfidenceLevel.HIGH: [
            "Vou te ajudar a remarcar seu horário!",
            "Perfeito! Vamos remarcar seu agendamento.",
            "Vou te ajudar a alterar sua data.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer remarcar. Vou te ajudar!",
            "Parece que você quer alterar seu horário. Deixe-me ajudar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de remarcar algum horário?",
            "Quer alterar sua data?",
        ]
    },
    
    Intent.BUSINESS_HOURS: {
        ConfidenceLevel.HIGH: [
            "Vou te passar nosso horário de funcionamento!",
            "Deixe-me te informar nossos horários...",
            "Perfeito! Aqui estão nossos horários.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber nossos horários. Vou te informar!",
            "Parece que você quer ver quando funcionamos. Deixe-me te passar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de saber nossos horários?",
            "Quer ver quando funcionamos?",
        ]
    },
    
    Intent.ADDRESS: {
        ConfidenceLevel.HIGH: [
            "Vou te passar nosso endereço!",
            "Deixe-me te informar nossa localização...",
            "Perfeito! Aqui está nosso endereço.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber nosso endereço. Vou te informar!",
            "Parece que você quer nossa localização. Deixe-me te passar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de saber nosso endereço?",
            "Quer nossa localização?",
        ]
    },
    
    Intent.PAYMENT: {
        ConfidenceLevel.HIGH: [
            "Vou te explicar nossas formas de pagamento!",
            "Deixe-me te informar sobre pagamentos...",
            "Perfeito! Aqui estão nossas opções de pagamento.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer saber sobre pagamento. Vou te explicar!",
            "Parece que você quer saber como pagar. Deixe-me te informar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de saber sobre formas de pagamento?",
            "Quer saber como pagar?",
        ]
    },
    
    Intent.HUMAN: {
        ConfidenceLevel.HIGH: [
            "Entendo! Vou te conectar com um atendente humano.",
            "Perfeito! Vou te passar para um de nossos atendentes.",
            "Vou te direcionar para atendimento pessoal.",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que você quer falar com alguém. Vou te conectar!",
            "Parece que você prefere atendimento humano. Deixe-me te conectar...",
        ],
        ConfidenceLevel.LOW: [
            "Você gostaria de falar com um atendente?",
            "Quer atendimento pessoal?",
        ]
    },
    
    Intent.UNKNOWN: {
        ConfidenceLevel.HIGH: [
            "Desculpe, não entendi bem. Pode reformular sua pergunta?",
            "Não consegui entender. Pode me explicar de outra forma?",
        ],
        ConfidenceLevel.MEDIUM: [
            "Acredito que não entendi direito. Pode me explicar melhor?",
            "Parece que não captei. Pode reformular?",
        ],
        ConfidenceLevel.LOW: [
            "Não tenho certeza do que você quer. Pode me explicar?",
            "Pode me ajudar a entender o que você precisa?",
        ]
    }
}


def get_smart_response(
    intent: str, 
    confidence: float, 
    context: Optional[Dict[str, Any]] = None,
    user_name: str = "",
    service_name: str = ""
) -> str:
    """
    Gera resposta inteligente baseada em intenção, confiança e contexto
    
    Args:
        intent: Intenção detectada
        confidence: Nível de confiança (0.0 - 1.0)
        context: Contexto adicional da conversa
        user_name: Nome do usuário
        service_name: Nome do serviço
    
    Returns:
        Resposta personalizada do bot
    """
    
    # Determinar nível de confiança
    conf_level = get_confidence_level(confidence)
    
    # Obter prefixo de cumprimento
    prefix = get_greeting_prefix(datetime.utcnow())
    
    # Preparar contexto
    template_context = {
        "prefix": prefix,
        "user_name": user_name,
        "service_name": service_name,
        "confidence": f"{confidence:.1%}"
    }
    
    # Adicionar contexto adicional se fornecido
    if context:
        template_context.update(context)
    
    # Obter templates para a intenção
    intent_enum = Intent(intent) if intent in [i.value for i in Intent] else Intent.UNKNOWN
    templates = SMART_TEMPLATES.get(intent_enum, {}).get(conf_level, [])
    
    # Se não há templates específicos, usar fallback
    if not templates:
        templates = SMART_TEMPLATES[Intent.UNKNOWN][conf_level]
    
    # Escolher template aleatório
    template = random.choice(templates)
    
    # Preencher template
    try:
        return template.format(**template_context)
    except KeyError as e:
        # Se faltar alguma variável, usar template simples
        return f"{prefix}! Como posso ajudar você hoje?"


def get_follow_up_questions(intent: str, confidence: float) -> List[str]:
    """
    Gera perguntas de acompanhamento baseadas na intenção
    
    Args:
        intent: Intenção detectada
        confidence: Nível de confiança
    
    Returns:
        Lista de perguntas de acompanhamento
    """
    
    follow_ups = {
        Intent.SCHEDULE: [
            "Qual serviço você tem interesse?",
            "Para quando você gostaria de agendar?",
            "Que horário funciona melhor para você?",
        ],
        Intent.PRICE: [
            "Para qual serviço você quer saber o preço?",
            "Quer ver preços de todos os serviços?",
            "Tem algum procedimento específico em mente?",
        ],
        Intent.SERVICES: [
            "Quer ver todos os serviços ou algum específico?",
            "Tem alguma área de interesse?",
            "Quer saber mais sobre algum procedimento?",
        ],
        Intent.AVAILABILITY: [
            "Para qual serviço você quer ver horários?",
            "Que período você tem disponível?",
            "Prefere manhã, tarde ou noite?",
        ]
    }
    
    intent_enum = Intent(intent) if intent in [i.value for i in Intent] else Intent.UNKNOWN
    questions = follow_ups.get(intent_enum, [])
    
    # Retornar pergunta aleatória se disponível
    return [random.choice(questions)] if questions else []


def get_contextual_response(
    intent: str,
    confidence: float,
    conversation_history: List[Dict[str, Any]],
    user_preferences: Dict[str, Any] = None
) -> str:
    """
    Gera resposta contextual baseada no histórico da conversa
    
    Args:
        intent: Intenção detectada
        confidence: Nível de confiança
        conversation_history: Histórico da conversa
        user_preferences: Preferências do usuário
    
    Returns:
        Resposta contextual
    """
    
    # Analisar histórico para contexto
    recent_intents = [msg.get('intent') for msg in conversation_history[-3:]]
    is_repeat_intent = recent_intents.count(intent) > 1
    
    # Ajustar resposta baseada no contexto
    base_response = get_smart_response(intent, confidence)
    
    if is_repeat_intent:
        return f"{base_response} (Vejo que você já perguntou sobre isso antes. Vou te ajudar melhor desta vez!)"
    
    # Adicionar informações baseadas em preferências
    if user_preferences and intent == Intent.SCHEDULE.value:
        preferred_time = user_preferences.get('preferred_time')
        if preferred_time:
            return f"{base_response} Vi que você prefere horários de {preferred_time}. Vou te mostrar opções nesse período!"
    
    return base_response



