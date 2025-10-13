"""
Sistema de coleta automática e etiquetagem de dados do bot
Para treinar Mini ML depois
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from enum import Enum
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path


class Intent(str, Enum):
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


class LabelQuality(str, Enum):
    CONFIDENT = "confident"      # Regra identificou com > 0.8
    UNCERTAIN = "uncertain"      # 0.5-0.8, precisa validar
    MANUAL = "manual"            # Etiquetado manualmente
    FEEDBACK = "feedback"        # Usuário corrigiu


@dataclass
class TrainingExample:
    """Um exemplo para treinar o modelo"""
    text: str
    intent: str
    confidence: float
    label_quality: str
    timestamp: str
    context: Dict[str, Any]
    user_whatsapp: str
    resolved: bool = False  # Se o bot conseguiu ajudar depois
    feedback: Optional[str] = None  # Feedback do usuário
    
    def to_dict(self):
        return asdict(self)


class DataCollector:
    """Coleta dados de conversas do bot"""
    
    def __init__(self, db_path: str = "bot_training_data.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Cria tabelas se não existirem"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS training_examples (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                intent TEXT NOT NULL,
                confidence REAL,
                label_quality TEXT,
                timestamp TEXT,
                context TEXT,
                user_whatsapp TEXT,
                resolved BOOLEAN,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_corrections (
                id INTEGER PRIMARY KEY,
                example_id INTEGER,
                original_intent TEXT,
                corrected_intent TEXT,
                user_whatsapp TEXT,
                timestamp TEXT,
                FOREIGN KEY(example_id) REFERENCES training_examples(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_interaction(
        self,
        text: str,
        intent: str,
        confidence: float,
        label_quality: str,
        user_whatsapp: str,
        context: Dict[str, Any],
        resolved: bool = False
    ) -> int:
        """Registra uma interação do bot"""
        
        example = TrainingExample(
            text=text,
            intent=intent,
            confidence=confidence,
            label_quality=label_quality,
            timestamp=datetime.utcnow().isoformat(),
            context=context,
            user_whatsapp=user_whatsapp,
            resolved=resolved
        )
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO training_examples 
            (text, intent, confidence, label_quality, timestamp, context, user_whatsapp, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            example.text,
            example.intent,
            example.confidence,
            example.label_quality,
            example.timestamp,
            json.dumps(example.context),
            example.user_whatsapp,
            example.resolved
        ))
        
        example_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return example_id
    
    def log_user_feedback(
        self,
        example_id: int,
        correct_intent: str,
        user_whatsapp: str
    ):
        """Registra quando usuário corrige o bot"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Pegar intent original
        c.execute('SELECT intent FROM training_examples WHERE id = ?', (example_id,))
        row = c.fetchone()
        
        if row:
            original_intent = row[0]
            
            # Registrar correção
            c.execute('''
                INSERT INTO user_corrections
                (example_id, original_intent, corrected_intent, user_whatsapp, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                example_id,
                original_intent,
                correct_intent,
                user_whatsapp,
                datetime.utcnow().isoformat()
            ))
            
            # Marcar exemplo como feedback
            c.execute('''
                UPDATE training_examples
                SET label_quality = ?, feedback = ?, resolved = 1
                WHERE id = ?
            ''', (LabelQuality.FEEDBACK.value, correct_intent, example_id))
        
        conn.commit()
        conn.close()
    
    def get_uncertain_examples(self, limit: int = 50) -> List[Dict]:
        """Retorna exemplos incertos que precisam etiquetagem manual"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, text, intent, confidence, timestamp
            FROM training_examples
            WHERE label_quality = ?
            ORDER BY confidence ASC
            LIMIT ?
        ''', (LabelQuality.UNCERTAIN.value, limit))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'text': row[1],
                'predicted_intent': row[2],
                'confidence': row[3],
                'timestamp': row[4]
            }
            for row in rows
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de coleta"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM training_examples')
        total = c.fetchone()[0]
        
        c.execute('''
            SELECT label_quality, COUNT(*) as count
            FROM training_examples
            GROUP BY label_quality
        ''')
        by_quality = {row[0]: row[1] for row in c.fetchall()}
        
        c.execute('''
            SELECT intent, COUNT(*) as count
            FROM training_examples
            GROUP BY intent
        ''')
        by_intent = {row[0]: row[1] for row in c.fetchall()}
        
        c.execute('SELECT COUNT(*) FROM user_corrections')
        corrections = c.fetchone()[0]
        
        conn.close()
        
        return {
            'total_examples': total,
            'by_quality': by_quality,
            'by_intent': by_intent,
            'user_corrections': corrections,
            'ready_to_train': by_quality.get(LabelQuality.CONFIDENT.value, 0) + 
                             by_quality.get(LabelQuality.MANUAL.value, 0) +
                             by_quality.get(LabelQuality.FEEDBACK.value, 0)
        }
    
    def export_to_csv(self, output_path: str = "training_data.csv"):
        """Exporta dados em CSV para treinar com HuggingFace"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT text, intent, feedback
            FROM training_examples
            WHERE label_quality IN (?, ?, ?)
            ORDER BY timestamp DESC
        ''', (
            LabelQuality.CONFIDENT.value,
            LabelQuality.MANUAL.value,
            LabelQuality.FEEDBACK.value
        ))
        
        rows = c.fetchall()
        conn.close()
        
        # Escrever CSV
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("text,label\n")
            for text, intent, feedback in rows:
                # Se teve feedback (correção), usar esse
                label = feedback if feedback else intent
                # Escapar aspas no texto
                text_clean = text.replace('"', '""')
                f.write(f'"{text_clean}",{label}\n')
        
        return output_path
    
    def get_low_confidence_by_intent(self) -> Dict[str, List[Dict]]:
        """Agrupa falhas por tipo de intenção"""
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT intent, text, confidence
            FROM training_examples
            WHERE confidence < 0.6
            ORDER BY intent, confidence ASC
        ''')
        
        rows = c.fetchall()
        conn.close()
        
        result = {}
        for intent, text, confidence in rows:
            if intent not in result:
                result[intent] = []
            result[intent].append({
                'text': text,
                'confidence': confidence
            })
        
        return result


class ManualLabelingTool:
    """Ferramenta interativa para etiquetar dados"""
    
    def __init__(self, collector: DataCollector):
        self.collector = collector
    
    def start_labeling_session(self):
        """Inicia sessão interativa de etiquetagem"""
        
        print("\n🏷️ FERRAMENTA DE ETIQUETAGEM MANUAL")
        print("=" * 50)
        
        uncertain = self.collector.get_uncertain_examples(limit=100)
        
        if not uncertain:
            print("✅ Nenhum exemplo incerto para etiquetar!")
            return
        
        print(f"📊 {len(uncertain)} exemplos para revisar\n")
        
        labeled_count = 0
        
        for idx, example in enumerate(uncertain, 1):
            print(f"\n[{idx}/{len(uncertain)}]")
            print(f"📝 Texto: {example['text']}")
            print(f"🤖 Previsão: {example['predicted_intent']} "
                  f"(confiança: {example['confidence']:.2%})")
            print(f"\nOpções de intenção:")
            
            # Mapeamento em português
            intent_names = {
                "greeting": "Cumprimentos/Olá/Bom dia",
                "availability": "Disponibilidade/Horários",
                "schedule": "Agendar/Marcar",
                "reschedule": "Remarcar/Alterar",
                "cancel": "Cancelar/Desmarcar",
                "price": "Preços/Valores",
                "services": "Serviços/Procedimentos",
                "about": "Como funciona/Informações",
                "business_hours": "Horário de funcionamento",
                "address": "Endereço/Localização",
                "payment": "Pagamento/Formas de pagar",
                "human": "Falar com pessoa/Atendente",
                "unknown": "Não sei/Não entendi"
            }
            
            for i, intent in enumerate(Intent):
                name_pt = intent_names.get(intent.value, intent.value)
                print(f"  {i}: {name_pt}")
            
            while True:
                try:
                    choice = input("\nSua escolha (0-11) ou 's' para pular: ").strip()
                    
                    if choice.lower() == 's':
                        break
                    
                    choice_idx = int(choice)
                    intents = list(Intent)
                    
                    if 0 <= choice_idx < len(intents):
                        correct_intent = intents[choice_idx].value
                        
                        # Salvar correção
                        self.collector.log_user_feedback(
                            example['id'],
                            correct_intent,
                            user_whatsapp="manual_labeling"
                        )
                        
                        labeled_count += 1
                        print(f"✅ Etiquetado como: {correct_intent}")
                        break
                    else:
                        print("❌ Escolha inválida")
                
                except ValueError:
                    print("❌ Digite um número válido")
        
        stats = self.collector.get_stats()
        print(f"\n✅ Sessão concluída!")
        print(f"📊 {labeled_count} exemplos etiquetados")
        print(f"📈 Total pronto para treino: {stats['ready_to_train']}")


class DataQualityAnalyzer:
    """Analisa qualidade dos dados coletados"""
    
    def __init__(self, collector: DataCollector):
        self.collector = collector
    
    def analyze(self):
        """Analisa e reporta qualidade"""
        
        stats = self.collector.get_stats()
        low_conf = self.collector.get_low_confidence_by_intent()
        
        print("\n📊 ANÁLISE DE QUALIDADE DOS DADOS")
        print("=" * 50)
        
        print(f"\n✅ Total de exemplos: {stats['total_examples']}")
        print(f"📈 Pronto para treino: {stats['ready_to_train']}")
        print(f"🔄 Correções do usuário: {stats['user_corrections']}")
        
        print("\n📋 Por qualidade de etiqueta:")
        for quality, count in stats['by_quality'].items():
            pct = (count / stats['total_examples'] * 100) if stats['total_examples'] else 0
            print(f"  {quality}: {count} ({pct:.1f}%)")
        
        print("\n🎯 Distribuição por intenção:")
        for intent, count in stats['by_intent'].items():
            pct = (count / stats['total_examples'] * 100) if stats['total_examples'] else 0
            print(f"  {intent}: {count} ({pct:.1f}%)")
        
        if low_conf:
            print("\n⚠️ Intenções com baixa confiança:")
            for intent, examples in low_conf.items():
                print(f"\n  {intent}: {len(examples)} exemplos")
                for ex in examples[:3]:
                    print(f"    - '{ex['text']}' "
                          f"({ex['confidence']:.2%} confiança)")

