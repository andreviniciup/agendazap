"""
Regras de intenção para o bot baseado em palavras‑chave e regex
"""

from typing import Dict, List, Pattern, Any
import re
import unicodedata


class Intent:
    GREETING = "greeting"
    AVAILABILITY = "availability"
    SCHEDULE = "schedule"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    PRICE = "price"
    SERVICES = "services"
    ABOUT = "about"
    HOURS = "business_hours"
    ADDRESS = "address"
    PAYMENT = "payment"
    HUMAN = "human"
    UNKNOWN = "unknown"


class IntentRule:
    def __init__(
        self,
        name: str,
        patterns: List[str],
        synonyms: List[str] = None,
        negative_keywords: List[str] = None,
        entity_patterns: Dict[str, str] = None,
    ) -> None:
        self.name = name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.synonyms = [s.lower() for s in (synonyms or [])]
        self.negative_keywords = [n.lower() for n in (negative_keywords or [])]
        self.entity_patterns: Dict[str, Pattern[str]] = {
            k: re.compile(v, re.IGNORECASE) for k, v in (entity_patterns or {}).items()
        }


# Correções de typos e variações comuns (sem IA)
CORRECTIONS = {
    "serviç": "servic",
    "sevico": "servico",
    "sevicos": "servicos",
    "servi[çc]0s": "servicos",
    "preço": "preco",
    "preços": "precos",
    "preç": "prec",
    "valoes": "valores",
    "horarios": "horario",
    "horÃ¡rio": "horario",
    "funcionamento": "funciona",
    "whats": "whatsapp",
}


def normalize_and_correct(text: str) -> str:
    if not text:
        return ""
    s = text.strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # aplicar correções conhecidas
    for wrong, right in CORRECTIONS.items():
        try:
            s = re.sub(wrong, right, s)
        except re.error:
            # fallback simples
            s = s.replace(wrong, right)
    return s


def build_default_rules() -> List[IntentRule]:
    """Regras padrão em PT‑BR com padrões e sinônimos comuns."""
    rules: List[IntentRule] = [
        IntentRule(
            Intent.AVAILABILITY,
            patterns=[
                r"\b(horarios?|horario|hora|disponibilidade|disponivel|agenda[r]?)\b",
                r"\bquando\b",
                r"\btem\s+vagas?\b",
            ],
            synonyms=[
                "que horas tem", "tem horario", "abre quando", "tem horario hoje",
                "tem agenda", "qual horario disponivel",
            ],
        ),
        IntentRule(
            Intent.SCHEDULE,
            patterns=[
                r"\b(agendar|agendo|agende|marcar|marco|quero marcar|quero agendar)\b",
                r"\b(reservar|reserva)\b",
            ],
            synonyms=["quero fazer", "quero reservar", "quero um horario", "book"],
        ),
        IntentRule(
            Intent.RESCHEDULE,
            patterns=[r"\b(remarcar|remarco|mudar|trocar|alterar)\b"],
            synonyms=["alterar horario", "adiar", "remarcar horario"],
        ),
        IntentRule(
            Intent.CANCEL,
            patterns=[r"\b(cancelar|cancela|desmarcar|desmarca)\b"],
            synonyms=["nao vou", "vou cancelar", "quero cancelar"],
        ),
        IntentRule(
            Intent.PRICE,
            patterns=[
                r"\b(preco|precos|pre[çc]o|valor(es)?|custa|cobran[çc]a|tabela( de)? precos?)\b",
            ],
            synonyms=[
                "quanto fica", "quanto sai", "tabela", "precos", "valores", "preco",
                "quanto custa", "qual o valor", "lista de precos",
            ],
            negative_keywords=["preço antigo", "aumento de preço"],
        ),
        IntentRule(
            Intent.SERVICES,
            patterns=[r"\b(servico[s]?|servi[çc]o[s]?|lista de servicos?|catalogo)\b"],
            synonyms=[
                "catalogo", "o que vcs fazem", "opcoes", "tipos de servico", "cardapio",
                "menu", "portfolio", "servicos disponiveis",
            ],
        ),
        IntentRule(
            Intent.ABOUT,
            patterns=[
                r"\b(como funciona|como que funciona|como voces funcionam|como vocês funcionam|como e|como é)\b",
                r"\b(procedimento|processo|passo a passo)\b",
                r"\b(informacoes|informações|sobre)\b",
            ],
            synonyms=[
                "explicacao", "explicação", "como funciona o servico", "como funciona a depilacao",
            ],
        ),
        IntentRule(
            Intent.HOURS,
            patterns=[r"\b(horario de funcion|funciona de|abre|fecha|expediente)\b"],
            synonyms=["que horas funciona", "funciona hoje", "qual o horario"],
        ),
        IntentRule(
            Intent.ADDRESS,
            patterns=[r"\b(endereco|endere[çc]o|localiza[çc][aã]o|como chegar|mapa)\b"],
            synonyms=["onde fica", "como eu chego", "ponto de referencia"],
        ),
        IntentRule(
            Intent.PAYMENT,
            patterns=[r"\b(pagamento|pagar|pix|cart[aã]o|debito|credito|dinheiro|boleto)\b"],
            synonyms=["formas de pagamento", "aceita cartao", "aceita pix"],
        ),
        IntentRule(
            Intent.HUMAN,
            patterns=[r"\b(humano|atendente|falar com algu[eé]m|pessoa|suporte)\b"],
            synonyms=["falar com humano", "atendimento humano", "falar com atendente"],
        ),
        IntentRule(
            Intent.GREETING,
            patterns=[
                r"\b(oi|ola|ol[aá]|bom dia|boa tarde|boa noite|eai|e a[ií]|beleza|tudo bem)\b",
                r"\b(opa|eae|eai|blz|beleza|tchau|obrigado|obrigada|valeu)\b",
            ],
            synonyms=[
                "oi tudo bem", "ola tudo bem", "bom dia tudo bem", "boa tarde tudo bem",
                "boa noite tudo bem", "oi como vai", "ola como vai", "bom dia como vai",
                "boa tarde como vai", "boa noite como vai", "oi beleza", "ola beleza",
                "bom dia beleza", "boa tarde beleza", "boa noite beleza", "oi pessoal",
                "ola pessoal", "bom dia pessoal", "boa tarde pessoal", "boa noite pessoal",
                "oi gente", "ola gente", "bom dia gente", "boa tarde gente", "boa noite gente",
                "oi galera", "ola galera", "bom dia galera", "boa tarde galera", "boa noite galera",
                "tudo certo", "tudo tranquilo", "tudo otimo", "tudo perfeito", "valeu pela ajuda",
                "obrigado pela ajuda", "obrigada pela ajuda", "valeu pela atencao", "obrigado pela atencao",
                "obrigada pela atencao", "valeu pela atencao", "muito obrigado", "muito obrigada",
                "obrigado mesmo", "obrigada mesmo", "valeu mesmo", "vlw", "obrigado", "obrigada", "valeu"
            ],
        ),
    ]
    return rules


DEFAULT_RULES = build_default_rules()


