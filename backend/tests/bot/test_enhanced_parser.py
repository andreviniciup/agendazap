"""
Testes para EnhancedParser
"""

import pytest
from datetime import datetime, date, time, timedelta
from app.services.bot.enhanced_parser import EnhancedParser


@pytest.fixture
def parser():
    """Fixture para parser"""
    return EnhancedParser()


@pytest.fixture
def base_date():
    """Data base para testes (segunda-feira, 15/01/2024)"""
    return datetime(2024, 1, 15, 10, 0, 0)  # Segunda-feira


class TestDateParsing:
    """Testes de parsing de datas"""
    
    def test_relative_dates(self, parser, base_date):
        """Testar datas relativas"""
        # Hoje
        result = parser.parse_date("quero para hoje", base_date)
        assert result == base_date.date()
        
        # Amanhã
        result = parser.parse_date("amanhã", base_date)
        assert result == (base_date + timedelta(days=1)).date()
        
        # Depois de amanhã
        result = parser.parse_date("depois de amanhã", base_date)
        assert result == (base_date + timedelta(days=2)).date()
    
    def test_weekday_parsing(self, parser, base_date):
        """Testar dias da semana"""
        # Próxima segunda (base é segunda, então próxima semana)
        result = parser.parse_date("próxima segunda", base_date)
        expected = (base_date + timedelta(days=7)).date()
        assert result == expected
        
        # Próxima terça
        result = parser.parse_date("próxima terça", base_date)
        expected = (base_date + timedelta(days=1)).date()
        assert result == expected
        
        # Sexta que vem
        result = parser.parse_date("sexta que vem", base_date)
        expected = (base_date + timedelta(days=4)).date()
        assert result == expected
    
    def test_month_date_parsing(self, parser, base_date):
        """Testar formato '23 de março'"""
        # Data futura
        result = parser.parse_date("23 de março", base_date)
        assert result.day == 23
        assert result.month == 3
        assert result.year == 2024
        
        # Data que já passou (deve usar próximo ano)
        result = parser.parse_date("10 de janeiro", base_date)
        assert result.day == 10
        assert result.month == 1
        # Como base_date é 15/01, 10/01 já passou, deve ser 2025
        assert result.year == 2025
    
    def test_slash_date_parsing(self, parser, base_date):
        """Testar formato '23/03' e '23/03/2024'"""
        # Sem ano
        result = parser.parse_date("23/03", base_date)
        assert result.day == 23
        assert result.month == 3
        
        # Com ano completo
        result = parser.parse_date("23/03/2024", base_date)
        assert result == date(2024, 3, 23)
        
        # Com ano curto
        result = parser.parse_date("23/03/24", base_date)
        assert result == date(2024, 3, 23)
    
    def test_invalid_dates(self, parser, base_date):
        """Testar datas inválidas"""
        # Data impossível
        result = parser.parse_date("32/13/2024", base_date)
        assert result is None
        
        # Texto sem data
        result = parser.parse_date("sem data aqui", base_date)
        assert result is None


class TestTimeParsing:
    """Testes de parsing de horários"""
    
    def test_specific_times(self, parser):
        """Testar horários específicos"""
        # 10h
        result = parser.parse_time("10h")
        assert result == time(10, 0)
        
        # 14:30
        result = parser.parse_time("14:30")
        assert result == time(14, 30)
        
        # 10h30
        result = parser.parse_time("10h30")
        assert result == time(10, 30)
    
    def test_period_times(self, parser):
        """Testar períodos do dia"""
        # Manhã
        result = parser.parse_time("de manhã")
        assert result == time(9, 0)
        
        # Meio-dia
        result = parser.parse_time("meio dia")
        assert result == time(12, 0)
        
        # Tarde
        result = parser.parse_time("à tarde")
        assert result == time(14, 0)
        
        # Noite
        result = parser.parse_time("de noite")
        assert result == time(19, 0)
        
        # Final da tarde
        result = parser.parse_time("final da tarde")
        assert result == time(17, 0)
    
    def test_invalid_times(self, parser):
        """Testar horários inválidos"""
        # Hora inválida
        result = parser.parse_time("25:00")
        assert result is None
        
        # Texto sem horário
        result = parser.parse_time("sem horário")
        assert result is None


class TestWindowParsing:
    """Testes de parsing de janelas de horário"""
    
    def test_morning_window(self, parser):
        """Testar janela da manhã"""
        test_cases = ["manhã", "de manhã", "pela manhã", "cedo"]
        
        for text in test_cases:
            result = parser.parse_window(text)
            assert result == "morning", f"Falhou para: {text}"
    
    def test_afternoon_window(self, parser):
        """Testar janela da tarde"""
        test_cases = ["tarde", "de tarde", "pela tarde"]
        
        for text in test_cases:
            result = parser.parse_window(text)
            assert result == "afternoon", f"Falhou para: {text}"
    
    def test_evening_window(self, parser):
        """Testar janela da noite"""
        test_cases = ["noite", "de noite", "à noite", "noitinha"]
        
        for text in test_cases:
            result = parser.parse_window(text)
            assert result == "evening", f"Falhou para: {text}"


class TestPhoneParsing:
    """Testes de parsing de telefone"""
    
    def test_phone_formats(self, parser):
        """Testar formatos de telefone"""
        test_cases = [
            ("11987654321", "+5511987654321"),
            ("(11) 98765-4321", "+5511987654321"),
            ("+55 11 98765-4321", "+5511987654321"),
            ("5511987654321", "+5511987654321"),
        ]
        
        for input_phone, expected in test_cases:
            result = parser.parse_phone(input_phone)
            assert result == expected, f"Falhou para: {input_phone}"
    
    def test_invalid_phones(self, parser):
        """Testar telefones inválidos"""
        test_cases = [
            "123",  # Muito curto
            "abc",  # Não é número
            "",     # Vazio
        ]
        
        for text in test_cases:
            result = parser.parse_phone(text)
            assert result is None, f"Deveria falhar para: {text}"


class TestNameParsing:
    """Testes de parsing de nomes"""
    
    def test_name_extraction(self, parser):
        """Testar extração de nomes"""
        test_cases = [
            ("Meu nome é João", "João"),
            ("me chamo Maria Silva", "Maria Silva"),
            ("sou o Pedro", "Pedro"),
        ]
        
        for text, expected in test_cases:
            result = parser.parse_name(text)
            assert result == expected, f"Falhou para: {text}"


class TestEntityExtraction:
    """Testes de extração completa de entidades"""
    
    def test_extract_all_entities(self, parser, base_date):
        """Testar extração de múltiplas entidades"""
        text = "Meu nome é João, quero agendar para amanhã às 14:30"
        
        entities = parser.extract_entities(text, base_date)
        
        # Deve extrair nome, data e hora
        assert "name" in entities
        assert entities["name"] == "João"
        
        assert "date" in entities
        assert entities["date"] == (base_date + timedelta(days=1)).date()
        
        assert "time" in entities
        assert entities["time"] == time(14, 30)
    
    def test_extract_partial_entities(self, parser, base_date):
        """Testar extração parcial"""
        text = "quero para amanhã"
        
        entities = parser.extract_entities(text, base_date)
        
        # Deve ter apenas data
        assert "date" in entities
        assert "time" not in entities
        assert "name" not in entities


class TestHelperMethods:
    """Testes de métodos auxiliares"""
    
    def test_format_date_friendly(self, parser):
        """Testar formatação amigável de datas"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Hoje
        result = parser.format_date_friendly(today)
        assert result == "hoje"
        
        # Amanhã
        result = parser.format_date_friendly(tomorrow)
        assert result == "amanhã"
        
        # Data futura
        future = today + timedelta(days=7)
        result = parser.format_date_friendly(future)
        # Deve conter dia da semana e data
        assert "," in result
        assert "/" in result
    
    def test_format_time_friendly(self, parser):
        """Testar formatação amigável de horários"""
        # Hora cheia
        result = parser.format_time_friendly(time(10, 0))
        assert result == "10h"
        
        # Com minutos
        result = parser.format_time_friendly(time(14, 30))
        assert result == "14:30"

