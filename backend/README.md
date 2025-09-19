# AgendaZap Backend

Sistema de agendamento de serviços com automação WhatsApp - Backend FastAPI

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker e Docker Compose (opcional)

### Instalação

1. **Clone o repositório e navegue para o backend:**
```bash
cd backend
```

2. **Crie um ambiente virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente:**
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Execute o script de desenvolvimento:**
```bash
python run_dev.py
```

### Usando Docker

```bash
# Subir todos os serviços
docker-compose up -d

# Apenas banco e cache
docker-compose up -d postgres redis

# Ver logs
docker-compose logs -f backend
```

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação principal
│   ├── config.py            # Configurações
│   ├── database.py          # Conexão DB
│   ├── dependencies.py      # Dependências globais
│   │
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   ├── api/                 # Endpoints
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── services.py
│   │   ├── appointments.py
│   │   ├── clients.py
│   │   └── webhooks.py
│   │
│   ├── core/                # Lógica de negócio
│   ├── services/            # Serviços
│   ├── utils/               # Utilitários
│   └── tests/               # Testes
│
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── init.sql
├── run_dev.py
└── README.md
```

## 🔧 Configuração

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|---------|
| `ENVIRONMENT` | Ambiente (development/staging/production) | development |
| `DATABASE_URL` | URL do PostgreSQL | postgresql://agendazap:agendazap123@localhost:5432/agendazap |
| `REDIS_URL` | URL do Redis | redis://localhost:6379/0 |
| `SECRET_KEY` | Chave secreta para JWT | your-secret-key-change-in-production |
| `TWILIO_ACCOUNT_SID` | SID da conta Twilio | - |
| `TWILIO_AUTH_TOKEN` | Token de autenticação Twilio | - |
| `SENDGRID_API_KEY` | Chave API do SendGrid | - |

### Banco de Dados

O banco PostgreSQL é inicializado automaticamente com:
- Extensões: `uuid-ossp`, `pg_trgm`
- Enums: `template_type`, `plan_type`, `appointment_status`
- Tabelas: `users`, `services`, `appointments`, `clients`
- Índices para performance
- Triggers para `updated_at`

## 📚 API Endpoints

### Autenticação
- `POST /api/auth/register` - Registrar usuário
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Renovar token
- `POST /api/auth/logout` - Logout

### Usuários
- `GET /api/users/profile` - Perfil do usuário
- `PUT /api/users/profile` - Atualizar perfil
- `GET /api/users/plan` - Informações do plano
- `POST /api/users/upgrade` - Upgrade de plano

### Serviços
- `GET /api/services` - Listar serviços
- `POST /api/services` - Criar serviço
- `GET /api/services/{id}` - Obter serviço
- `PUT /api/services/{id}` - Atualizar serviço
- `DELETE /api/services/{id}` - Deletar serviço

### Agendamentos
- `GET /api/appointments` - Listar agendamentos
- `POST /api/appointments` - Criar agendamento
- `GET /api/appointments/{id}` - Obter agendamento
- `PUT /api/appointments/{id}` - Atualizar agendamento
- `DELETE /api/appointments/{id}` - Deletar agendamento

### Clientes
- `GET /api/clients` - Listar clientes
- `POST /api/clients` - Criar cliente
- `GET /api/clients/{id}` - Obter cliente
- `PUT /api/clients/{id}` - Atualizar cliente
- `DELETE /api/clients/{id}` - Deletar cliente

### Webhooks (n8n)
- `POST /api/webhooks/appointment` - Webhook de agendamento
- `POST /api/webhooks/sync` - Webhook de sincronização
- `POST /api/webhooks/message` - Webhook de mensagem

## 🏗️ Arquitetura

### Stack Tecnológico
- **FastAPI**: Framework web moderno e rápido
- **PostgreSQL**: Banco de dados principal
- **Redis**: Cache e filas de mensagens
- **SQLAlchemy**: ORM para Python
- **Pydantic**: Validação de dados
- **JWT**: Autenticação
- **Twilio**: WhatsApp Business API
- **SendGrid**: Emails transacionais

### Fluxo de Dados
```
Cliente → Frontend → FastAPI → PostgreSQL
                ↓
            n8n (WhatsApp) ← Redis (Filas)
```

## 🧪 Desenvolvimento

### Executar Testes
```bash
pytest
pytest --cov=app tests/
```

### Formatação de Código
```bash
black app/
isort app/
flake8 app/
```

### Logs
Os logs são salvos em `logs/agendazap.log` e também exibidos no console.

## 🚀 Deploy

### Produção
1. Configure as variáveis de ambiente de produção
2. Execute as migrações do banco
3. Use um servidor WSGI como Gunicorn:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```bash
docker build -t agendazap-backend .
docker run -p 8000:8000 --env-file .env agendazap-backend
```

## 📊 Monitoramento

### Health Check
- `GET /health` - Status da aplicação

### Métricas
- Logs estruturados com timestamps
- Middleware de logging de requests
- Error handling global

## 🔒 Segurança

- JWT para autenticação
- CORS configurado
- Rate limiting
- Validação de dados com Pydantic
- Hash de senhas com bcrypt
- HTTPS em produção

## 📝 Próximos Passos

1. ✅ Estrutura base do FastAPI
2. ✅ Configurações e dependências
3. ✅ Endpoints básicos
4. 🔄 Modelos de dados (SQLAlchemy)
5. 🔄 Autenticação JWT
6. 🔄 Integração com n8n
7. 🔄 Testes automatizados

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
