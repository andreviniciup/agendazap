"""
Templates com variações e placeholders
"""

from typing import Dict, List
import random
from datetime import datetime


def is_night(now: datetime) -> bool:
    hour = now.hour
    return hour < 8 or hour >= 20


def greeting_prefix(now: datetime) -> str:
    hour = now.hour
    if 5 <= hour < 12:
        return "Bom dia"
    if 12 <= hour < 18:
        return "Boa tarde"
    return "Boa noite"


VARIATIONS: Dict[str, Dict[str, List[str]]] = {
    "greeting": {
        "day": [
            "{prefix}, {first_name}! Tudo bem? Sou da {provider_name}. Como posso ajudar hoje?",
            "{prefix}, {first_name}! Posso listar serviços, valores ou horários para você?",
            "{prefix}! Aqui é da {provider_name}. Deseja ver serviços, preços ou disponibilidade?",
        ],
        "night": [
            "{prefix}, {first_name}! Tudo bem? Posso ajudar com serviços, valores ou horários?",
            "{prefix}! Sou da {provider_name}. Quer ver serviços ou preços?",
        ],
    },
    "availability": {
        "day": [
            "Perfeito! Tenho {time_options}. Qual fica melhor para você?",
            "Tenho disponibilidade em {time_options}. Prefere algum horário?",
        ],
        "night": [
            "Amanhã tenho {time_options}. Posso reservar para você?",
        ],
    },
    "price": {
        "day": [
            "{prefix}, {first_name}! O valor de {service_name} é {price}. Posso te mostrar horários?",
            "{service_name} fica em {price}. Deseja que eu liste horários disponíveis?",
        ],
        "night": [
            "{service_name} custa {price}. Posso te enviar horários amanhã cedo?",
        ],
    },
    "confirm": {
        "day": [
            "Ótimo! Confirmo para {date} às {time}?",
            "Posso agendar {service_name} para {date} às {time}?",
        ],
        "night": [
            "Deixo reservado para {date} às {time}?",
        ],
    },
    "handoff": {
        "day": [
            "Entendi. Vou encaminhar para um profissional te responder rapidinho!",
            "Sem problemas! Vou te passar para um atendente que já te retorna.",
        ],
        "night": [
            "Vou encaminhar para um profissional e ele te retorna logo!",
        ],
    },
    "media_handoff": {
        "day": [
            "Recebi {media_type}! No momento não consigo processar, então vou passar para um profissional, tudo bem?",
            "Vi que você enviou {media_type}. Vou encaminhar para um profissional analisar, ok?",
        ],
        "night": [
            "Recebi {media_type}. Vou passar para um profissional te responder amanhã cedo!",
        ],
    },
    "reminder": {
        "day": [
            "⏰ Oi {client_name}! Lembrando do seu horário de {service_name} em {date} às {time}. Nos vemos lá!",
            "⏰ Olá {client_name}! Seu horário de {service_name} é amanhã às {time}. Até lá!",
        ],
        "night": [
            "⏰ Oi {client_name}! Lembre-se: {service_name} amanhã às {time}!",
        ],
    },
    "confirmation_request": {
        "day": [
            "Oi {client_name}! Você confirma seu horário de {service_name} em {date} às {time}? Responda:\n1️⃣ Confirmo\n2️⃣ Preciso cancelar\n3️⃣ Reagendar",
            "Olá {client_name}! Confirma o {service_name} para {date} às {time}?\n1️⃣ Sim, confirmo\n2️⃣ Cancelar\n3️⃣ Mudar horário",
        ],
        "night": [
            "Oi {client_name}! Confirma {service_name} amanhã às {time}?\n1️⃣ Confirmo\n2️⃣ Cancelar\n3️⃣ Reagendar",
        ],
    },
    "feedback_request": {
        "day": [
            "Oi {client_name}! Como foi sua experiência com {service_name}? De 0 a 10, qual a chance de nos recomendar? Pode comentar algo que possamos melhorar? 😊",
            "Olá {client_name}! Gostou do {service_name}? Sua opinião é muito importante! De 0 a 10, nos recomendaria? Conte o que achou! 💬",
        ],
        "night": [
            "Oi {client_name}! Como foi o {service_name}? De 0 a 10, nos recomendaria? 😊",
        ],
    },
    "clarify": {
        "day": [
            "Você prefere que eu mostre horários ou valores do {service_name}?",
            "Prefere que eu te mostre preços ou horários agora?",
        ],
        "night": [
            "Quer preços ou horários do {service_name}?",
        ],
    },
    "about": {
        "day": [
            "{prefix}, {first_name}! Funciona assim: você escolhe o serviço, eu mostro horários e confirmo. Quer ver serviços ou horários?",
            "Nosso processo é simples: escolher serviço → ver horários → confirmar. Prefere começar pelos serviços?",
        ],
        "night": [
            "É simples: serviço, horários e confirmação. Quer que eu liste os serviços?",
        ],
    },
}


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def pick(intent: str, tone: str, **kwargs) -> str:
    variants = VARIATIONS.get(intent, {}).get(tone, [])
    if not variants:
        return ""
    template = random.choice(variants)
    # Preencher prefixo educado se não fornecido
    if "prefix" not in kwargs:
        kwargs["prefix"] = greeting_prefix(datetime.utcnow())
    return template.format_map(_SafeDict(**kwargs))


