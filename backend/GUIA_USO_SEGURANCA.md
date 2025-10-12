# 🔐 Guia Rápido - Funcionalidades de Segurança

## 📋 Índice
1. [Configuração Inicial](#configuração-inicial)
2. [Registro com Senha Forte](#registro-com-senha-forte)
3. [Login e Logout Seguro](#login-e-logout-seguro)
4. [Verificação de Email](#verificação-de-email)
5. [Testes de Segurança](#testes-de-segurança)

---

## 🚀 Configuração Inicial

### 1. Gerar SECRET_KEY

```bash
# Execute no terminal
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Saída exemplo**:
```
k7xJ9pQmL2nR8vW3yT6uB4cF1dG5hK0sA9zX2wE7qP6
```

### 2. Configurar .env

**Desenvolvimento**:
```env
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=k7xJ9pQmL2nR8vW3yT6uB4cF1dG5hK0sA9zX2wE7qP6

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgresql://user:pass@localhost:5432/agendazap
REDIS_URL=redis://localhost:6379/0
```

**Produção**:
```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<GERAR_NOVA_CHAVE_DIFERENTE_DO_DEV>

ALLOWED_ORIGINS=https://agendazap.com,https://www.agendazap.com
ALLOWED_HOSTS=agendazap.com,www.agendazap.com

DATABASE_URL=postgresql://user:SENHA_FORTE@prod-db:5432/agendazap
REDIS_URL=redis://:SENHA_REDIS@prod-redis:6379/0
REDIS_PASSWORD=SENHA_REDIS
```

---

## 🔑 Registro com Senha Forte

### Requisitos de Senha

#### ✅ Senha VÁLIDA:
```
MyS3cur3P@ssw0rd!
```
- ✅ 16 caracteres
- ✅ Maiúscula (M, S, P)
- ✅ Minúscula (y, u, r, e, s, s, w, r, d)
- ✅ Número (3, 0)
- ✅ Especial (@, !)
- ✅ Sem repetições excessivas
- ✅ Não é senha comum

#### ❌ Senhas INVÁLIDAS:

```python
"senha123"           # ❌ Muito curta (< 12)
"senhasenha12"       # ❌ Sem maiúscula
"SENHASENHA12"       # ❌ Sem minúscula
"SenhaSenha"         # ❌ Sem número
"SenhaSenha123"      # ❌ Sem caractere especial
"Senha1111111!"      # ❌ Muitas repetições (1111)
"Password123!"       # ❌ Senha comum
"Abcdef123456!"      # ❌ Sequência óbvia (123456)
```

### Exemplo de Registro

**Request**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@exemplo.com",
    "password": "MyS3cur3P@ssw0rd!",
    "template_type": "service_table",
    "whatsapp_number": "+5511999999999"
  }'
```

**Response (Sucesso)**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@exemplo.com",
    "is_verified": false,
    "is_active": true,
    "plan_type": "FREE"
  },
  "message": "Usuário registrado com sucesso"
}
```

**Response (Erro - Senha Fraca)**:
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Senha deve conter pelo menos um caractere especial (!@#$%^&* etc)",
      "type": "value_error"
    }
  ]
}
```

---

## 🔐 Login e Logout Seguro

### Login

**Request**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@exemplo.com",
    "password": "MyS3cur3P@ssw0rd!"
  }'
```

**Response**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@exemplo.com",
    "is_verified": false,
    "is_active": true
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "Login realizado com sucesso"
}
```

### Logout (Invalidação Imediata)

**Request**:
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response**:
```json
{
  "message": "Logout realizado com sucesso"
}
```

### Tentar Usar Token Após Logout

**Request**:
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response (Erro)**:
```json
{
  "detail": "Token foi revogado. Faça login novamente"
}
```

---

## ✉️ Verificação de Email

### 1. Gerar Token de Verificação (Após Registro)

**Automático**: Token é gerado automaticamente no registro.

**Manual** (reenviar):
```bash
curl -X POST http://localhost:8000/api/auth/resend-verification \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response**:
```json
{
  "message": "Email de verificação enviado",
  "token": "xJ3kR9pQmL2nR8vW3yT6uB4cF1dG5hK0s"
}
```

### 2. Verificar Email

**Request** (usuário clica no link do email):
```bash
curl -X POST http://localhost:8000/api/auth/verify-email/xJ3kR9pQmL2nR8vW3yT6uB4cF1dG5hK0s
```

**Response (Sucesso)**:
```json
{
  "message": "Email verificado com sucesso",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response (Token Expirado)**:
```json
{
  "detail": "Token inválido ou expirado"
}
```

### 3. Verificar Status

**Request**:
```bash
curl -X GET http://localhost:8000/api/auth/verification-status \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response**:
```json
{
  "is_verified": true,
  "email": "usuario@exemplo.com",
  "requires_verification": false
}
```

### 4. Tentar Acessar Sem Verificar (Produção)

**Request** (em produção com email não verificado):
```bash
curl -X GET http://localhost:8000/api/appointments \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response (Erro)**:
```json
{
  "detail": "Email não verificado. Por favor, verifique seu email antes de continuar."
}
```

---

## 🧪 Testes de Segurança

### Teste 1: Senha Fraca

```bash
# Deve REJEITAR
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@teste.com",
    "password": "senha123",
    "template_type": "service_table"
  }'
```

**Resultado Esperado**: ❌ Erro 422 - "Senha muito fraca"

### Teste 2: Timing Attack

```bash
# Testar com usuário que NÃO existe
time curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "naoexiste@teste.com", "password": "qualquer"}'

# Testar com usuário que EXISTE mas senha errada
time curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "existe@teste.com", "password": "errada123"}'
```

**Resultado Esperado**: ⏱️ Tempos similares (~200-300ms)

### Teste 3: Token Blacklist

```bash
# 1. Fazer login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@teste.com", "password": "MyS3cur3P@ssw0rd!"}' \
  | jq -r '.tokens.access_token')

# 2. Testar acesso (deve funcionar)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 3. Fazer logout
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# 4. Tentar acessar novamente (deve FALHAR)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**Resultado Esperado**: 
- ✅ Passo 2: Sucesso
- ❌ Passo 4: Erro 401 - "Token foi revogado"

### Teste 4: CORS

```bash
# Tentar de origem não autorizada
curl -X POST http://localhost:8000/api/auth/login \
  -H "Origin: https://site-malicioso.com" \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@teste.com", "password": "senha"}'
```

**Resultado Esperado**: ❌ CORS policy error

### Teste 5: XSS em Templates

```bash
# Criar cliente com nome malicioso
curl -X POST http://localhost:8000/api/clients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<script>alert(\"XSS\")</script>",
    "whatsapp": "+5511999999999"
  }'

# Renderizar template com esse cliente
# O script deve ser escapado como: &lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;
```

**Resultado Esperado**: ✅ HTML escapado, script não executado

---

## 📊 Monitoramento

### Logs de Segurança

Os logs agora são seguros e não vazam dados sensíveis:

**Antes**:
```
INFO - GET /api/users?token=abc123&password=secret - 200
```

**Depois**:
```
INFO - GET /api/users - 200
```

### Métricas Importantes

1. **Taxa de Rejeição de Senhas**: Quantas senhas são rejeitadas por serem fracas
2. **Tokens Blacklisted**: Quantos logouts por dia
3. **Tentativas de Login**: Monitorar picos (possível ataque)
4. **Emails Não Verificados**: Usuários que não verificaram após X dias

---

## 🆘 Troubleshooting

### Erro: "SECRET_KEY inválida"

**Problema**: Chave muito curta ou fraca
**Solução**: Gerar nova chave com `secrets.token_urlsafe(32)`

### Erro: "DEBUG deve ser False em produção"

**Problema**: DEBUG=true no .env de produção
**Solução**: Mudar para `DEBUG=false`

### Erro: "Token foi revogado"

**Problema**: Tentando usar token após logout
**Solução**: Fazer login novamente

### Erro: "Email não verificado"

**Problema**: Tentando acessar sem verificar email (produção)
**Solução**: Clicar no link de verificação enviado por email

---

## 📚 Recursos Adicionais

- Documentação Completa: `SECURITY_IMPROVEMENTS.md`
- Resumo Executivo: `RESUMO_SEGURANCA.md`
- Exemplos de API: Swagger UI em `/docs` (apenas desenvolvimento)

---

**Última Atualização**: 12/10/2025

