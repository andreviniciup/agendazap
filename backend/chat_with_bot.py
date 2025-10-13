#!/usr/bin/env python3
"""
Chat interativo com o bot para testar e coletar dados
"""

import os
import sys
from pathlib import Path
import asyncio

# Configurar ambiente
os.environ.setdefault("SECRET_KEY", "seed_secret_key_long_enough_1234567890")
_here = Path(__file__).resolve().parent
_db_path = (_here / "seed.db").as_posix()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

# Adicionar path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.bot.bot_service import BotService
from app.dependencies import get_redis


async def chat_with_bot():
    """Chat interativo com o bot"""
    
    print("\n" + "="*60)
    print("  🤖 CHAT INTERATIVO COM O BOT")
    print("="*60)
    print("Digite suas mensagens (digite 'sair' para encerrar)")
    print("="*60)
    
    # Inicializar serviços
    try:
        redis_client = await get_redis()
        if not redis_client:
            print("⚠️ Redis não disponível - usando modo limitado")
            redis_client = None
    except Exception as e:
        print(f"⚠️ Erro ao conectar Redis: {e}")
        redis_client = None
    
    bot_service = BotService(redis_client)
    
    # Número de teste
    test_number = "5511999999999"
    
    try:
        while True:
            # Input do usuário
            user_input = input("\n👤 Você: ").strip()
            
            if user_input.lower() in ['sair', 'exit', 'quit', 'bye']:
                print("\n👋 Até logo!")
                break
            
            if not user_input:
                continue
            
            # Simular payload do WhatsApp
            payload = {
                "messages": [{
                    "from": test_number,
                    "text": {"body": user_input}
                }]
            }
            
            # Processar com o bot
            try:
                response = await bot_service.process(payload)
                
                if response and "message" in response:
                    print(f"🤖 Bot: {response['message']}")
                    
                    # Mostrar informações adicionais se disponíveis
                    if "handoff" in response:
                        print("   🔄 Direcionando para atendimento humano")
                else:
                    print("🤖 Bot: [Sem resposta]")
                
                # Mostrar estatísticas de dados
                try:
                    stats = bot_service.collector.get_stats()
                    print(f"📊 Dados: {stats['total_examples']} exemplos | {stats['ready_to_train']} prontos")
                except Exception:
                    pass
                
            except Exception as e:
                print(f"❌ Erro: {e}")
    
    except KeyboardInterrupt:
        print("\n\n👋 Chat encerrado!")
    
    finally:
        # Fechar conexões se disponível
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass


async def test_bot_scenarios():
    """Testa cenários específicos do bot"""
    
    print("\n🧪 TESTE DE CENÁRIOS DO BOT")
    print("="*60)
    
    # Inicializar serviços
    try:
        redis_client = await get_redis()
        if not redis_client:
            print("⚠️ Redis não disponível - usando modo limitado")
            redis_client = None
    except Exception as e:
        print(f"⚠️ Erro ao conectar Redis: {e}")
        redis_client = None
    
    bot_service = BotService(redis_client)
    test_number = "5511999999999"
    
    # Cenários de teste
    scenarios = [
        "oi",
        "quero agendar",
        "quanto custa?",
        "que serviços vocês têm?",
        "como funciona?",
        "quero falar com alguém",
        "obrigado"
    ]
    
    print("🎭 Testando cenários automáticos...")
    print()
    
    for i, message in enumerate(scenarios, 1):
        print(f"💬 Cenário {i}: {message}")
        
        payload = {
            "messages": [{
                "from": test_number,
                "text": {"body": message}
            }]
        }
        
        try:
            response = await bot_service.process(payload)
            
            if response and "message" in response:
                print(f"🤖 Resposta: {response['message']}")
                
                if "handoff" in response:
                    print("   🔄 Direcionando para atendimento humano")
            else:
                print("🤖 Bot: [Sem resposta]")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
        
        print()
    
    # Fechar conexões se disponível
    if redis_client:
        try:
            await redis_client.close()
        except Exception:
            pass
    
    print("✅ Teste de cenários concluído!")


def show_menu():
    """Mostra menu de opções"""
    
    print("\n📋 OPÇÕES DISPONÍVEIS:")
    print("1. Chat interativo")
    print("2. Teste de cenários automáticos")
    print("3. Sair")
    
    while True:
        try:
            choice = input("\nEscolha uma opção (1-3): ").strip()
            
            if choice == "1":
                return "chat"
            elif choice == "2":
                return "test"
            elif choice == "3":
                return "exit"
            else:
                print("❌ Opção inválida. Escolha 1, 2 ou 3.")
        except KeyboardInterrupt:
            return "exit"


async def main():
    """Função principal"""
    
    print("🤖 BOT INTELIGENTE - CHAT E TESTES")
    print("="*60)
    
    while True:
        choice = show_menu()
        
        if choice == "chat":
            await chat_with_bot()
        elif choice == "test":
            await test_bot_scenarios()
        elif choice == "exit":
            print("\n👋 Até logo!")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa encerrado!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
