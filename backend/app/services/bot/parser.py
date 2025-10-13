"""
Parsing simples PT-BR de datas e horários para o bot
"""

from typing import Optional, Dict
from datetime import datetime, timedelta, date, time
import re


WEEKDAYS = {
    "segunda": 0,
    "terca": 1,
    "terça": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


TIME_RE = re.compile(r"\b(\d{1,2})(?:[:h](\d{2}))?\b")


def parse_date_from_text(text: str, now: Optional[datetime] = None) -> Optional[date]:
    text = (text or "").lower()
    base = now or datetime.utcnow()

    if "hoje" in text:
        return base.date()
    if "amanh" in text:  # amanhã/amanha
        return (base + timedelta(days=1)).date()

    for wd, idx in WEEKDAYS.items():
        if wd in text:
            days_ahead = (idx - base.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (base + timedelta(days=days_ahead)).date()

    return None


def parse_time_from_text(text: str) -> Optional[time]:
    text = (text or "").lower()
    m = TIME_RE.search(text)
    if not m:
        if "manh" in text:
            return time(10, 0)
        if "tarde" in text:
            return time(14, 0)
        if "noite" in text:
            return time(19, 0)
        return None

    hh = int(m.group(1))
    mm = int(m.group(2) or 0)
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return time(hh, mm)
    return None


def parse_window_from_text(text: str) -> Optional[str]:
    text = (text or "").lower()
    if "manh" in text:
        return "morning"
    if "tarde" in text:
        return "afternoon"
    if "noite" in text:
        return "evening"
    return None


