"""
EnhancedParser - Parser robusto com NLP para datas, horas e entidades
Suporta linguagem natural em português: 'hoje', 'amanhã', 'próxima segunda', etc.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class EnhancedParser:
    """Parser melhorado que captura mais variações de linguagem natural"""
    
    # Mapeamento de meses
    MONTHS_PT = {
        "janeiro": 1, "jan": 1,
        "fevereiro": 2, "fev": 2,
        "março": 3, "mar": 3, "marco": 3,
        "abril": 4, "abr": 4,
        "maio": 5, "mai": 5,
        "junho": 6, "jun": 6,
        "julho": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "setembro": 9, "set": 9,
        "outubro": 10, "out": 10,
        "novembro": 11, "nov": 11,
        "dezembro": 12, "dez": 12,
    }
    
    # Dias da semana
    WEEKDAYS_PT = {
        "segunda": 0, "segunda-feira": 0, "seg": 0,
        "terça": 1, "terca": 1, "terça-feira": 1, "terca-feira": 1, "ter": 1,
        "quarta": 2, "quarta-feira": 2, "qua": 2,
        "quinta": 3, "quinta-feira": 3, "qui": 3,
        "sexta": 4, "sexta-feira": 4, "sex": 4,
        "sábado": 5, "sabado": 5, "sáb": 5, "sab": 5,
        "domingo": 6, "dom": 6,
    }
    
    def __init__(self):
        """Inicializar parser"""
        pass
    
    def parse_date(self, text: str, base_date: Optional[datetime] = None) -> Optional[date]:
        """
        Captura datas em linguagem natural
        
        Suporta:
        - 'hoje', 'amanhã', 'depois de amanhã'
        - 'próxima segunda', 'terça que vem'
        - '23 de março', '15 de dezembro'
        - '23/03', '15/12/2024'
        
        Args:
            text: Texto com possível data
            base_date: Data base (default: agora)
            
        Returns:
            Objeto date ou None
        """
        if not base_date:
            base_date = datetime.now()
        
        text_lower = text.lower().strip()
        
        # Normalizar variações de caracteres
        text_lower = self._normalize_text(text_lower)
        
        # 1. Datas relativas simples (ordem importa - mais específicos primeiro)
        relative_dates = {
            r"\bhoje\b": base_date.date(),
            r"\bdepois de amanha\b": (base_date + timedelta(days=2)).date(),  # Mais específico primeiro
            r"\bamanha\b": (base_date + timedelta(days=1)).date(),
            r"\bdaqui a 2 dias\b": (base_date + timedelta(days=2)).date(),
            r"\bdaqui a 3 dias\b": (base_date + timedelta(days=3)).date(),
        }
        
        for pattern, date_value in relative_dates.items():
            if re.search(pattern, text_lower):
                logger.debug(f"📅 Data relativa encontrada: {date_value}")
                return date_value
        
        # 2. Dias da semana (próxima segunda, terça que vem, etc)
        weekday_match = re.search(
            r"\b(proxima?|que vem|essa?|esta?)\s+(" + "|".join(self.WEEKDAYS_PT.keys()) + r")\b",
            text_lower
        )
        if weekday_match:
            weekday_name = weekday_match.group(2)
            weekday_num = self.WEEKDAYS_PT.get(weekday_name)
            if weekday_num is not None:
                result = self._next_weekday(base_date, weekday_num)
                logger.debug(f"📅 Dia da semana encontrado: {weekday_name} → {result}")
                return result
        
        # Também capturar apenas o dia da semana sem "próxima"
        for weekday_name, weekday_num in self.WEEKDAYS_PT.items():
            if re.search(r"\b" + weekday_name + r"\b", text_lower):
                result = self._next_weekday(base_date, weekday_num)
                logger.debug(f"📅 Dia da semana implícito: {weekday_name} → {result}")
                return result
        
        # 3. Formato "23 de março", "15 de dezembro"
        month_pattern = r"\b(\d{1,2})\s+de\s+(" + "|".join(self.MONTHS_PT.keys()) + r")\b"
        month_match = re.search(month_pattern, text_lower)
        if month_match:
            day = int(month_match.group(1))
            month_name = month_match.group(2)
            month = self.MONTHS_PT.get(month_name)
            
            if month:
                # Usar ano atual ou próximo se já passou
                year = base_date.year
                try:
                    result = date(year, month, day)
                    # Se data no passado, usar próximo ano
                    if result < base_date.date():
                        result = date(year + 1, month, day)
                    logger.debug(f"📅 Data por extenso: {day}/{month} → {result}")
                    return result
                except ValueError:
                    logger.warning(f"⚠️ Data inválida: {day}/{month}/{year}")
                    return None
        
        # 4. Formato "23/03", "15/12", "23/03/2024"
        slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?\b", text_lower)
        if slash_match:
            day = int(slash_match.group(1))
            month = int(slash_match.group(2))
            year_str = slash_match.group(3)
            
            if year_str:
                year = int(year_str)
                if year < 100:  # Ano com 2 dígitos
                    year += 2000
            else:
                year = base_date.year
                # Se data no passado, usar próximo ano
                try:
                    temp = date(year, month, day)
                    if temp < base_date.date():
                        year += 1
                except ValueError:
                    pass
            
            try:
                result = date(year, month, day)
                logger.debug(f"📅 Data slash: {day}/{month}/{year} → {result}")
                return result
            except ValueError:
                logger.warning(f"⚠️ Data inválida: {day}/{month}/{year}")
                return None
        
        logger.debug(f"❌ Nenhuma data encontrada em: '{text}'")
        return None
    
    def parse_time(self, text: str) -> Optional[time]:
        """
        Captura horários em linguagem natural
        
        Suporta:
        - '10h', '14:30', '10h30'
        - 'manhã', 'meio dia', 'tarde', 'noite'
        - 'cedo', 'final da tarde'
        
        Args:
            text: Texto com possível horário
            
        Returns:
            Objeto time ou None
        """
        text_lower = text.lower().strip()
        text_lower = self._normalize_text(text_lower)
        
        # 1. Horários específicos: 10h, 14:30, 10h30
        time_patterns = [
            (r"\b(\d{1,2})h(\d{2})\b", lambda m: time(int(m.group(1)), int(m.group(2)))),
            (r"\b(\d{1,2}):(\d{2})\b", lambda m: time(int(m.group(1)), int(m.group(2)))),
            (r"\b(\d{1,2})h(?:oras?)?\b", lambda m: time(int(m.group(1)), 0)),
        ]
        
        for pattern, time_func in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result = time_func(match)
                    logger.debug(f"⏰ Horário específico: {result}")
                    return result
                except ValueError:
                    logger.warning(f"⚠️ Horário inválido: {match.group(0)}")
                    continue
        
        # 2. Períodos do dia (ordem importa - mais específicos primeiro)
        period_times = {
            r"\b(cedo|madrugada|bem cedo)\b": time(6, 0),
            r"\b(manha|de manha|pela manha)\b": time(9, 0),
            r"\b(meio[- ]?dia|12h|12:00)\b": time(12, 0),
            r"\b(final da tarde|final de tarde|fim de tarde)\b": time(17, 0),  # Mais específico primeiro
            r"\b(tarde|de tarde|pela tarde)\b": time(14, 0),
            r"\b(noite|de noite|noitinha|a noite)\b": time(19, 0),
        }
        
        for pattern, time_obj in period_times.items():
            if re.search(pattern, text_lower):
                logger.debug(f"⏰ Período do dia: {time_obj}")
                return time_obj
        
        logger.debug(f"❌ Nenhum horário encontrado em: '{text}'")
        return None
    
    def parse_window(self, text: str) -> Optional[str]:
        """
        Captura janela de horário (morning/afternoon/evening)
        
        Args:
            text: Texto com possível janela
            
        Returns:
            'morning', 'afternoon', 'evening' ou None
        """
        text_lower = text.lower().strip()
        text_lower = self._normalize_text(text_lower)
        
        window_patterns = {
            "morning": [r"\bmanha\b", r"\bde manha\b", r"\bpela manha\b", r"\bcedo\b"],
            "afternoon": [r"\btarde\b", r"\bde tarde\b", r"\bpela tarde\b"],
            "evening": [r"\bnoite\b", r"\bde noite\b", r"\ba noite\b", r"\bnoitinha\b"],
        }
        
        for window, patterns in window_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    logger.debug(f"🕐 Janela encontrada: {window}")
                    return window
        
        logger.debug(f"❌ Nenhuma janela encontrada em: '{text}'")
        return None
    
    def parse_phone(self, text: str) -> Optional[str]:
        """
        Extrair número de telefone
        
        Suporta:
        - (11) 98765-4321
        - 11987654321
        - +55 11 98765-4321
        
        Args:
            text: Texto com possível telefone
            
        Returns:
            Telefone normalizado ou None
        """
        # Remover formatação comum
        clean = re.sub(r'[\s\-\(\)]+', '', text)
        
        # Padrões de telefone brasileiro
        patterns = [
            r'\+?55(\d{2})9?\d{8}',  # +55 11 987654321
            r'(\d{2})9?\d{8}',       # 11 987654321
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean)
            if match:
                # Normalizar para formato +55XXXXXXXXXXX
                digits = re.sub(r'\D', '', match.group(0))
                if len(digits) == 11:  # DDD + número
                    result = f"+55{digits}"
                    logger.debug(f"📱 Telefone encontrado: {result}")
                    return result
                elif len(digits) == 13 and digits.startswith('55'):  # Já tem +55
                    result = f"+{digits}"
                    logger.debug(f"📱 Telefone encontrado: {result}")
                    return result
        
        return None
    
    def parse_name(self, text: str) -> Optional[str]:
        """
        Extrair nome próprio do texto
        
        Heurística simples: palavras capitalizadas
        """
        # Procurar padrão "meu nome é X" ou "me chamo X"
        name_patterns = [
            r"nome [eé]\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",  # "nome é João"
            r"(?:meu nome [eé]|me chamo|sou o?a?)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            r"\b([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){0,2})\b",  # Palavras capitalizadas
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Validar que não é palavra comum
                common_words = {"Whatsapp", "Bot", "Agenda", "Por", "Favor", "Obrigado", "Oi", "Olá", "Meu", "Nome", "É", "Sou", "O", "A"}
                if name not in common_words and len(name) > 2:
                    logger.debug(f"👤 Nome encontrado: {name}")
                    return name
        
        return None
    
    def extract_entities(self, text: str, base_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extrair todas as entidades de uma vez
        
        Args:
            text: Texto do usuário
            base_date: Data base para parsing relativo
            
        Returns:
            Dict com entidades extraídas: {date, time, window, phone, name}
        """
        entities = {}
        
        # Extrair cada tipo de entidade
        parsed_date = self.parse_date(text, base_date)
        if parsed_date:
            entities["date"] = parsed_date
        
        parsed_time = self.parse_time(text)
        if parsed_time:
            entities["time"] = parsed_time
        
        parsed_window = self.parse_window(text)
        if parsed_window:
            entities["window"] = parsed_window
        
        parsed_phone = self.parse_phone(text)
        if parsed_phone:
            entities["phone"] = parsed_phone
        
        parsed_name = self.parse_name(text)
        if parsed_name:
            entities["name"] = parsed_name
        
        logger.debug(f"📦 Entidades extraídas: {list(entities.keys())}")
        
        return entities
    
    # Métodos auxiliares
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto removendo acentos e pontuação desnecessária"""
        import unicodedata
        
        # Remover acentos mas manter ç
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn' or c in ['ç', 'Ç']
        )
        
        # Substituir ç por c para facilitar matching
        text = text.replace('ç', 'c').replace('Ç', 'c')
        
        return text
    
    def _next_weekday(self, base_date: datetime, weekday: int) -> date:
        """
        Calcular próxima ocorrência de dia da semana
        
        Args:
            base_date: Data base
            weekday: Dia da semana (0=segunda, 6=domingo)
            
        Returns:
            Próxima data desse dia da semana
        """
        days_ahead = weekday - base_date.weekday()
        
        # Se é o mesmo dia ou já passou, pegar próxima semana
        if days_ahead <= 0:
            days_ahead += 7
        
        result = (base_date + timedelta(days=days_ahead)).date()
        logger.debug(f"📅 Próximo(a) {weekday}: {result}")
        return result
    
    def _parse_full_date(self, match: re.Match, base_year: Optional[int] = None) -> Optional[date]:
        """Parser para formato '23 de março'"""
        try:
            day = int(match.group(1))
            month_name = match.group(2)
            month = self.MONTHS_PT.get(month_name)
            
            if not month:
                return None
            
            year = base_year or datetime.now().year
            result = date(year, month, day)
            
            # Se no passado, usar próximo ano
            if result < datetime.now().date():
                result = date(year + 1, month, day)
            
            return result
        except ValueError:
            return None
    
    def _parse_slash_date(self, match: re.Match) -> Optional[date]:
        """Parser para formato '23/03' ou '23/03/2024'"""
        try:
            day = int(match.group(1))
            month = int(match.group(2))
            year_str = match.group(3) if match.lastindex >= 3 else None
            
            if year_str:
                year = int(year_str)
                if year < 100:  # Ano com 2 dígitos
                    year += 2000
            else:
                year = datetime.now().year
                # Se no passado, usar próximo ano
                temp = date(year, month, day)
                if temp < datetime.now().date():
                    year += 1
            
            return date(year, month, day)
        except ValueError:
            return None
    
    def format_date_friendly(self, dt: date) -> str:
        """Formatar data de forma amigável em português"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        if dt == today:
            return "hoje"
        elif dt == tomorrow:
            return "amanhã"
        elif dt == today + timedelta(days=2):
            return "depois de amanhã"
        else:
            # Formato: "segunda, 23/03"
            weekday_names = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
            weekday = weekday_names[dt.weekday()]
            return f"{weekday}, {dt.strftime('%d/%m')}"
    
    def format_time_friendly(self, t: time) -> str:
        """Formatar horário de forma amigável"""
        if t.minute == 0:
            return f"{t.hour}h"
        return f"{t.hour:02d}:{t.minute:02d}"


# Funções de compatibilidade com código existente
def parse_date_from_text(text: str, base_date: Optional[datetime] = None) -> Optional[date]:
    """Função de compatibilidade com código antigo"""
    parser = EnhancedParser()
    return parser.parse_date(text, base_date)


def parse_time_from_text(text: str) -> Optional[time]:
    """Função de compatibilidade com código antigo"""
    parser = EnhancedParser()
    return parser.parse_time(text)


def parse_window_from_text(text: str) -> Optional[str]:
    """Função de compatibilidade com código antigo"""
    parser = EnhancedParser()
    return parser.parse_window(text)


# Adicionar métodos de compatibilidade à classe EnhancedParser
def _add_compatibility_methods():
    """Adicionar métodos de compatibilidade à classe EnhancedParser"""
    
    def parse_date_from_text(self, text: str, base_date: Optional[datetime] = None) -> Optional[date]:
        """Método de compatibilidade"""
        return self.parse_date(text, base_date)
    
    def parse_time_from_text(self, text: str) -> Optional[time]:
        """Método de compatibilidade"""
        return self.parse_time(text)
    
    def parse_window_from_text(self, text: str) -> Optional[str]:
        """Método de compatibilidade"""
        return self.parse_window(text)
    
    # Adicionar métodos à classe
    EnhancedParser.parse_date_from_text = parse_date_from_text
    EnhancedParser.parse_time_from_text = parse_time_from_text
    EnhancedParser.parse_window_from_text = parse_window_from_text

# Executar a adição dos métodos
_add_compatibility_methods()

