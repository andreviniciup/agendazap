# 📚 AgendaZap Backend - Documentação Completa

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Arquitetura e Tecnologias](#-arquitetura-e-tecnologias)
3. [Estrutura do Projeto](#-estrutura-do-projeto)
4. [Modelos de Dados](#-modelos-de-dados)
5. [APIs e Endpoints](#-apis-e-endpoints)
6. [Serviços e Lógica de Negócio](#-serviços-e-lógica-de-negócio)
7. [Sistema de Filas e Workers](#-sistema-de-filas-e-workers)
8. [Configuração e Deployment](#-configuração-e-deployment)
9. [Funcionalidades Implementadas](#-funcionalidades-implementadas)
10. [Exemplos de Uso](#-exemplos-de-uso)

---

## 🎯 Visão Geral

O **AgendaZap Backend** é uma API RESTful desenvolvida em **FastAPI** para gerenciar agendamentos de serviços com automação via WhatsApp. O sistema oferece funcionalidades completas de gestão de usuários, serviços, agendamentos, clientes e notificações automáticas.

### 🎯 Objetivos Principais
- **Gestão completa de agendamentos** com verificação de disponibilidade
- **Automação de notificações** via WhatsApp e email
- **Sistema de planos** com limites e controle de uso
- **Gestão avançada de clientes** com histórico e métricas
- **API robusta** com autenticação JWT e validação de dados

---

## 🏗️ Arquitetura e Tecnologias

### 🛠️ Stack Tecnológico

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **FastAPI** | 0.104.1 | Framework web moderno e rápido |
| **Python** | 3.12+ | Linguagem de programação |
| **PostgreSQL** | 15 | Banco de dados relacional |
| **Redis** | 7 | Cache e sistema de filas |
| **SQLAlchemy** | 2.0.23 | ORM para interação com banco |
| **Pydantic** | 2.5.0 | Validação e serialização de dados |
| **JWT** | 3.3.0 | Autenticação stateless |
| **Docker** | - | Containerização |

### 🏛️ Arquitetura do Sistema

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

### 🔄 Fluxo de Dados

1. **Cliente** faz requisição para API
2. **FastAPI** processa e valida dados
3. **SQLAlchemy** interage com PostgreSQL
4. **Redis** gerencia cache e filas
5. **Workers** processam notificações
6. **WhatsApp/Email** enviam mensagens

---

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicação principal FastAPI
│   ├── config.py              # Configurações da aplicação
│   ├── database.py            # Configuração do banco de dados
│   ├── dependencies.py        # Dependências globais
│   │
│   ├── api/                   # Endpoints da API
│   │   ├── auth.py           # Autenticação
│   │   ├── users.py          # Gestão de usuários
│   │   ├── services.py       # Gestão de serviços
│   │   ├── appointments.py   # Gestão de agendamentos
│   │   ├── clients.py        # Gestão de clientes
│   │   ├── queues.py         # Gestão de filas
│   │   └── webhooks.py       # Webhooks
│   │
│   ├── models/               # Modelos de dados (SQLAlchemy)
│   │   ├── user.py          # Modelo de usuário
│   │   ├── service.py       # Modelo de serviço
│   │   ├── appointment.py   # Modelo de agendamento
│   │   └── client.py        # Modelo de cliente
│   │
│   ├── schemas/              # Schemas de validação (Pydantic)
│   │   ├── user.py          # Schemas de usuário
│   │   ├── service.py       # Schemas de serviço
│   │   ├── appointment.py   # Schemas de agendamento
│   │   ├── client.py        # Schemas de cliente
│   │   ├── auth.py          # Schemas de autenticação
│   │   └── plan.py          # Schemas de planos
│   │
│   ├── services/             # Lógica de negócio
│   │   ├── auth_service.py  # Serviço de autenticação
│   │   ├── user_service.py  # Serviço de usuários
│   │   ├── service_service.py # Serviço de serviços
│   │   ├── appointment_service.py # Serviço de agendamentos
│   │   ├── client_service.py # Serviço de clientes
│   │   ├── plan_service.py  # Serviço de planos
│   │   ├── queue_service.py # Serviço de filas
│   │   └── notification_service.py # Serviço de notificações
│   │
│   ├── workers/              # Workers para processamento assíncrono
│   │   └── message_worker.py # Worker de mensagens
│   │
│   ├── middleware/           # Middlewares
│   │   └── plan_middleware.py # Middleware de verificação de planos
│   │
│   ├── core/                 # Configurações centrais
│   │   └── security.py      # Configurações de segurança
│   │
│   └── utils/                # Utilitários
│       └── enums.py         # Enums da aplicação
│
├── docker-compose.yml        # Configuração Docker
├── Dockerfile               # Imagem Docker
├── requirements.txt         # Dependências Python
├── init.sql                # Script de inicialização do banco
├── start_workers.py        # Script para iniciar workers
└── env.example             # Exemplo de variáveis de ambiente
```

---

## 🗄️ Modelos de Dados

### 👤 Modelo User (Usuário)

```python
class User(Base):
    __tablename__ = "users"
    
    # Identificação
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Dados do negócio
    business_name = Column(String(255), nullable=True)
    template_type = Column(Enum(TemplateType), nullable=False)
    whatsapp_number = Column(String(20), nullable=True)
    
    # Status e controle
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    plan_type = Column(Enum(PlanType), default=PlanType.FREE)
    
    # Relacionamentos
    services = relationship("Service", back_populates="user")
    appointments = relationship("Appointment", back_populates="user")
    clients = relationship("Client", back_populates="user")
```

**Campos Principais:**
- **Identificação**: ID único, email, senha hashada
- **Negócio**: Nome do negócio, tipo de template, WhatsApp
- **Status**: Ativo, verificado, tipo de plano
- **Relacionamentos**: Serviços, agendamentos, clientes

### 🛍️ Modelo Service (Serviço)

```python
class Service(Base):
    __tablename__ = "services"
    
    # Identificação
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID, ForeignKey("service_categories.id"), nullable=True)
    
    # Dados do serviço
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=False)  # em minutos
    price = Column(Float, nullable=True)
    
    # Configurações
    is_active = Column(Boolean, default=True)
    images = Column(ARRAY(String), nullable=True)
    credentials = Column(JSON, nullable=True)
    promotions = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="services")
    category = relationship("ServiceCategory", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
```

**Campos Principais:**
- **Identificação**: ID único, usuário proprietário, categoria
- **Dados**: Nome, descrição, duração, preço
- **Configurações**: Ativo, imagens, credenciais, promoções
- **Relacionamentos**: Usuário, categoria, agendamentos

### 📅 Modelo Appointment (Agendamento)

```python
class Appointment(Base):
    __tablename__ = "appointments"
    
    # Identificação
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    service_id = Column(UUID, ForeignKey("services.id"), nullable=False)
    client_id = Column(UUID, ForeignKey("clients.id"), nullable=True)
    
    # Dados do agendamento
    client_name = Column(String(255), nullable=False)
    client_whatsapp = Column(String(20), nullable=False)
    client_email = Column(String(255), nullable=True)
    
    # Horários
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Status e controle
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    is_confirmed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    
    # Notas e dados extras
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    custom_fields = Column(JSON, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")
```

**Campos Principais:**
- **Identificação**: ID único, usuário, serviço, cliente
- **Dados do cliente**: Nome, WhatsApp, email
- **Horários**: Início, fim, duração
- **Status**: Pendente, confirmado, cancelado, concluído
- **Relacionamentos**: Usuário, serviço, cliente

### 👥 Modelo Client (Cliente)

```python
class Client(Base):
    __tablename__ = "clients"
    
    # Identificação
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Informações básicas
    name = Column(String(255), nullable=False)
    whatsapp = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Status e controle
    is_active = Column(Boolean, default=True)
    is_vip = Column(Boolean, default=False)
    
    # Histórico de agendamentos
    first_appointment_at = Column(DateTime, nullable=True)
    last_appointment_at = Column(DateTime, nullable=True)
    total_appointments = Column(Integer, default=0)
    completed_appointments = Column(Integer, default=0)
    cancelled_appointments = Column(Integer, default=0)
    no_show_appointments = Column(Integer, default=0)
    
    # Métricas de frequência
    frequency_score = Column(Float, default=0.0)  # 0-100
    appointments_this_month = Column(Integer, default=0)
    appointments_last_month = Column(Integer, default=0)
    average_days_between_appointments = Column(Float, default=0.0)
    
    # Preferências e comportamento
    preferred_services = Column(ARRAY(UUID), nullable=True)
    preferred_days = Column(ARRAY(String), nullable=True)
    preferred_times = Column(ARRAY(String), nullable=True)
    communication_preference = Column(String(20), default="whatsapp")
    
    # Dados demográficos
    birth_date = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    
    # Métricas financeiras
    total_spent = Column(Float, default=0.0)
    average_ticket = Column(Float, default=0.0)
    last_payment_at = Column(DateTime, nullable=True)
    
    # Dados de marketing
    source = Column(String(100), nullable=True)
    referral_code = Column(String(50), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Metadados
    custom_fields = Column(JSON, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client")
```

**Campos Principais:**
- **Identificação**: ID único, usuário proprietário
- **Informações básicas**: Nome, WhatsApp, email, notas
- **Histórico**: Datas, contadores de agendamentos
- **Métricas**: Score de frequência, agendamentos mensais
- **Preferências**: Serviços, dias, horários preferidos
- **Dados demográficos**: Data nascimento, gênero, endereço
- **Métricas financeiras**: Total gasto, ticket médio
- **Marketing**: Fonte, código indicação, tags

---

## 🔌 APIs e Endpoints

### 🔐 Autenticação (`/api/auth`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `POST` | `/register` | Registrar novo usuário | ❌ |
| `POST` | `/login` | Fazer login | ❌ |
| `POST` | `/logout` | Fazer logout | ✅ |
| `POST` | `/refresh` | Renovar token | ✅ |

**Exemplo de Registro:**
```json
POST /api/auth/register
{
  "email": "usuario@exemplo.com",
  "password": "Senha123!",
  "template_type": "service_table",
  "whatsapp_number": "+5511999999999"
}
```

**Exemplo de Login:**
```json
POST /api/auth/login
{
  "email": "usuario@exemplo.com",
  "password": "Senha123!"
}
```

### 👤 Usuários (`/api/users`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/profile` | Obter perfil do usuário | ✅ |
| `PUT` | `/profile` | Atualizar perfil | ✅ |
| `GET` | `/usage` | Obter estatísticas de uso | ✅ |
| `POST` | `/upgrade-plan` | Fazer upgrade de plano | ✅ |

**Exemplo de Perfil:**
```json
GET /api/users/profile
Authorization: Bearer <token>

Response:
{
  "id": "uuid",
  "email": "usuario@exemplo.com",
  "business_name": "Meu Negócio",
  "template_type": "service_table",
  "whatsapp_number": "+5511999999999",
  "plan_type": "free",
  "is_active": true,
  "is_verified": false
}
```

### 🛍️ Serviços (`/api/services`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/` | Listar serviços | ✅ |
| `POST` | `/` | Criar serviço | ✅ |
| `GET` | `/{service_id}` | Obter serviço específico | ✅ |
| `PUT` | `/{service_id}` | Atualizar serviço | ✅ |
| `DELETE` | `/{service_id}` | Deletar serviço | ✅ |
| `GET` | `/stats` | Estatísticas dos serviços | ✅ |

**Exemplo de Criação de Serviço:**
```json
POST /api/services/
{
  "name": "Corte de Cabelo",
  "description": "Corte moderno e estiloso",
  "duration": 60,
  "price": 50.0,
  "category_id": "uuid"
}
```

### 📅 Agendamentos (`/api/appointments`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/` | Listar agendamentos | ✅ |
| `POST` | `/` | Criar agendamento | ✅ |
| `GET` | `/{appointment_id}` | Obter agendamento específico | ✅ |
| `PUT` | `/{appointment_id}` | Atualizar agendamento | ✅ |
| `DELETE` | `/{appointment_id}` | Cancelar agendamento | ✅ |
| `GET` | `/availability` | Verificar disponibilidade | ✅ |
| `GET` | `/stats` | Estatísticas dos agendamentos | ✅ |
| `POST` | `/public` | Agendamento público | ❌ |

**Exemplo de Criação de Agendamento:**
```json
POST /api/appointments/
{
  "service_id": "uuid",
  "client_name": "João Silva",
  "client_whatsapp": "+5511888888888",
  "client_email": "joao@email.com",
  "start_time": "2024-01-15T14:00:00Z",
  "notes": "Primeiro agendamento"
}
```

**Exemplo de Verificação de Disponibilidade:**
```json
GET /api/appointments/availability?service_id=uuid&date=2024-01-15&duration=60

Response:
{
  "available_slots": [
    "2024-01-15T09:00:00Z",
    "2024-01-15T10:00:00Z",
    "2024-01-15T11:00:00Z"
  ],
  "conflicts": []
}
```

### 👥 Clientes (`/api/clients`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/` | Listar clientes | ✅ |
| `POST` | `/` | Criar cliente | ✅ |
| `GET` | `/{client_id}` | Obter cliente específico | ✅ |
| `PUT` | `/{client_id}` | Atualizar cliente | ✅ |
| `DELETE` | `/{client_id}` | Deletar cliente | ✅ |
| `POST` | `/bulk-update` | Atualização em massa | ✅ |
| `GET` | `/{client_id}/history` | Histórico do cliente | ✅ |
| `GET` | `/analytics/overview` | Analytics de clientes | ✅ |

**Exemplo de Listagem de Clientes:**
```json
GET /api/clients/?query=João&is_active=true&min_appointments=1&page=1&per_page=10

Response:
{
  "clients": [
    {
      "id": "uuid",
      "name": "João Silva",
      "whatsapp": "+5511888888888",
      "email": "joao@email.com",
      "total_appointments": 5,
      "frequency_score": 85.5,
      "is_regular_customer": true,
      "last_appointment_at": "2024-01-10T14:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10,
  "total_pages": 1
}
```

**Exemplo de Analytics:**
```json
GET /api/clients/analytics/overview

Response:
{
  "total_clients": 150,
  "active_clients": 120,
  "inactive_clients": 30,
  "clients_with_appointments": 100,
  "average_appointments_per_client": 3.2,
  "most_frequent_clients": [...],
  "top_preferred_services": {
    "Corte de Cabelo": 45,
    "Manicure": 32,
    "Pedicure": 28
  },
  "clients_by_creation_month": {
    "2024-01": 25,
    "2024-02": 30,
    "2024-03": 35
  }
}
```

### 📬 Filas (`/api/queues`)

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/status` | Status das filas | ✅ |
| `GET` | `/failed/{queue_name}` | Mensagens falhadas | ✅ |
| `DELETE` | `/failed/{queue_name}` | Limpar mensagens falhadas | ✅ |
| `POST` | `/test/whatsapp` | Teste WhatsApp | ✅ |
| `POST` | `/test/email` | Teste Email | ✅ |
| `GET` | `/workers/status` | Status dos workers | ✅ |
| `POST` | `/workers/start` | Iniciar workers | ✅ |
| `POST` | `/workers/stop` | Parar workers | ✅ |

---

## ⚙️ Serviços e Lógica de Negócio

### 🔐 AuthService

**Responsabilidades:**
- Registro de novos usuários
- Autenticação e geração de tokens JWT
- Validação de credenciais
- Gerenciamento de sessões

**Métodos Principais:**
```python
async def register_user(user_data: UserCreate) -> RegisterResponse
async def authenticate_user(login_data: UserLogin) -> LoginResponse
async def refresh_token(refresh_data: RefreshTokenRequest) -> LoginResponse
async def logout_user(token: str) -> LogoutResponse
```

### 👤 UserService

**Responsabilidades:**
- Gestão de perfis de usuários
- Atualização de dados pessoais
- Controle de verificação de email
- Gerenciamento de configurações

**Métodos Principais:**
```python
async def get_user_profile(user_id: UUID) -> UserResponse
async def update_user_profile(user_id: UUID, user_data: UserUpdate) -> UserResponse
async def verify_email(user_id: UUID, verification_code: str) -> bool
```

### 🛍️ ServiceService

**Responsabilidades:**
- CRUD de serviços
- Validação baseada no template do usuário
- Verificação de limites de plano
- Gestão de categorias

**Métodos Principais:**
```python
async def create_service(service_data: ServiceCreate, user: User) -> Service
async def get_services(user: User, search_params: ServiceSearch) -> Dict
async def update_service(service_id: UUID, service_data: ServiceUpdate, user: User) -> Service
async def delete_service(service_id: UUID, user: User) -> bool
```

### 📅 AppointmentService

**Responsabilidades:**
- CRUD de agendamentos
- Verificação de disponibilidade
- Detecção de conflitos
- Integração com clientes
- Agendamento de notificações

**Métodos Principais:**
```python
async def create_appointment(appointment_data: AppointmentCreate, user: User) -> Appointment
async def check_availability(user_id: UUID, service_id: UUID, start_time: datetime, duration: int) -> Tuple[bool, str]
async def get_appointments(user: User, search_params: AppointmentSearch) -> Dict
async def cancel_appointment(appointment_id: UUID, user: User, cancellation_data: AppointmentCancellation) -> Appointment
```

### 👥 ClientService

**Responsabilidades:**
- CRUD de clientes
- Criação automática de clientes
- Cálculo de métricas de frequência
- Sistema de busca avançado
- Analytics e relatórios

**Métodos Principais:**
```python
async def create_client(client_data: ClientCreate, user: User) -> Client
async def find_or_create_client(name: str, whatsapp: str, email: str, user: User) -> Client
async def update_client_metrics(client_id: UUID, user: User) -> None
async def get_clients(user: User, search_params: ClientSearch) -> Dict
async def get_client_analytics(user: User) -> ClientAnalytics
```

### 📊 PlanService

**Responsabilidades:**
- Verificação de limites de planos
- Controle de uso de recursos
- Alertas de limite
- Upgrade/downgrade de planos

**Métodos Principais:**
```python
async def check_limit(user_id: str, resource: str, amount: int) -> bool
async def increment_usage(user_id: str, resource: str, amount: int) -> None
async def get_usage_stats(user_id: str) -> UsageStats
async def get_plan_limits(plan_type: PlanType) -> PlanLimits
```

### 📬 QueueService

**Responsabilidades:**
- Gerenciamento de filas Redis
- Agendamento de mensagens
- Processamento de notificações
- Retry de mensagens falhadas

**Métodos Principais:**
```python
async def add_message(queue_name: str, message_data: Dict, delay_seconds: int = 0) -> str
async def get_next_message(queue_name: str, consumer_group: str, consumer_name: str) -> Dict
async def acknowledge_message(queue_name: str, consumer_group: str, message_id: str) -> None
```

### 📱 NotificationService

**Responsabilidades:**
- Envio de mensagens WhatsApp
- Envio de emails
- Gerenciamento de templates
- Integração com APIs externas

**Métodos Principais:**
```python
async def send_notification(notification_type: str, recipient_whatsapp: str, recipient_email: str, data: Dict) -> Dict
async def send_custom_whatsapp_message(recipient_whatsapp: str, message_content: str) -> bool
async def send_custom_email(recipient_email: str, subject: str, body: str) -> bool
```

---

## 🔄 Sistema de Filas e Workers

### 📬 Arquitetura de Filas

O sistema utiliza **Redis Streams** para gerenciar filas de mensagens de forma robusta e escalável.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │     Redis       │    │    Workers      │
│   Backend       │───►│    Streams      │───►│   (Processors)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🏷️ Tipos de Filas

| Fila | Propósito | Exemplo de Uso |
|------|-----------|----------------|
| `appointment_confirmations` | Confirmações de agendamento | "Seu agendamento foi confirmado" |
| `appointment_reminders` | Lembretes de agendamento | "Lembrete: seu agendamento é amanhã" |
| `appointment_cancellations` | Cancelamentos | "Seu agendamento foi cancelado" |
| `appointment_follow_ups` | Follow-ups pós-agendamento | "Como foi seu atendimento?" |
| `whatsapp_messages` | Mensagens WhatsApp customizadas | Mensagens personalizadas |
| `email_notifications` | Notificações por email | Emails de marketing |

### ⚙️ Workers

**MessageWorker** processa mensagens de forma assíncrona:

```python
class MessageWorker:
    async def start(self):
        """Inicia o worker para processar mensagens"""
        while self._running:
            # Processar mensagens agendadas
            await self._process_scheduled_messages()
            
            # Processar mensagens da fila principal
            message = await self.queue_service.get_next_message(...)
            if message:
                await self._process_message(message)
```

**WorkerManager** gerencia múltiplos workers:

```python
class WorkerManager:
    async def start_workers(self):
        """Inicia todos os workers"""
        for queue_name, worker in self.workers.items():
            task = asyncio.create_task(worker.start())
            self.worker_tasks[queue_name] = task
```

### 🔄 Fluxo de Notificações

1. **Agendamento criado** → Sistema agenda notificações
2. **Mensagens enfileiradas** → Redis Streams
3. **Workers processam** → Consomem mensagens
4. **APIs externas** → WhatsApp/Email
5. **Retry automático** → Em caso de falha

### 📊 Monitoramento de Filas

```json
GET /api/queues/status

Response:
{
  "appointment_confirmations": {
    "length": 15,
    "groups": 1,
    "last-entry": "1640995200000-0"
  },
  "appointment_reminders": {
    "length": 8,
    "groups": 1,
    "last-entry": "1640995200000-1"
  },
  "scheduled_messages": {
    "length": 23
  }
}
```

---

## ⚙️ Configuração e Deployment

### 🐳 Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agendazap
      POSTGRES_USER: agendazap
      POSTGRES_PASSWORD: agendazap123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://agendazap:agendazap123@postgres:5432/agendazap
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 🔧 Variáveis de Ambiente

```bash
# Banco de dados
DATABASE_URL=postgresql://user:password@localhost:5432/agendazap

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# WhatsApp API
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_API_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com

# Aplicação
ENVIRONMENT=development
ALLOWED_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
```

### 🚀 Comandos de Deploy

```bash
# Desenvolvimento
docker-compose up -d

# Produção
docker-compose -f docker-compose.prod.yml up -d

# Iniciar workers
python start_workers.py

# Verificar logs
docker-compose logs -f backend
```

### 📊 Monitoramento

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Status das Filas:**
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/queues/status
```

**Métricas de Uso:**
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users/usage
```

---

## 🎯 Funcionalidades Implementadas

### ✅ Ação 1.4: Estrutura Base do Backend
- [x] Configuração FastAPI com hot reload
- [x] Integração PostgreSQL + SQLAlchemy
- [x] Integração Redis para cache
- [x] Configuração Docker Compose
- [x] Middleware de CORS e logging
- [x] Health check endpoint
- [x] Estrutura de pastas organizada

### ✅ Ação 2.1: Sistema de Autenticação JWT
- [x] Registro de usuários com validação
- [x] Login com JWT tokens
- [x] Refresh token automático
- [x] Logout com blacklist
- [x] Middleware de autenticação
- [x] Validação de senhas seguras
- [x] Hash de senhas com bcrypt

### ✅ Ação 2.2: Modelo de Usuário Completo
- [x] Modelo User expandido
- [x] Templates de negócio (consultation, service_table)
- [x] Verificação de email
- [x] Perfil de usuário completo
- [x] Endpoints de gestão de usuário
- [x] Validação de dados com Pydantic

### ✅ Ação 2.3: Sistema de Planos e Limites
- [x] Modelo de planos (FREE, STARTER, PRO, ENTERPRISE)
- [x] Controle de limites por plano
- [x] Contadores de uso em Redis
- [x] Middleware de verificação de limites
- [x] Sistema de alertas
- [x] Upgrade/downgrade de planos
- [x] Reset mensal de contadores

### ✅ Ação 3.1: Gestão de Serviços
- [x] CRUD completo de serviços
- [x] Categorias de serviços
- [x] Validação baseada no template
- [x] Campos customizados (JSONB)
- [x] Sistema de busca e filtros
- [x] Estatísticas de serviços
- [x] Upload de imagens (preparado)

### ✅ Ação 3.2: Sistema de Agendamentos
- [x] CRUD completo de agendamentos
- [x] Verificação de disponibilidade
- [x] Detecção de conflitos
- [x] Agendamentos públicos
- [x] Status de agendamentos
- [x] Sistema de busca avançado
- [x] Estatísticas e relatórios

### ✅ Ação 3.3: Gestão de Clientes
- [x] Modelo de cliente expandido
- [x] Criação automática no primeiro agendamento
- [x] Sistema de histórico completo
- [x] Métricas de frequência
- [x] Identificação de serviços preferidos
- [x] Busca avançada de clientes
- [x] Analytics e relatórios
- [x] Integração com agendamentos

### ✅ Sistema de Filas e Notificações
- [x] Redis Streams para filas
- [x] Workers assíncronos
- [x] Agendamento de mensagens
- [x] Integração WhatsApp API
- [x] Integração Email SMTP
- [x] Sistema de retry
- [x] Monitoramento de filas
- [x] Templates de mensagens

---

## 💡 Exemplos de Uso

### 🔐 Fluxo de Autenticação

```python
# 1. Registrar usuário
response = requests.post("http://localhost:8000/api/auth/register", json={
    "email": "usuario@exemplo.com",
    "password": "Senha123!",
    "template_type": "service_table",
    "whatsapp_number": "+5511999999999"
})

# 2. Fazer login
response = requests.post("http://localhost:8000/api/auth/login", json={
    "email": "usuario@exemplo.com",
    "password": "Senha123!"
})
token = response.json()["access_token"]

# 3. Usar token em requisições
headers = {"Authorization": f"Bearer {token}"}
```

### 🛍️ Gestão de Serviços

```python
# Criar serviço
service_data = {
    "name": "Corte de Cabelo",
    "description": "Corte moderno e estiloso",
    "duration": 60,
    "price": 50.0
}
response = requests.post("http://localhost:8000/api/services/", 
                        json=service_data, headers=headers)

# Listar serviços
response = requests.get("http://localhost:8000/api/services/", headers=headers)
services = response.json()["services"]
```

### 📅 Gestão de Agendamentos

```python
# Verificar disponibilidade
params = {
    "service_id": "uuid-do-servico",
    "date": "2024-01-15",
    "duration": 60
}
response = requests.get("http://localhost:8000/api/appointments/availability", 
                       params=params, headers=headers)
available_slots = response.json()["available_slots"]

# Criar agendamento
appointment_data = {
    "service_id": "uuid-do-servico",
    "client_name": "João Silva",
    "client_whatsapp": "+5511888888888",
    "client_email": "joao@email.com",
    "start_time": "2024-01-15T14:00:00Z",
    "notes": "Primeiro agendamento"
}
response = requests.post("http://localhost:8000/api/appointments/", 
                        json=appointment_data, headers=headers)
```

### 👥 Gestão de Clientes

```python
# Buscar clientes
params = {
    "query": "João",
    "is_active": True,
    "min_appointments": 1,
    "page": 1,
    "per_page": 10
}
response = requests.get("http://localhost:8000/api/clients/", 
                       params=params, headers=headers)
clients = response.json()["clients"]

# Obter analytics
response = requests.get("http://localhost:8000/api/clients/analytics/overview", 
                       headers=headers)
analytics = response.json()
```

### 📬 Sistema de Filas

```python
# Verificar status das filas
response = requests.get("http://localhost:8000/api/queues/status", headers=headers)
queue_status = response.json()

# Enviar mensagem de teste
test_data = {
    "recipient_whatsapp": "+5511888888888",
    "message_content": "Mensagem de teste"
}
response = requests.post("http://localhost:8000/api/queues/test/whatsapp", 
                        json=test_data, headers=headers)
```

---

## 🎉 Conclusão

O **AgendaZap Backend** está completamente implementado com todas as funcionalidades principais:

### 🏆 **Principais Conquistas:**
- ✅ **API RESTful completa** com FastAPI
- ✅ **Autenticação JWT** robusta e segura
- ✅ **Sistema de planos** com controle de limites
- ✅ **Gestão completa** de serviços, agendamentos e clientes
- ✅ **Sistema de filas** para notificações automáticas
- ✅ **Integração WhatsApp/Email** para automação
- ✅ **Analytics avançados** e relatórios
- ✅ **Arquitetura escalável** com Docker

### 🚀 **Próximos Passos:**
1. **Frontend** - Interface web para usuários
2. **Mobile App** - Aplicativo móvel
3. **Integrações** - Pagamentos, CRM, etc.
4. **Analytics** - Dashboard avançado
5. **Deploy** - Produção na nuvem

O sistema está pronto para uso e pode ser facilmente expandido com novas funcionalidades! 🎯
