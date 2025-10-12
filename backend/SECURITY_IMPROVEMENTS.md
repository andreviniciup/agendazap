# 🔒 Melhorias de Segurança Implementadas

Este documento detalha todas as correções de segurança implementadas no sistema AgendaZap.

## 📊 Status das Implementações

### ✅ Críticas (Implementadas)

#### 1. **Secrets em Código/Ambiente**
**Problema**: SECRET_KEY com valor padrão público em produção.

**Solução Implementada**:
- ✅ Removido valor padrão da SECRET_KEY no `config.py`
- ✅ Adicionado validador para garantir SECRET_KEY forte em produção (mínimo 32 caracteres)
- ✅ Verificação de chaves fracas/padrão (rejeita "secret", "password", "change", etc.)
- ✅ Validação automática de DEBUG=False em produção
- ✅ Atualizado `env.example` com instruções para gerar chave segura

**Arquivo**: `backend/app/config.py`
```python
SECRET_KEY: str = Field(
    ..., 
    min_length=32,
    description="Chave secreta para JWT. Gere com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
)
```

#### 2. **Senhas Fracas Aceitas**
**Problema**: Validação de senha muito simples, permitia senhas fracas como "Aaaaaa11".

**Solução Implementada**:
- ✅ Aumentado comprimento mínimo de 8 para 12 caracteres
- ✅ Obrigatório: maiúscula, minúscula, número E caractere especial
- ✅ Bloqueio de senhas com mais de 3 caracteres repetidos em sequência
- ✅ Lista de senhas comuns bloqueadas
- ✅ Bloqueio de sequências óbvias (123456, qwerty, etc.)

**Arquivo**: `backend/app/schemas/user.py`
```python
password: str = Field(..., min_length=12, max_length=128)
```

#### 3. **Tokens Não Invalidados no Logout**
**Problema**: Access token continuava válido após logout por até 30 minutos.

**Solução Implementada**:
- ✅ Implementado blacklist de tokens no Redis
- ✅ Logout invalida tanto refresh quanto access token
- ✅ Middleware verifica blacklist em cada requisição
- ✅ Tokens blacklisted expiram automaticamente após 30 min

**Arquivos**: 
- `backend/app/services/auth_service.py`
- `backend/app/dependencies.py` (verificação de blacklist)

#### 4. **CORS Muito Aberto**
**Problema**: `allow_methods=["*"]` e `allow_headers=["*"]` permitiam qualquer método/header.

**Solução Implementada**:
- ✅ Lista explícita de métodos permitidos: GET, POST, PUT, DELETE, PATCH, OPTIONS
- ✅ Lista explícita de headers permitidos
- ✅ Configurado max_age=3600 para cache de preflight
- ✅ Mantido allow_credentials=True para autenticação

**Arquivo**: `backend/app/main.py`

#### 5. **Proteção contra Timing Attacks**
**Problema**: Tempo de resposta diferente revelava se usuário existia.

**Solução Implementada**:
- ✅ Hash dummy executado sempre, mesmo se usuário não existir
- ✅ Tempo de resposta consistente independente de usuário existir ou não
- ✅ Previne enumeração de usuários

**Arquivo**: `backend/app/services/auth_service.py`
```python
if user:
    password_valid = verify_password(login_data.password, user.password_hash)
else:
    # Hash dummy para manter timing consistente
    dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5jtRfxkR4dYhi"
    verify_password(login_data.password, dummy_hash)
    password_valid = False
```

### ✅ Alto Nível (Implementadas)

#### 6. **Dados Sensíveis em Logs**
**Problema**: URLs com query strings (potencialmente com tokens/senhas) eram logadas.

**Solução Implementada**:
- ✅ Função `sanitize_url_for_log()` remove query strings
- ✅ Aplicada em todos os middlewares de logging
- ✅ Previne vazamento de dados sensíveis nos logs

**Arquivos**:
- `backend/app/main.py`
- `backend/app/middleware/plan_middleware.py`

#### 7. **Proteção contra XSS em Templates**
**Problema**: Variáveis em templates não eram escapadas, permitindo XSS.

**Solução Implementada**:
- ✅ Importado módulo `html.escape`
- ✅ Todas as variáveis são escapadas por padrão
- ✅ Parâmetro `escape_html=True` opcional (padrão ativado)

**Arquivo**: `backend/app/services/template_service.py`
```python
str_value = str(value) if value is not None else ""
if escape_html:
    str_value = escape(str_value)
```

#### 8. **Validação de Entrada Segura**
**Problema**: Campos de busca aceitavam qualquer caractere, potencial para exploits.

**Solução Implementada**:
- ✅ Regex restritivo em campos de busca
- ✅ Máximo de 100 caracteres em queries
- ✅ Apenas caracteres alfanuméricos, espaços e pontuação básica
- ✅ Suporte a caracteres acentuados (pt-BR)

**Arquivo**: `backend/app/schemas/client.py`
```python
query: Optional[str] = Field(
    None, 
    max_length=100,
    pattern=r'^[a-zA-Z0-9\s\-\.\@\+áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]*$'
)
```

#### 9. **Validação de Tamanho de Upload**
**Problema**: Sem limite de tamanho em URLs de imagens.

**Solução Implementada**:
- ✅ Máximo 5 imagens por serviço
- ✅ URL máximo de 2048 caracteres
- ✅ Validação de formato de URL (regex)
- ✅ Verificação de extensões permitidas (.jpg, .jpeg, .png, .webp, .gif)

**Arquivo**: `backend/app/schemas/service.py`

#### 10. **Sistema de Verificação de Email**
**Problema**: Qualquer email fake podia criar conta sem verificação.

**Solução Implementada**:
- ✅ Novo serviço `EmailVerificationService`
- ✅ Tokens seguros gerados com `secrets.token_urlsafe(32)`
- ✅ Tokens armazenados no Redis com expiração de 24h
- ✅ Endpoints para verificar, reenviar e checar status
- ✅ Em produção, acesso bloqueado para emails não verificados

**Arquivos**:
- `backend/app/services/email_verification_service.py` (novo)
- `backend/app/api/auth.py` (endpoints adicionados)

**Endpoints**:
- `POST /api/auth/verify-email/{token}` - Verificar email
- `POST /api/auth/resend-verification` - Reenviar verificação
- `GET /api/auth/verification-status` - Status de verificação

---

## 🔐 Configurações de Segurança Obrigatórias

### Produção (OBRIGATÓRIO)

```env
# .env em produção
ENVIRONMENT=production
DEBUG=false

# Gerar com: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=<GERAR_CHAVE_UNICA_FORTE_32_CHARS>

# CORS - listar apenas domínios reais
ALLOWED_ORIGINS=https://agendazap.com,https://www.agendazap.com
ALLOWED_HOSTS=agendazap.com,www.agendazap.com
```

### Desenvolvimento

```env
# .env em desenvolvimento
ENVIRONMENT=development
DEBUG=true

# Mesmo em dev, use uma chave forte
SECRET_KEY=<GERAR_CHAVE_UNICA>

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

---

## 📋 Checklist de Segurança para Deploy

### Antes de Subir para Produção

- [ ] SECRET_KEY gerada com `secrets.token_urlsafe(32)`
- [ ] ENVIRONMENT=production
- [ ] DEBUG=false
- [ ] ALLOWED_ORIGINS apenas com domínios reais (sem localhost)
- [ ] ALLOWED_HOSTS apenas com domínios reais
- [ ] Redis configurado com senha
- [ ] Banco de dados com credenciais fortes
- [ ] HTTPS configurado (SSL/TLS)
- [ ] Backup do banco configurado
- [ ] Logs configurados (sem dados sensíveis)
- [ ] Rate limiting ativado
- [ ] Monitoramento de erros ativo
- [ ] WAF configurado (ex: Cloudflare)

### Testes de Segurança

- [ ] Testar login com senha fraca (deve rejeitar)
- [ ] Testar logout + uso de token antigo (deve rejeitar)
- [ ] Testar CORS de domínio não autorizado (deve rejeitar)
- [ ] Testar XSS em templates (deve escapar)
- [ ] Testar SQL injection em buscas (deve sanitizar)
- [ ] Testar timing attack (tempo de resposta consistente)
- [ ] Testar upload de imagem muito grande (deve rejeitar)
- [ ] Testar acesso sem email verificado (deve bloquear em prod)

---

## 🚨 Vulnerabilidades Conhecidas (Backlog)

### Médio Prazo

1. **Audit Log** - Implementar log de todas as ações para compliance (LGPD/GDPR)
2. **Rate Limiting por Usuário** - Limitar requisições por usuário (não só global)
3. **CSRF Protection** - Adicionar proteção contra CSRF (ex: fastapi-csrf-protect)
4. **2FA** - Autenticação de dois fatores para contas premium

### Longo Prazo

1. **WAF** - Web Application Firewall (Cloudflare, AWS WAF)
2. **Encryption em Repouso** - Criptografar dados sensíveis no banco
3. **Penetration Testing** - Contratar teste de invasão profissional
4. **Compliance Audit** - Auditoria LGPD/GDPR completa
5. **Security Headers** - Implementar todos os headers de segurança (CSP, X-Frame-Options, etc.)

---

## 📚 Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [LGPD - Lei Geral de Proteção de Dados](https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd)

---

## 📞 Contato de Segurança

Para reportar vulnerabilidades de segurança:
- Email: security@agendazap.com (criar)
- Não divulgar publicamente antes de correção
- Tempo de resposta esperado: 48h

---

**Data da Última Atualização**: 12/10/2025
**Versão**: 1.0
**Responsável**: Sistema de Segurança AgendaZap

