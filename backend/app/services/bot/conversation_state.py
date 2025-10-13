"""
Gerenciamento de estado de conversa no Redis
"""

from typing import Optional, Dict, Any
import json
from datetime import timedelta


class ConversationState:
    def __init__(self, redis_client, ttl_seconds: int = 24 * 3600) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _key(self, wa_number: str) -> str:
        return f"conversation:{wa_number}"

    async def load(self, wa_number: str) -> Dict[str, Any]:
        raw = await self.redis.get(self._key(wa_number)) if self.redis else None
        return json.loads(raw) if raw else {
            "state": "idle",
            "last_intent": None,
            "slots": {},
            "fail_count": 0,
        }

    async def save(self, wa_number: str, data: Dict[str, Any]) -> None:
        if not self.redis:
            return
        await self.redis.set(self._key(wa_number), json.dumps(data))
        await self.redis.expire(self._key(wa_number), self.ttl)

    async def reset(self, wa_number: str) -> None:
        if not self.redis:
            return
        await self.redis.delete(self._key(wa_number))



