#!/usr/bin/env python3
"""
Ferramenta de etiquetagem manual de dados
"""

import os
import sys
from pathlib import Path

# Configurar ambiente
os.environ.setdefault("SECRET_KEY", "seed_secret_key_long_enough_1234567890")
_here = Path(__file__).resolve().parent
_db_path = (_here / "seed.db").as_posix()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

# Adicionar path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.bot.data_collector import DataCollector, LabelQuality


def label_data():
    """Ferramenta de etiquetagem manual"""
    
    print("\n" + "="*60)
    print("  🏷️ FERRAMENTA DE ETIQUETAGEM MANUAL")
    print("="*60)
    
    collector = DataCollector()
    
    # Lista de intenções disponíveis
    intents = [
        "greeting",
        "schedule", 
        "availability",
        "price",
        "services",
        "about",
        "cancel",
        "reschedule",
        "business_hours",
        "address",
        "payment",
        "human",
        "unknown"
    ]
    
    # Mapeamento em português
    intent_names = {
        "greeting": "Cumprimentos/Olá/Bom dia",
        "schedule": "Agendar/Marcar",
        "availability": "Disponibilidade/Horários",
        "price": "Preços/Valores",
        "services": "Serviços/Procedimentos",
        "about": "Como funciona/Informações",
        "cancel": "Cancelar/Desmarcar",
        "reschedule": "Remarcar/Alterar",
        "business_hours": "Horário de funcionamento",
        "address": "Endereço/Localização",
        "payment": "Pagamento/Formas de pagar",
        "human": "Falar com pessoa/Atendente",
        "unknown": "Não sei/Não entendi"
    }
    
    # Buscar exemplos incertos
    examples = collector.get_uncertain_examples(limit=50)
    
    if not examples:
        print("✅ Nenhum exemplo incerto encontrado!")
        print("   Todos os dados estão com boa qualidade.")
        return
    
    print(f"\n📝 Encontrados {len(examples)} exemplos para revisar")
    print("   (Pressione Ctrl+C para sair a qualquer momento)")
    print()
    
    labeled_count = 0
    
    try:
        for i, example in enumerate(examples, 1):
            print(f"\n{'='*60}")
            print(f"📝 Exemplo {i}/{len(examples)}")
            print(f"📝 Texto: {example['text']}")
            print(f"🤖 Previsão: {example['predicted_intent']} "
                  f"(confiança: {example['confidence']:.2%})")
            print(f"\nOpções de intenção:")
            
            for j, intent in enumerate(intents):
                name_pt = intent_names.get(intent, intent)
                print(f"  {j}: {name_pt}")
            
            print(f"  {len(intents)}: Pular este exemplo")
            print(f"  {len(intents) + 1}: Sair")
            
            while True:
                try:
                    choice = input(f"\nEscolha a intenção correta (0-{len(intents) + 1}): ").strip()
                    
                    if choice == str(len(intents) + 1):
                        print("\n👋 Saindo...")
                        return
                    elif choice == str(len(intents)):
                        print("⏭️ Pulando exemplo...")
                        break
                    
                    choice_idx = int(choice)
                    if 0 <= choice_idx < len(intents):
                        selected_intent = intents[choice_idx]
                        
                        # Atualizar etiqueta
                        collector.log_user_feedback(
                            example['id'],
                            selected_intent,
                            "label_tool"
                        )
                        
                        print(f"✅ Etiquetado como: {intent_names.get(selected_intent, selected_intent)}")
                        labeled_count += 1
                        break
                    else:
                        print("❌ Opção inválida. Tente novamente.")
                        
                except ValueError:
                    print("❌ Digite um número válido.")
                except KeyboardInterrupt:
                    print("\n\n👋 Saindo...")
                    return
    
    except KeyboardInterrupt:
        print("\n\n👋 Saindo...")
    
    print(f"\n✅ Etiquetagem concluída!")
    print(f"   Exemplos etiquetados: {labeled_count}")
    
    # Mostrar estatísticas atualizadas
    stats = collector.get_stats()
    quality_rate = (stats['ready_to_train'] / stats['total_examples']) * 100 if stats['total_examples'] > 0 else 0
    print(f"\n📊 Estatísticas atualizadas:")
    print(f"   Total: {stats['total_examples']}")
    print(f"   Prontos para treino: {stats['ready_to_train']}")
    print(f"   Taxa de qualidade: {quality_rate:.1f}%")


if __name__ == "__main__":
    label_data()
