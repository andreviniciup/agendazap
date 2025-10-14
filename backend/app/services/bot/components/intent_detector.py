"""
IntentDetector - Detecta intenção com fallback automático entre regras e ML
Responsabilidade única: determinar a intenção do usuário
"""

from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detector de intenção híbrido (regras + ML)"""
    
    def __init__(self, intent_engine, classifier, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            intent_engine: Motor de regras (IntentEngine)
            classifier: Classificador ML (BotClassifier)
            config: Configurações opcionais (thresholds, etc)
        """
        self.engine = intent_engine
        self.classifier = classifier
        self.config = config or {}
        
        # Thresholds configuráveis
        self.rule_confidence_threshold = self.config.get("rule_confidence_threshold", 0.8)
        self.ml_min_confidence = self.config.get("ml_min_confidence", 0.6)
        self.ml_improvement_margin = self.config.get("ml_improvement_margin", 0.15)
        self.min_words_for_ml = self.config.get("min_words_for_ml", 3)
    
    async def detect(self, text: str, context: Optional[Dict] = None) -> Tuple[str, float, str]:
        """
        Detectar intenção com fallback automático
        
        Args:
            text: Texto do usuário
            context: Contexto adicional (histórico, estado, etc)
            
        Returns:
            Tuple[intent, confidence, source] - intenção, confiança (0-1), fonte ('rule' ou 'ml')
        """
        if not text:
            return "unknown", 0.0, "none"
        
        context = context or {}
        
        # 1. REGRA (rápido e determinístico)
        rule_intent, rule_entities, rule_conf = self.engine.detect(text)
        logger.debug(f"🔍 REGRA: {rule_intent} ({rule_conf:.2%}) - '{text}'")
        
        # 2. DECIDIR SE USA ML
        use_ml = self._should_use_ml(text, rule_conf, context)
        
        if not use_ml:
            logger.debug(f"⏭️ PULANDO ML (regra confiante ou texto curto)")
            return rule_intent, rule_conf, "rule"
        
        # 3. TENTAR ML
        ml_intent, ml_conf = self.classifier.classify(text)
        logger.debug(f"🤖 ML: {ml_intent} ({ml_conf:.2%})")
        
        # 4. DECIDIR QUAL USAR
        final_intent, final_conf, source = self._choose_best(
            rule_intent, rule_conf,
            ml_intent, ml_conf,
            context
        )
        
        logger.info(f"✅ INTENT FINAL: {final_intent} ({final_conf:.2%}) via {source.upper()}")
        
        return final_intent, final_conf, source
    
    def _should_use_ml(self, text: str, rule_conf: float, context: Dict) -> bool:
        """Decidir se deve usar ML baseado em heurísticas"""
        
        # ML não disponível
        if not self.classifier.ready:
            return False
        
        word_count = len(text.split())
        
        # Sempre usar ML para frases longas ou regra incerta
        should_use = (
            rule_conf < self.rule_confidence_threshold or  # Regra incerta
            word_count > self.min_words_for_ml or  # Frase longa
            rule_conf < 0.6  # Regra com baixa confiança
        )
        
        return should_use
    
    def _choose_best(
        self, 
        rule_intent: str, 
        rule_conf: float,
        ml_intent: str, 
        ml_conf: float,
        context: Dict
    ) -> Tuple[str, float, str]:
        """
        Escolher melhor predição entre regra e ML
        
        Estratégia:
        - ML vence se: confiança > threshold E (confiança > regra OU regra muito incerta)
        - Regra vence nos demais casos (mais conservador)
        """
        
        # ML precisa ter confiança mínima
        if ml_conf < self.ml_min_confidence:
            logger.debug(f"❌ ML confiança baixa ({ml_conf:.2%} < {self.ml_min_confidence:.2%})")
            return rule_intent, rule_conf, "rule"
        
        # ML vence se significativamente melhor que regra
        if ml_conf > rule_conf + self.ml_improvement_margin:
            logger.debug(f"✅ ML vence (margem: {ml_conf - rule_conf:.2%})")
            return ml_intent, ml_conf, "ml"
        
        # ML vence se regra muito incerta
        if ml_conf > rule_conf and rule_conf < 0.5:
            logger.debug(f"✅ ML vence (regra incerta: {rule_conf:.2%})")
            return ml_intent, ml_conf, "ml"
        
        # Padrão: manter regra (mais conservador)
        logger.debug(f"❌ MANTENDO REGRA (conf: {rule_conf:.2%})")
        return rule_intent, rule_conf, "rule"


class ContextAwareIntentDetector(IntentDetector):
    """
    Detector de intenção que usa histórico da conversa para desambiguar
    """
    
    def __init__(self, intent_engine, classifier, config: Optional[Dict[str, Any]] = None):
        super().__init__(intent_engine, classifier, config)
    
    async def detect(self, text: str, context: Optional[Dict] = None) -> Tuple[str, float, str]:
        """Detectar intenção considerando contexto anterior"""
        
        # Detecção base
        base_intent, base_conf, source = await super().detect(text, context)
        
        # Se confiança alta, retornar direto
        if base_conf > 0.8:
            return base_intent, base_conf, source
        
        # Tentar melhorar com contexto
        if context and "history" in context and len(context["history"]) > 0:
            enhanced_intent, enhanced_conf = self._enhance_with_context(
                text, base_intent, base_conf, context
            )
            
            if enhanced_conf > base_conf:
                logger.info(f"📈 Contexto melhorou confiança: {base_conf:.2%} → {enhanced_conf:.2%}")
                return enhanced_intent, enhanced_conf, "context"
        
        return base_intent, base_conf, source
    
    def _enhance_with_context(
        self, 
        text: str, 
        base_intent: str, 
        base_conf: float, 
        context: Dict
    ) -> Tuple[str, float]:
        """Melhorar detecção usando histórico"""
        
        history = context.get("history", [])
        if not history:
            return base_intent, base_conf
        
        last_turn = history[-1]
        last_intent = last_turn.get("intent")
        current_state = context.get("state", "idle")
        
        # Regras contextuais
        word_count = len(text.split())
        
        # Se última intenção foi "services" e resposta curta, provavelmente é seleção
        if last_intent == "services" and word_count <= 3:
            logger.debug(f"🔄 Contexto: última intent=services, resposta curta → select_service")
            return "select_service", 0.75
        
        # Se foi perguntando data e tem número, é confirmação de data
        if current_state == "asking_date" and any(char.isdigit() for char in text):
            logger.debug(f"🔄 Contexto: estado=asking_date, tem número → confirm_date")
            return "confirm_date", 0.8
        
        # Se foi perguntando horário e tem padrão de hora
        if current_state in ("asking_time", "asking_window"):
            import re
            if re.search(r'\d{1,2}h|\d{1,2}:\d{2}|manhã|tarde|noite', text.lower()):
                logger.debug(f"🔄 Contexto: estado={current_state}, tem hora → confirm_time")
                return "confirm_time", 0.8
        
        # Padrão: retornar base
        return base_intent, base_conf

