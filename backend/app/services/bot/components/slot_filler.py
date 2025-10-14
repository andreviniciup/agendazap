"""
SlotFiller - Gerencia coleta de dados necessários para uma ação
Responsabilidade única: preencher slots de forma conversacional
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SlotFiller:
    """Gerenciador de preenchimento de slots para agendamentos"""
    
    def __init__(self, parser, db_session=None):
        """
        Args:
            parser: Parser de entidades (datas, horas, etc)
            db_session: Sessão de banco (opcional)
        """
        self.parser = parser
        self.db = db_session
    
    async def fill_appointment_slots(
        self, 
        conversation: Dict[str, Any], 
        user_message: str,
        now: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Preencher slots para agendamento de forma incremental
        
        Máquina de estados: idle → need_service → need_date → need_time → confirm
        
        Args:
            conversation: Estado da conversa
            user_message: Mensagem do usuário
            now: Timestamp atual (para parsing de datas relativas)
            
        Returns:
            Dict com: slots, state, next_prompt, error (se houver)
        """
        if not now:
            now = datetime.utcnow()
        
        slots = conversation.get("slots", {})
        state = conversation.get("state", "idle")
        
        logger.debug(f"📋 SlotFiller - Estado: {state}, Slots: {list(slots.keys())}")
        
        # Máquina de estados
        if state == "idle":
            return await self._handle_idle(user_message, slots, now)
        
        elif state == "need_service" or state == "asking_service":
            return await self._handle_need_service(user_message, slots)
        
        elif state == "need_date" or state == "asking_date":
            return await self._handle_need_date(user_message, slots, now)
        
        elif state == "need_window" or state == "asking_window":
            return await self._handle_need_window(user_message, slots)
        
        elif state == "need_time" or state == "asking_time":
            return await self._handle_need_time(user_message, slots)
        
        elif state == "confirm":
            return await self._handle_confirm(user_message, slots)
        
        # Estado desconhecido - resetar
        logger.warning(f"⚠️ Estado desconhecido: {state}, resetando para idle")
        return {
            "slots": {},
            "state": "idle",
            "next_prompt": "Como posso ajudar?"
        }
    
    async def _handle_idle(
        self, 
        user_message: str, 
        slots: Dict, 
        now: datetime
    ) -> Dict[str, Any]:
        """Estado inicial: tentar extrair tudo de uma vez"""
        
        # Tentar extrair serviço (se disponível no payload ou texto)
        service_id = slots.get("service_id") or await self._extract_service(user_message)
        
        # Tentar extrair data
        date = self.parser.parse_date_from_text(user_message, now)
        
        # Tentar extrair horário
        time = self.parser.parse_time_from_text(user_message)
        
        # Preencher o que conseguiu extrair
        updated_slots = dict(slots)
        if service_id:
            updated_slots["service_id"] = service_id
        if date:
            updated_slots["date"] = date.isoformat()
        if time:
            updated_slots["time"] = f"{time.hour:02d}:{time.minute:02d}" if time.minute else f"{time.hour:02d}h"
        
        # Determinar próximo estado
        if not service_id:
            return {
                "slots": updated_slots,
                "state": "need_service",
                "next_prompt": "Qual serviço você gostaria?"
            }
        
        if not date:
            return {
                "slots": updated_slots,
                "state": "need_date",
                "next_prompt": "Que dia gostaria? (hoje, amanhã, ou uma data específica)"
            }
        
        if not time:
            return {
                "slots": updated_slots,
                "state": "need_time",
                "next_prompt": "Que horário prefere?"
            }
        
        # Tem tudo! Ir para confirmação
        return {
            "slots": updated_slots,
            "state": "confirm",
            "next_prompt": f"Confirma agendamento para {updated_slots.get('date')} às {updated_slots.get('time')}?"
        }
    
    async def _handle_need_service(self, user_message: str, slots: Dict) -> Dict[str, Any]:
        """Coletar serviço"""
        
        service_id = await self._extract_service(user_message)
        
        if service_id:
            slots["service_id"] = service_id
            return {
                "slots": slots,
                "state": "need_date",
                "next_prompt": "Que dia gostaria?"
            }
        
        return {
            "slots": slots,
            "state": "need_service",
            "error": "Serviço não identificado. Por favor, escolha um serviço da lista.",
            "next_prompt": "Qual serviço você deseja?"
        }
    
    async def _handle_need_date(
        self, 
        user_message: str, 
        slots: Dict,
        now: datetime
    ) -> Dict[str, Any]:
        """Coletar data"""
        
        date = self.parser.parse_date_from_text(user_message, now)
        
        if date:
            slots["date"] = date.isoformat()
            
            # Perguntar janela (manhã/tarde) antes de horário específico
            return {
                "slots": slots,
                "state": "need_window",
                "next_prompt": "Prefere manhã ou tarde?"
            }
        
        return {
            "slots": slots,
            "state": "need_date",
            "error": "Data não entendida.",
            "next_prompt": "Que dia? (hoje, amanhã, próxima segunda, etc)"
        }
    
    async def _handle_need_window(self, user_message: str, slots: Dict) -> Dict[str, Any]:
        """Coletar janela (manhã/tarde/noite)"""
        
        window = self.parser.parse_window_from_text(user_message)
        
        if window:
            slots["window"] = window
            return {
                "slots": slots,
                "state": "need_time",
                "next_prompt": "Que horário prefere?"
            }
        
        # Se usuário já deu horário específico, pular janela
        time = self.parser.parse_time_from_text(user_message)
        if time:
            slots["time"] = f"{time.hour:02d}:{time.minute:02d}" if time.minute else f"{time.hour:02d}h"
            return {
                "slots": slots,
                "state": "confirm",
                "next_prompt": f"Confirma agendamento para {slots.get('date')} às {slots.get('time')}?"
            }
        
        return {
            "slots": slots,
            "state": "need_window",
            "error": "Não entendi. Manhã, tarde ou noite?",
            "next_prompt": "Prefere manhã, tarde ou noite?"
        }
    
    async def _handle_need_time(self, user_message: str, slots: Dict) -> Dict[str, Any]:
        """Coletar horário"""
        
        time = self.parser.parse_time_from_text(user_message)
        
        if time:
            slots["time"] = f"{time.hour:02d}:{time.minute:02d}" if time.minute else f"{time.hour:02d}h"
            return {
                "slots": slots,
                "state": "confirm",
                "next_prompt": f"Confirma agendamento para {slots.get('date')} às {slots.get('time')}?"
            }
        
        return {
            "slots": slots,
            "state": "need_time",
            "error": "Horário não entendido.",
            "next_prompt": "Que horário? (ex: 10h, 14:30, manhã, tarde)"
        }
    
    async def _handle_confirm(self, user_message: str, slots: Dict) -> Dict[str, Any]:
        """Estado de confirmação - aguardando sim/não"""
        
        # Analisar afirmação/negação
        text_lower = user_message.lower().strip()
        
        # Afirmações positivas
        if any(word in text_lower for word in ["sim", "confirmo", "ok", "pode", "isso", "certeza"]):
            return {
                "slots": slots,
                "state": "confirmed",
                "confirmed": True,
                "next_prompt": None
            }
        
        # Negações
        if any(word in text_lower for word in ["não", "nao", "cancel", "desist", "esquece"]):
            return {
                "slots": {},
                "state": "idle",
                "confirmed": False,
                "next_prompt": "Ok, cancelado. Em que posso ajudar?"
            }
        
        # Não entendeu - repetir pergunta
        return {
            "slots": slots,
            "state": "confirm",
            "next_prompt": f"Confirma o agendamento para {slots.get('date')} às {slots.get('time')}? (sim ou não)"
        }
    
    async def _extract_service(self, text: str) -> Optional[str]:
        """
        Extrair service_id do texto
        
        Nota: Implementação simplificada. Em produção, 
        deve consultar BD e fazer matching fuzzy
        """
        # TODO: implementar matching real com banco de dados
        # Por enquanto, retornar None para forçar pergunta
        return None
    
    def get_missing_slots(self, slots: Dict[str, Any]) -> list:
        """Retornar lista de slots faltantes para agendamento"""
        required = ["service_id", "date", "time", "client_whatsapp"]
        missing = [s for s in required if s not in slots or not slots[s]]
        return missing
    
    def is_complete(self, slots: Dict[str, Any]) -> bool:
        """Verificar se todos os slots necessários estão preenchidos"""
        return len(self.get_missing_slots(slots)) == 0

