#!/usr/bin/env python3
"""
Script para executar o servidor de desenvolvimento
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Verificar se as dependências estão instaladas"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import redis
        print("✅ Dependências Python instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência não encontrada: {e}")
        print("Execute: pip install -r requirements.txt")
        return False

def check_services():
    """Verificar se os serviços estão rodando"""
    services = {
        "PostgreSQL": ("localhost", 5432),
        "Redis": ("localhost", 6379)
    }
    
    all_running = True
    
    for service_name, (host, port) in services.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {service_name} está rodando")
            else:
                print(f"❌ {service_name} não está rodando na porta {port}")
                all_running = False
        except Exception as e:
            print(f"❌ Erro ao verificar {service_name}: {e}")
            all_running = False
    
    return all_running

def create_env_file():
    """Criar arquivo .env se não existir"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Criando arquivo .env a partir do exemplo...")
        with open(env_example, 'r') as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
        print("✅ Arquivo .env criado")
    elif env_file.exists():
        print("✅ Arquivo .env já existe")
    else:
        print("⚠️  Arquivo env.example não encontrado")

def create_directories():
    """Criar diretórios necessários"""
    directories = ["logs", "uploads"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Diretório {directory} criado/verificado")

def run_server():
    """Executar o servidor de desenvolvimento"""
    print("🚀 Iniciando servidor de desenvolvimento...")
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

def main():
    """Função principal"""
    print("🔧 AgendaZap - Setup de Desenvolvimento")
    print("=" * 50)
    
    # Verificar se estamos no diretório correto
    if not Path("app").exists():
        print("❌ Execute este script no diretório backend/")
        sys.exit(1)
    
    # Verificar dependências
    if not check_dependencies():
        sys.exit(1)
    
    # Criar arquivo .env
    create_env_file()
    
    # Criar diretórios
    create_directories()
    
    # Verificar serviços
    print("\n🔍 Verificando serviços...")
    if not check_services():
        print("\n💡 Para usar Docker:")
        print("   docker-compose up -d postgres redis")
        print("\n💡 Ou instale os serviços localmente:")
        print("   - PostgreSQL na porta 5432")
        print("   - Redis na porta 6379")
        
        response = input("\nContinuar mesmo assim? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup concluído! Iniciando servidor...")
    print("📖 Documentação: http://localhost:8000/docs")
    print("🔗 API: http://localhost:8000")
    print("=" * 50)
    
    # Executar servidor
    run_server()

if __name__ == "__main__":
    main()
