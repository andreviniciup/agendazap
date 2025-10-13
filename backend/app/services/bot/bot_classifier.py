"""
Classificador Mini ML para intenções do bot usando DistilBERT
"""

import json
from typing import Tuple, Optional
from pathlib import Path

# Imports opcionais de ML
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None


class BotClassifier:
    """Classificador Mini ML para intenções do bot"""
    
    def __init__(self, model_path: str = "./training_data/models/bot_model_v1/final"):
        self.model_path = model_path
        self.ready = False
        
        # Verificar se ML está disponível
        if not ML_AVAILABLE:
            print("⚠️ PyTorch/Transformers não instalados")
            print("   Bot vai usar apenas regras até instalar: pip install torch transformers")
            self.ready = False
            return
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            # Verificar se modelo existe
            if not Path(model_path).exists():
                print(f"⚠️ Modelo não encontrado em: {model_path}")
                print("   Bot vai usar apenas regras até modelo estar disponível")
                self.ready = False
                return
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Carregar mapping de labels
            label_mapping_path = Path(model_path) / "label_mapping.json"
            if label_mapping_path.exists():
                with open(label_mapping_path) as f:
                    mapping = json.load(f)
                    self.id2label = {int(k): v for k, v in mapping['id2label'].items()}
            else:
                print("⚠️ label_mapping.json não encontrado")
                self.ready = False
                return
            
            self.ready = True
            print(f"✅ BotClassifier carregado com sucesso")
            print(f"   Device: {self.device}")
            print(f"   Labels: {list(self.id2label.values())}")
        
        except Exception as e:
            print(f"⚠️ BotClassifier não disponível: {e}")
            print("   Bot vai usar apenas regras até modelo estar disponível")
            self.ready = False
    
    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classifica texto e retorna (intent, confidence)
        
        Args:
            text: Texto da mensagem do usuário
            
        Returns:
            Tupla (intent, confidence) onde:
            - intent: Nome da intenção prevista
            - confidence: Confiança da previsão (0-1)
        """
        
        if not self.ready:
            return "unknown", 0.0
        
        try:
            # Tokenizar
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128
            )
            
            # Mover para device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inferência
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)
                predicted_id = torch.argmax(probs[0]).item()
                confidence = probs[0][predicted_id].item()
            
            intent = self.id2label[predicted_id]
            return intent, confidence
        
        except Exception as e:
            print(f"⚠️ Erro ao classificar '{text[:50]}...': {e}")
            return "unknown", 0.0
    
    def batch_classify(self, texts: list) -> list:
        """
        Classifica múltiplos textos de uma vez (mais eficiente)
        
        Args:
            texts: Lista de textos para classificar
            
        Returns:
            Lista de tuplas (intent, confidence)
        """
        
        if not self.ready:
            return [("unknown", 0.0)] * len(texts)
        
        try:
            # Tokenizar batch
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128
            )
            
            # Mover para device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inferência
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)
                predicted_ids = torch.argmax(probs, dim=1).tolist()
                confidences = [probs[i][pred_id].item() 
                              for i, pred_id in enumerate(predicted_ids)]
            
            results = [
                (self.id2label[pred_id], conf)
                for pred_id, conf in zip(predicted_ids, confidences)
            ]
            
            return results
        
        except Exception as e:
            print(f"⚠️ Erro ao classificar batch: {e}")
            return [("unknown", 0.0)] * len(texts)

