"""
Componentes modulares do bot
"""

from .intent_detector import IntentDetector
from .slot_filler import SlotFiller
from .response_generator import ResponseGenerator

__all__ = ["IntentDetector", "SlotFiller", "ResponseGenerator"]




