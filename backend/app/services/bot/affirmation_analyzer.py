"""
Analisador de afirmações e negações para melhor compreensão do contexto
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum


class AffirmationType(Enum):
    POSITIVE = "positive"      # "sim", "ok", "certo", "perfeito"
    NEGATIVE = "negative"      # "não", "nunca", "jamais", "nada"
    UNCERTAIN = "uncertain"    # "talvez", "pode ser", "não sei"
    CONFIRMATION = "confirmation"  # "confirmo", "exato", "isso mesmo"
    REJECTION = "rejection"    # "não quero", "não preciso", "recuso"


class AffirmationAnalyzer:
    """Analisador de afirmações e negações"""
    
    def __init__(self):
        # Padrões de afirmação
        self.positive_patterns = [
            r"\b(sim|s|yes|y|ok|okay|beleza|perfeito|ótimo|excelente|maravilhoso)\b",
            r"\b(certo|correto|exato|isso mesmo|exatamente|preciso|quero|gostaria)\b",
            r"\b(confirmo|confirmado|aceito|aceito|concordo|concordado)\b",
            r"\b(obrigado|obrigada|valeu|vlw|obg|obrigad)\b",
            r"\b(entendi|entendido|compreendi|compreendido|captei)\b",
            r"\b(legal|bacana|massa|show|top|demais|incrível)\b",
            r"\b(ótimo|otimo|perfeito|excelente|maravilhoso|fantástico)\b",
            r"\b(tenho|posso|consigo|conseguir|fazer|realizar)\b",
            r"\b(disponível|livre|tem|tem sim|tem disponível)\b",
            r"\b(interessado|interesse|curioso|quero saber|gostaria de saber)\b"
        ]
        
        # Padrões de negação
        self.negative_patterns = [
            r"\b(não|nao|n|no|nunca|jamais|nada|nenhum|nenhuma)\b",
            r"\b(recuso|recusar|recusado|negado|negado|rejeitado)\b",
            r"\b(não quero|nao quero|não preciso|nao preciso|não gosto|nao gosto)\b",
            r"\b(não tenho|nao tenho|não posso|nao posso|não consigo|nao consigo)\b",
            r"\b(não disponível|nao disponivel|não livre|nao livre|ocupado)\b",
            r"\b(não interessado|nao interessado|não tenho interesse|nao tenho interesse)\b",
            r"\b(cancelar|cancelado|cancelamento|desistir|desistido)\b",
            r"\b(impossível|impossivel|não dá|nao da|não rola|nao rola)\b",
            r"\b(recusar|recusado|negar|negado|rejeitar|rejeitado)\b",
            r"\b(não aceito|nao aceito|não concordo|nao concordo)\b"
        ]
        
        # Padrões de incerteza
        self.uncertain_patterns = [
            r"\b(talvez|pode ser|pode ser que|não sei|nao sei|não tenho certeza|nao tenho certeza)\b",
            r"\b(acho que|creio que|parece que|aparenta ser|provavelmente)\b",
            r"\b(quem sabe|se der|se conseguir|se for possível|se der certo)\b",
            r"\b(depende|dependendo|vou ver|vou pensar|preciso pensar)\b",
            r"\b(não tenho certeza|nao tenho certeza|não sei bem|nao sei bem)\b",
            r"\b(meio|mais ou menos|assim assim|nem sim nem não|nem sim nem nao)\b"
        ]
        
        # Padrões de confirmação
        self.confirmation_patterns = [
            r"\b(confirmo|confirmado|exato|isso mesmo|exatamente|correto)\b",
            r"\b(perfeito|ótimo|otimo|excelente|maravilhoso|fantástico)\b",
            r"\b(entendi|entendido|compreendi|compreendido|captei)\b",
            r"\b(aceito|aceito|concordo|concordado|aprovado)\b",
            r"\b(isso|isso aí|isso mesmo|exatamente isso|perfeito)\b"
        ]
        
        # Padrões de rejeição
        self.rejection_patterns = [
            r"\b(não quero|nao quero|não preciso|nao preciso|não gosto|nao gosto)\b",
            r"\b(recuso|recusar|recusado|negado|negado|rejeitado)\b",
            r"\b(não aceito|nao aceito|não concordo|nao concordo|discordo)\b",
            r"\b(cancelar|cancelado|cancelamento|desistir|desistido)\b",
            r"\b(não|nao|nunca|jamais|nada|nenhum|nenhuma)\b"
        ]
        
        # Palavras de intensidade
        self.intensity_words = {
            "muito": 2.0,
            "muito": 2.0,
            "super": 2.5,
            "extremamente": 3.0,
            "totalmente": 3.0,
            "completamente": 3.0,
            "bastante": 1.5,
            "um pouco": 0.5,
            "pouco": 0.3,
            "ligeiramente": 0.4
        }
    
    def analyze_affirmation(self, text: str) -> Dict[str, any]:
        """
        Analisa afirmações e negações no texto
        
        Args:
            text: Texto para analisar
            
        Returns:
            Dict com informações sobre afirmações/negações
        """
        text_lower = text.lower().strip()
        
        # Detectar tipo de afirmação
        affirmation_type = self._detect_affirmation_type(text_lower)
        
        # Calcular intensidade
        intensity = self._calculate_intensity(text_lower)
        
        # Detectar contexto
        context = self._extract_context(text_lower)
        
        # Detectar negação dupla
        double_negative = self._detect_double_negative(text_lower)
        
        return {
            "type": affirmation_type,
            "intensity": intensity,
            "context": context,
            "double_negative": double_negative,
            "confidence": self._calculate_confidence(text_lower, affirmation_type),
            "original_text": text
        }
    
    def _detect_affirmation_type(self, text: str) -> AffirmationType:
        """Detecta o tipo de afirmação"""
        
        # Verificar negação primeiro (mais específico)
        for pattern in self.negative_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AffirmationType.NEGATIVE
        
        # Verificar rejeição
        for pattern in self.rejection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AffirmationType.REJECTION
        
        # Verificar confirmação
        for pattern in self.confirmation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AffirmationType.CONFIRMATION
        
        # Verificar incerteza
        for pattern in self.uncertain_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AffirmationType.UNCERTAIN
        
        # Verificar afirmação positiva
        for pattern in self.positive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AffirmationType.POSITIVE
        
        return AffirmationType.UNCERTAIN
    
    def _calculate_intensity(self, text: str) -> float:
        """Calcula intensidade da afirmação/negação"""
        intensity = 1.0
        
        for word, multiplier in self.intensity_words.items():
            if word in text:
                intensity *= multiplier
        
        return min(intensity, 3.0)  # Cap em 3.0
    
    def _extract_context(self, text: str) -> Dict[str, str]:
        """Extrai contexto da afirmação/negação"""
        context = {
            "subject": "",
            "action": "",
            "object": ""
        }
        
        # Padrões para extrair contexto
        subject_patterns = [
            r"\b(eu|me|mim|minha|meu|nós|nos|nossa|nosso)\b",
            r"\b(você|voce|vocês|voces|você|voce)\b",
            r"\b(eles|elas|deles|delas)\b"
        ]
        
        action_patterns = [
            r"\b(quero|preciso|gostaria|desejo|pretendo|vou|farei)\b",
            r"\b(aceito|concordo|confirmo|aprovo|aceito)\b",
            r"\b(recuso|nego|rejeito|desaprovo|discordo)\b",
            r"\b(agendar|marcar|reservar|fazer|realizar)\b",
            r"\b(cancelar|desmarcar|remarcar|alterar)\b"
        ]
        
        object_patterns = [
            r"\b(horário|horario|agendamento|consulta|serviço|servico)\b",
            r"\b(preço|preco|valor|custo|tabela)\b",
            r"\b(informação|informacao|detalhe|explicação|explicacao)\b"
        ]
        
        # Extrair sujeito
        for pattern in subject_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context["subject"] = match.group()
                break
        
        # Extrair ação
        for pattern in action_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context["action"] = match.group()
                break
        
        # Extrair objeto
        for pattern in object_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context["object"] = match.group()
                break
        
        return context
    
    def _detect_double_negative(self, text: str) -> bool:
        """Detecta negação dupla"""
        negative_count = 0
        for pattern in self.negative_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            negative_count += len(matches)
        
        return negative_count >= 2
    
    def _calculate_confidence(self, text: str, affirmation_type: AffirmationType) -> float:
        """Calcula confiança da análise"""
        confidence = 0.5  # Base
        
        # Aumentar confiança baseado no tipo
        if affirmation_type == AffirmationType.POSITIVE:
            confidence += 0.3
        elif affirmation_type == AffirmationType.NEGATIVE:
            confidence += 0.3
        elif affirmation_type == AffirmationType.CONFIRMATION:
            confidence += 0.4
        elif affirmation_type == AffirmationType.REJECTION:
            confidence += 0.4
        elif affirmation_type == AffirmationType.UNCERTAIN:
            confidence += 0.2
        
        # Aumentar confiança se há palavras de intensidade
        for word in self.intensity_words:
            if word in text:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_response_modifier(self, analysis: Dict[str, any]) -> str:
        """Retorna modificador de resposta baseado na análise"""
        
        affirmation_type = analysis["type"]
        intensity = analysis["intensity"]
        
        if affirmation_type == AffirmationType.POSITIVE:
            if intensity > 1.5:
                return "Perfeito! Vou te ajudar com isso."
            else:
                return "Ótimo! Vou te ajudar."
        
        elif affirmation_type == AffirmationType.NEGATIVE:
            if intensity > 1.5:
                return "Entendo que você não quer isso. Vou te ajudar com outra coisa."
            else:
                return "Entendo. Vou te ajudar com outra opção."
        
        elif affirmation_type == AffirmationType.CONFIRMATION:
            return "Perfeito! Confirmado."
        
        elif affirmation_type == AffirmationType.REJECTION:
            return "Entendo que você não quer isso. Vou te ajudar com outra coisa."
        
        elif affirmation_type == AffirmationType.UNCERTAIN:
            return "Entendo que você tem dúvidas. Vou te explicar melhor."
        
        return "Entendi. Vou te ajudar."
    
    def should_continue_conversation(self, analysis: Dict[str, any]) -> bool:
        """Determina se deve continuar a conversa baseado na análise"""
        
        affirmation_type = analysis["type"]
        
        # Continuar se for positiva ou confirmação
        if affirmation_type in [AffirmationType.POSITIVE, AffirmationType.CONFIRMATION]:
            return True
        
        # Continuar se for incerta (precisa de esclarecimento)
        if affirmation_type == AffirmationType.UNCERTAIN:
            return True
        
        # Não continuar se for negação ou rejeição
        if affirmation_type in [AffirmationType.NEGATIVE, AffirmationType.REJECTION]:
            return False
        
        return True



