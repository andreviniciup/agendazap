"""
ResponseGenerator - Gera respostas contextualizadas
Responsabilidade única: criar mensagens apropriadas ao contexto
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Gerador de respostas inteligente e contextualizado"""
    
    def __init__(self, templates, affirmation_analyzer):
        """
        Args:
            templates: Módulo de templates
            affirmation_analyzer: Analisador de afirmações/negações
        """
        self.templates = templates
        self.analyzer = affirmation_analyzer
    
    def generate(
        self, 
        intent: str, 
        confidence: float, 
        context: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> str:
        """
        Gerar resposta apropriada ao contexto
        
        Args:
            intent: Intenção detectada
            confidence: Nível de confiança (0-1)
            context: Contexto da mensagem (texto, user_name, etc)
            conversation_state: Estado da conversa (slots, history, etc)
            
        Returns:
            Mensagem de resposta
        """
        
        # Analisar tom da mensagem do usuário
        user_text = context.get("text", "")
        affirmation = self.analyzer.analyze_affirmation(user_text)
        
        logger.debug(f"💬 Gerando resposta - Intent: {intent}, Conf: {confidence:.2%}, Afirmação: {affirmation['type'].value}")
        
        # Se foi negação/rejeição, tratar especialmente
        if affirmation["type"].value in ["negative", "rejection"]:
            return self._handle_rejection(intent, context, conversation_state)
        
        # Gerar resposta baseada em confiança
        if confidence < 0.3:
            return self._generate_low_confidence(intent, context, conversation_state)
        
        elif 0.3 <= confidence < 0.6:
            return self._generate_medium_confidence(intent, context, conversation_state)
        
        else:  # confidence >= 0.6
            return self._generate_high_confidence(intent, context, conversation_state, affirmation)
    
    def _handle_rejection(
        self, 
        intent: str, 
        context: Dict, 
        conversation_state: Dict
    ) -> str:
        """Tratar negações e rejeições"""
        
        last_intent = conversation_state.get("last_intent")
        user_name = context.get("user_name", "")
        
        # Mensagens de empatia
        empathy_phrases = [
            f"Entendo{', ' + user_name if user_name else ''}.",
            "Sem problema!",
            "Tudo bem!",
            "Ok, entendi."
        ]
        
        # Oferecer alternativa
        alternatives = {
            "schedule": "Prefere escolher outro horário?",
            "services": "Quer saber sobre outro serviço?",
            "price": "Tem alguma dúvida?",
        }
        
        base = empathy_phrases[0]  # Poderia ser aleatório
        alt = alternatives.get(last_intent, "Como posso ajudar?")
        
        return f"{base} {alt}"
    
    def _generate_low_confidence(
        self, 
        intent: str, 
        context: Dict, 
        conversation_state: Dict
    ) -> str:
        """Resposta para baixa confiança - pedir esclarecimento"""
        
        state = conversation_state.get("state", "idle")
        
        # Se estamos em estado de coleta, repetir pergunta de forma mais clara
        if state == "asking_date":
            return "Que dia você prefere? (hoje, amanhã, ou diga uma data)"
        
        elif state == "asking_window":
            return "Prefere pela manhã, tarde ou noite?"
        
        elif state == "asking_time":
            return "Que horário você gostaria? (ex: 10h, 14:30)"
        
        # Estado idle - saudação genérica
        user_name = context.get("user_name", "")
        greeting = f"Olá{', ' + user_name if user_name else ''}! "
        
        return (
            f"{greeting}Não entendi muito bem. "
            "Posso ajudar com agendamentos, informações sobre serviços ou preços. "
            "O que você precisa?"
        )
    
    def _generate_medium_confidence(
        self, 
        intent: str, 
        context: Dict, 
        conversation_state: Dict
    ) -> str:
        """Resposta para confiança média - clarificar intenção"""
        
        user_name = context.get("user_name", "")
        
        clarifications = {
            "schedule": f"Você quer fazer um agendamento{', ' + user_name if user_name else ''}?",
            "services": "Quer saber sobre nossos serviços?",
            "price": "Está perguntando sobre preços?",
            "availability": "Quer saber horários disponíveis?",
            "about": "Quer mais informações sobre o que fazemos?",
        }
        
        clarify = clarifications.get(intent, "Pode me explicar melhor?")
        
        return f"{clarify} Responda sim ou não, ou me diga o que precisa!"
    
    def _generate_high_confidence(
        self, 
        intent: str, 
        context: Dict, 
        conversation_state: Dict,
        affirmation: Dict
    ) -> str:
        """Resposta para alta confiança - processamento normal"""
        
        user_name = context.get("user_name", "")
        service_name = context.get("service_name", "o serviço")
        
        # Modificador baseado em afirmação
        modifier = ""
        if affirmation["type"].value == "positive":
            modifier = self.analyzer.get_response_modifier(affirmation)
        
        # Templates por intenção
        templates_map = {
            "greeting": self._template_greeting,
            "schedule": self._template_schedule,
            "services": self._template_services,
            "price": self._template_price,
            "availability": self._template_availability,
            "about": self._template_about,
            "human": self._template_human,
            "confirm": self._template_confirm,
        }
        
        template_func = templates_map.get(intent, self._template_default)
        message = template_func(context, conversation_state)
        
        # Adicionar modificador de afirmação se houver
        if modifier:
            return f"{modifier} {message}"
        
        return message
    
    # Templates específicos por intenção
    
    def _template_greeting(self, context: Dict, state: Dict) -> str:
        user_name = context.get("user_name", "")
        greeting = f"Olá{', ' + user_name if user_name else ''}! "
        return f"{greeting}Como posso ajudar? Posso agendar serviços, informar preços ou tirar dúvidas."
    
    def _template_schedule(self, context: Dict, state: Dict) -> str:
        user_name = context.get("user_name", "")
        return f"Perfeito{', ' + user_name if user_name else ''}! Vou te ajudar a agendar. Que dia você prefere?"
    
    def _template_services(self, context: Dict, state: Dict) -> str:
        services_list = context.get("services_list", "")
        if services_list:
            return f"Estes são nossos serviços:\n\n{services_list}\n\nQual te interessa?"
        return "Posso te passar informações sobre nossos serviços. Qual te interessa?"
    
    def _template_price(self, context: Dict, state: Dict) -> str:
        service_name = context.get("service_name", "o serviço")
        price = context.get("price", "sob consulta")
        
        if price != "sob consulta":
            return f"{service_name}: {price}. Gostaria de agendar?"
        
        return f"Para saber o valor de {service_name}, entre em contato conosco. Quer agendar?"
    
    def _template_availability(self, context: Dict, state: Dict) -> str:
        time_options = context.get("time_options", "")
        if time_options:
            return f"Tenho disponibilidade: {time_options}. Qual prefere?"
        return "Quando você gostaria de agendar? Que dia e horário?"
    
    def _template_about(self, context: Dict, state: Dict) -> str:
        service_info = context.get("service_info", "")
        if service_info:
            return f"{service_info}\n\nGostaria de agendar?"
        return "Estou aqui para ajudar com agendamentos e informações. O que você gostaria de saber?"
    
    def _template_human(self, context: Dict, state: Dict) -> str:
        user_name = context.get("user_name", "")
        return (
            f"Entendo{', ' + user_name if user_name else ''}! "
            "Vou transferir você para um atendente humano. "
            "Aguarde um momento, por favor."
        )
    
    def _template_confirm(self, context: Dict, state: Dict) -> str:
        date = context.get("date", "")
        time = context.get("time", "")
        service = context.get("service_name", "o serviço")
        
        return f"Perfeito! Agendamento confirmado para {date} às {time} - {service}. Até lá! 🎉"
    
    def _template_default(self, context: Dict, state: Dict) -> str:
        return "Como posso ajudar você hoje?"
    
    def add_follow_up_question(self, message: str, intent: str, confidence: float) -> str:
        """
        Adicionar pergunta de acompanhamento relevante
        
        Args:
            message: Mensagem base
            intent: Intenção atual
            confidence: Confiança da detecção
            
        Returns:
            Mensagem com follow-up
        """
        
        # Apenas adicionar follow-up em alta confiança
        if confidence < 0.7:
            return message
        
        follow_ups = {
            "price": [
                "Gostaria de agendar?",
                "Quer saber sobre outros serviços?",
            ],
            "services": [
                "Qual desses te interessa?",
                "Quer agendar algum?",
            ],
            "about": [
                "Gostaria de mais detalhes?",
                "Posso agendar para você?",
            ],
        }
        
        questions = follow_ups.get(intent, [])
        if questions:
            # Escolher primeira (poderia ser aleatório)
            return f"{message}\n\n{questions[0]}"
        
        return message




