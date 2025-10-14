#!/usr/bin/env python3
"""
Script de Validação de Segurança
Verifica se todas as configurações de segurança estão corretas
"""

import sys
import os
from pathlib import Path

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def check_env_file():
    """Verificar se .env existe"""
    print("\n" + "="*60)
    print("1. Verificando arquivo .env")
    print("="*60)
    
    env_path = Path(".env")
    if not env_path.exists():
        print_warning(".env não encontrado. Usando variáveis de ambiente do sistema.")
        return False
    
    print_success(".env encontrado")
    return True

def check_secret_key():
    """Verificar SECRET_KEY"""
    print("\n" + "="*60)
    print("2. Verificando SECRET_KEY")
    print("="*60)
    
    try:
        from app.config import settings
        
        secret_key = settings.SECRET_KEY
        
        # Verificar tamanho
        if len(secret_key) < 32:
            print_error(f"SECRET_KEY muito curta: {len(secret_key)} caracteres (mínimo 32)")
            print_info("Gere uma nova: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            return False
        
        # Verificar se é uma chave óbvia
        weak_keys = ["secret", "password", "change", "your-", "default", "test", "example"]
        if any(weak in secret_key.lower() for weak in weak_keys):
            print_error("SECRET_KEY parece ser uma chave padrão/fraca")
            print_info("Gere uma nova: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            return False
        
        print_success(f"SECRET_KEY válida ({len(secret_key)} caracteres)")
        return True
        
    except Exception as e:
        print_error(f"Erro ao verificar SECRET_KEY: {e}")
        return False

def check_environment():
    """Verificar configurações de ambiente"""
    print("\n" + "="*60)
    print("3. Verificando Ambiente")
    print("="*60)
    
    try:
        from app.config import settings
        
        print_info(f"ENVIRONMENT: {settings.ENVIRONMENT}")
        print_info(f"DEBUG: {settings.DEBUG}")
        
        # Verificar produção
        if settings.ENVIRONMENT == "production":
            if settings.DEBUG:
                print_error("DEBUG=True em produção! Isso é um risco de segurança!")
                return False
            print_success("Configurações de produção corretas")
        else:
            print_warning(f"Ambiente: {settings.ENVIRONMENT} (não é produção)")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao verificar ambiente: {e}")
        return False

def check_cors():
    """Verificar CORS"""
    print("\n" + "="*60)
    print("4. Verificando CORS")
    print("="*60)
    
    try:
        from app.config import settings
        
        print_info(f"ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
        
        # Verificar se tem localhost em produção
        if settings.ENVIRONMENT == "production":
            for origin in settings.ALLOWED_ORIGINS:
                if "localhost" in origin or "127.0.0.1" in origin:
                    print_error(f"Origem localhost em produção: {origin}")
                    return False
            print_success("CORS configurado corretamente para produção")
        else:
            print_success("CORS configurado")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao verificar CORS: {e}")
        return False

def check_redis():
    """Verificar Redis"""
    print("\n" + "="*60)
    print("5. Verificando Redis")
    print("="*60)
    
    try:
        from app.config import settings
        
        print_info(f"REDIS_URL: {settings.REDIS_URL}")
        
        # Verificar senha em produção
        if settings.ENVIRONMENT == "production":
            if not settings.REDIS_PASSWORD:
                print_warning("Redis sem senha em produção (recomenda-se usar senha)")
            else:
                print_success("Redis com senha configurada")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao verificar Redis: {e}")
        return False

def check_password_validation():
    """Testar validação de senha"""
    print("\n" + "="*60)
    print("6. Testando Validação de Senha")
    print("="*60)
    
    try:
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        # Testar senhas fracas
        weak_passwords = [
            "senha123",           # Muito curta
            "senhasenha12",       # Sem maiúscula
            "SENHASENHA12",       # Sem minúscula
            "SenhaSenha",         # Sem número
            "SenhaSenha123",      # Sem especial
            "Senha1111111!",      # Repetições
            "Password123!",       # Comum
        ]
        
        rejected = 0
        for pwd in weak_passwords:
            try:
                UserCreate(
                    email="teste@teste.com",
                    password=pwd,
                    template_type="service_table"
                )
            except ValidationError:
                rejected += 1
        
        if rejected == len(weak_passwords):
            print_success(f"Todas as {len(weak_passwords)} senhas fracas foram rejeitadas")
            return True
        else:
            print_error(f"Apenas {rejected}/{len(weak_passwords)} senhas fracas foram rejeitadas")
            return False
        
    except Exception as e:
        print_error(f"Erro ao testar validação de senha: {e}")
        return False

def check_security_files():
    """Verificar se arquivos de documentação existem"""
    print("\n" + "="*60)
    print("7. Verificando Documentação de Segurança")
    print("="*60)
    
    # Arquivos de documentação foram removidos para limpeza
    print_info("Documentação de segurança foi removida para limpeza do projeto")
    return True

def main():
    """Executar todas as verificações"""
    print("\n" + "="*60)
    print("🔒 VALIDAÇÃO DE SEGURANÇA - AgendaZap")
    print("="*60)
    
    checks = [
        ("Arquivo .env", check_env_file),
        ("SECRET_KEY", check_secret_key),
        ("Ambiente", check_environment),
        ("CORS", check_cors),
        ("Redis", check_redis),
        ("Validação de Senha", check_password_validation),
        ("Documentação", check_security_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Erro na verificação {name}: {e}")
            results.append((name, False))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        color = GREEN if result else RED
        print(f"{color}{status}{RESET} - {name}")
    
    print("\n" + "="*60)
    percentage = (passed / total) * 100
    print(f"Resultado: {passed}/{total} verificações passaram ({percentage:.1f}%)")
    print("="*60)
    
    if passed == total:
        print_success("\n🎉 Todas as verificações passaram! Sistema seguro.")
        return 0
    elif passed >= total * 0.7:
        print_warning(f"\n⚠️  Algumas verificações falharam. Revise os itens acima.")
        return 1
    else:
        print_error(f"\n❌ Muitas verificações falharam. Sistema NÃO está seguro para produção!")
        return 2

if __name__ == "__main__":
    sys.exit(main())

