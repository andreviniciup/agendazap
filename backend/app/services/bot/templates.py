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
            "Se preferir, posso te direcionar ao atendimento humano agora.",
            "Posso te passar para um atendente, tudo bem?",
        ],
        "night": [
            "Se preferir, peço para um atendente te chamar amanhã cedo.",
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


