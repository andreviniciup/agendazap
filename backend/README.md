# 🚀 AgendaZap Backend

Sistema de agendamento de serviços com automação via WhatsApp - Backend API

## 📋 Resumo Executivo

O **AgendaZap Backend** é uma API RESTful desenvolvida em **FastAPI** que oferece funcionalidades completas para gestão de agendamentos de serviços com automação de notificações via WhatsApp e email.

### 🎯 **Funcionalidades Principais**

- ✅ **Autenticação JWT** com registro, login e refresh tokens
- ✅ **Sistema de Planos** com controle de limites (FREE, STARTER, PRO, ENTERPRISE)
- ✅ **Gestão de Serviços** com categorias e campos customizados
- ✅ **Sistema de Agendamentos** com verificação de disponibilidade
- ✅ **Gestão de Clientes** com histórico e métricas avançadas
- ✅ **Notificações Automáticas** via WhatsApp e email
- ✅ **Sistema de Filas** com Redis Streams para processamento assíncrono
- ✅ **Analytics e Relatórios** detalhados

## 🛠️ **Stack Tecnológico**

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **FastAPI** | 0.104.1 | Framework web moderno |
| **PostgreSQL** | 15 | Banco de dados relacional |
| **Redis** | 7 | Cache e sistema de filas |
| **SQLAlchemy** | 2.0.23 | ORM |
| **Pydantic** | 2.5.0 | Validação de dados |
| **Docker** | - | Containerização |

## 🚀 **Quick Start**

### 1. **Clone e Configure**
```bash
git clone <repository>
cd backend
cp env.example .env
# Configure as variáveis de ambiente
```

### 2. **Execute com Docker**
```bash
docker-compose up -d
```

### 3. **Acesse a API**
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. **Inicie os Workers**
```bash
python start_workers.py
```

## 📊 **APIs Principais**

### 🔐 **Autenticação**
```bash
POST /api/auth/register    # Registrar usuário
POST /api/auth/login       # Fazer login
POST /api/auth/refresh     # Renovar token
```

### 🛍️ **Serviços**
```bash
GET    /api/services/      # Listar serviços
POST   /api/services/      # Criar serviço
PUT    /api/services/{id}  # Atualizar serviço
DELETE /api/services/{id}  # Deletar serviço
```

### 📅 **Agendamentos**
```bash
GET    /api/appointments/                    # Listar agendamentos
POST   /api/appointments/                    # Criar agendamento
GET    /api/appointments/availability        # Verificar disponibilidade
POST   /api/appointments/public              # Agendamento público
```

### 👥 **Clientes**
```bash
GET    /api/clients/                         # Listar clientes
POST   /api/clients/                         # Criar cliente
GET    /api/clients/{id}/history             # Histórico do cliente
GET    /api/clients/analytics/overview       # Analytics
```

### 📬 **Filas e Notificações**
```bash
GET    /api/queues/status                    # Status das filas
POST   /api/queues/test/whatsapp             # Teste WhatsApp
POST   /api/queues/test/email                # Teste Email
```

## 🏗️ **Arquitetura**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   PostgreSQL    │
│   (React/Vue)   │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │  Cache + Queues │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Workers       │
                       │  (WhatsApp/Email)│
                       └─────────────────┘
```

## 📈 **Funcionalidades Implementadas**

### ✅ **Ação 1.4: Estrutura Base**
- Configuração FastAPI com hot reload
- Integração PostgreSQL + SQLAlchemy
- Integração Redis para cache
- Configuração Docker Compose
- Middleware de CORS e logging

### ✅ **Ação 2.1: Autenticação JWT**
- Registro e login de usuários
- Tokens JWT com refresh automático
- Middleware de autenticação
- Validação de senhas seguras

### ✅ **Ação 2.2: Modelo de Usuário**
- Perfil completo de usuário
- Templates de negócio
- Verificação de email
- Gestão de configurações

### ✅ **Ação 2.3: Sistema de Planos**
- Planos com limites (FREE, STARTER, PRO, ENTERPRISE)
- Controle de uso em tempo real
- Sistema de alertas
- Upgrade/downgrade de planos

### ✅ **Ação 3.1: Gestão de Serviços**
- CRUD completo de serviços
- Categorias de serviços
- Campos customizados
- Sistema de busca e filtros

### ✅ **Ação 3.2: Sistema de Agendamentos**
- CRUD completo de agendamentos
- Verificação de disponibilidade
- Detecção de conflitos
- Agendamentos públicos

### ✅ **Ação 3.3: Gestão de Clientes**
- Modelo de cliente expandido
- Criação automática no primeiro agendamento
- Sistema de histórico completo
- Métricas de frequência
- Analytics avançados

### ✅ **Sistema de Filas e Notificações**
- Redis Streams para filas
- Workers assíncronos
- Integração WhatsApp API
- Integração Email SMTP
- Sistema de retry automático

## 🔧 **Configuração**

### **Variáveis de Ambiente Essenciais**
```bash
# Banco de dados
DATABASE_URL=postgresql://user:password@localhost:5432/agendazap

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here

# WhatsApp API
WHATSAPP_API_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id

# Email
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📊 **Exemplo de Uso**

### **1. Registrar Usuário**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@exemplo.com",
    "password": "Senha123!",
    "template_type": "service_table",
    "whatsapp_number": "+5511999999999"
  }'
```

### **2. Criar Serviço**
```bash
curl -X POST "http://localhost:8000/api/services/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Corte de Cabelo",
    "description": "Corte moderno e estiloso",
    "duration": 60,
    "price": 50.0
  }'
```

### **3. Criar Agendamento**
```bash
curl -X POST "http://localhost:8000/api/appointments/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "uuid-do-servico",
    "client_name": "João Silva",
    "client_whatsapp": "+5511888888888",
    "start_time": "2024-01-15T14:00:00Z"
  }'
```

## 📚 **Documentação Completa**

Para documentação detalhada, consulte: [DOCUMENTATION.md](./DOCUMENTATION.md)

## 🎯 **Status do Projeto**

- ✅ **Backend API**: 100% implementado
- ✅ **Autenticação**: 100% implementado
- ✅ **Sistema de Planos**: 100% implementado
- ✅ **Gestão de Serviços**: 100% implementado
- ✅ **Sistema de Agendamentos**: 100% implementado
- ✅ **Gestão de Clientes**: 100% implementado
- ✅ **Sistema de Filas**: 100% implementado
- ✅ **Notificações**: 100% implementado

## 🚀 **Próximos Passos**

1. **Frontend Web** - Interface para usuários
2. **Mobile App** - Aplicativo móvel
3. **Integrações** - Pagamentos, CRM
4. **Deploy Produção** - Nuvem
5. **Monitoramento** - Logs e métricas

---

**🎉 O AgendaZap Backend está pronto para uso!**