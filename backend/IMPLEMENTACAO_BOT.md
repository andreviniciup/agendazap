# Implementação: Bot Handoff, Mídia e Notificações

## 📋 Resumo Executivo

Implementação completa do sistema de handoff, detecção de mídia, preferências do prestador, onboarding de metadados e preparação para notificações automatizadas no AgendaZap.

## ✅ Features Implementadas

### 1. Templates de Mensagens
- **Arquivo**: `backend/app/services/bot/templates.py`
- **Novos templates**:
  - `handoff`: Mensagem ao transferir para humano
  - `media_handoff`: Mensagem ao detectar mídia não suportada
  - `reminder`: Lembrete de agendamento
  - `confirmation_request`: Pedido de confirmação ao cliente
  - `feedback_request`: Pedido de feedback pós-atendimento
- **Variações**: dia/noite para tom apropriado
- **Parametrização**: nome do cliente, serviço, data/hora, tipo de mídia

### 2. Detecção de Mídia e Handoff Automático
- **Arquivo**: `backend/app/api/webhooks.py`
- **Funcionalidades**:
  - Detecta `audio`, `image`, `video`, `document` em payloads do Twilio e Meta WhatsApp
  - Aciona handoff automaticamente quando mídia é detectada
  - Respeita preferências do usuário (`trigger_on_media`)
  - Envia alerta ao prestador via email e/ou WhatsApp
  - Responde ao cliente com mensagem apropriada

### 3. Handoff por Baixa Confiança
- **Arquivo**: `backend/app/services/bot/bot_service.py`
- **Funcionalidades**:
  - Detecta quando confiança < 0.3 por 3 vezes consecutivas
  - Aciona handoff automático
  - Registra métricas de handoff
  - Usa templates de handoff apropriados

### 4. Estado de Conversa Aprimorado
- **Arquivo**: `backend/app/services/bot/conversation_state.py`
- **Novos métodos**:
  - `mark_handoff()`: Marca handoff com razão e metadados
  - `get_conversation_snippet()`: Obtém últimas N interações
- **Estado padrão** inclui campo `handoff`

### 5. Métricas do Bot
- **Arquivo**: `backend/app/services/bot/bot_metrics.py`
- **Novas métricas**:
  - `handoffs_to_human`: Total de handoffs
  - `handoff_reasons`: Contagem por razão (media, low_confidence, human_requested)
  - `media_detected`: Total de mídias detectadas
  - `media_types`: Contagem por tipo
  - `confirmations_sent/yes/no`: Métricas de confirmação
  - `feedbacks_received`: Total de feedbacks
  - `confirmation_rate`: Taxa de confirmação calculada
- **Novos métodos**:
  - `record_handoff_to_human(reason)`
  - `record_media_detected(media_type)`
  - `record_confirmation_sent()`
  - `record_confirmation_response(confirmed)`
  - `record_feedback_received()`

### 6. Preferências do Prestador
- **Schemas**: `backend/app/schemas/user.py`
  - `NotificationPreferences`: Canais de alerta, horários silenciosos, limiar de handoff, trigger_on_media, include_snippet
  - `QuietHours`: Horário de início/fim
  - `NotificationPreferencesUpdate`: Schema de atualização
- **Modelo**: `backend/app/models/user.py`
  - Nova coluna `notification_preferences` (JSONB)
- **Endpoints**: `backend/app/api/users.py`
  - `PATCH /api/users/preferences/notifications`: Atualizar preferências
  - `GET /api/users/preferences/notifications`: Obter preferências

### 7. Perfil do Negócio
- **Schemas**: `backend/app/schemas/user.py`
  - `BusinessProfileMetadata`: Descrição, regiões, estacionamento, acompanhante, formas de pagamento, política de cancelamento, local de trabalho, idiomas
  - `BusinessProfileUpdate`: Schema de atualização
- **Modelo**: `backend/app/models/user.py`
  - Nova coluna `profile_metadata` (JSONB)
- **Endpoints**: `backend/app/api/users.py`
  - `PATCH /api/users/profile/business`: Atualizar perfil
  - `GET /api/users/profile/business`: Obter perfil

### 8. Metadados de Serviço
- **Schemas**: `backend/app/schemas/service.py`
  - `ServiceMetadata`: Categoria, requisitos, pós-cuidados, local, materiais, contraindicações, preparação
  - `ServiceMetadataUpdate`: Schema de atualização
- **Modelo**: `backend/app/models/service.py`
  - Nova coluna `metadata` (JSONB)
- **Endpoints**: `backend/app/api/services.py`
  - `PATCH /api/services/{id}/metadata`: Atualizar metadados
  - `GET /api/services/{id}/metadata`: Obter metadados

### 9. Configurações de Notificação por Serviço
- **Schemas**: `backend/app/schemas/service.py`
  - `NotificationSettings`: Lembretes, confirmação, feedback
  - `NotificationConfig`: Offset em horas
  - `ServiceNotificationSettingsUpdate`: Schema de atualização
- **Modelo**: `backend/app/models/service.py`
  - Nova coluna `notification_settings` (JSONB)
- **Endpoints**: `backend/app/api/services.py`
  - `PATCH /api/services/{id}/notifications`: Atualizar configurações
  - `GET /api/services/{id}/notifications`: Obter configurações

### 10. Serviço de Notificações Aprimorado
- **Arquivo**: `backend/app/services/notification_service.py`
- **Novo método**:
  - `send_handoff_alert()`: Envia alerta ao prestador
    - Suporta email e WhatsApp
    - Inclui snippet da conversa
    - Mapeia razões para mensagens amigáveis
    - Template HTML para email
    - Respeita canais configurados

## 📊 Fluxos Implementados

### Fluxo de Detecção de Mídia
1. Cliente envia áudio/imagem/vídeo/documento
2. Webhook detecta tipo de mídia
3. Busca preferências do prestador
4. Se `trigger_on_media = true`:
   - Obtém snippet da conversa
   - Envia alerta ao prestador (email/WhatsApp)
   - Registra métrica de mídia detectada
5. Responde ao cliente com template `media_handoff`

### Fluxo de Handoff por Baixa Confiança
1. Bot detecta confiança < 0.3
2. Incrementa contador de falhas
3. Se 3 falhas consecutivas:
   - Marca handoff no estado
   - Registra métrica
   - Busca dados do prestador
   - Envia alerta
   - Responde com template `handoff`

### Fluxo de Handoff por Solicitação
1. Cliente pede "falar com humano"
2. Bot detecta intenção `Intent.HUMAN`
3. Marca handoff no estado
4. Registra métrica
5. Busca dados do prestador
6. Envia alerta
7. Responde com template `handoff`

## 🔧 Configurações

### Preferências Padrão (Prestador)
```json
{
  "alert_channels": ["email"],
  "handoff_threshold": 0.5,
  "trigger_on_media": true,
  "include_conversation_snippet": true,
  "quiet_hours": {
    "start": "22:00",
    "end": "07:00"
  }
}
```

### Exemplo de Metadados de Serviço
```json
{
  "category": "estetica",
  "requirements": ["chegar 10 min antes", "evitar maquiagem"],
  "post_care": ["hidratar a pele", "evitar sol por 24h"],
  "location_type": "studio",
  "materials_included": true,
  "contraindications": ["gravidez", "alergias"]
}
```

### Exemplo de Configuração de Notificações
```json
{
  "reminders": [
    {"offset_hours": 24},
    {"offset_hours": 2}
  ],
  "confirmation": {
    "offset_hours": 24
  },
  "feedback": {
    "delay_hours": 24,
    "questions": ["NPS", "comentario_livre"]
  }
}
```

## 🚀 Próximos Passos

### Pendente de Implementação
1. **Sistema de Notificações (Scheduler/Worker)**
   - Implementar scheduler para lembretes automáticos
   - Worker para processar confirmações
   - Parser de respostas de confirmação (1/2/3, sim/não)
   - Worker para feedbacks pós-atendimento
   - Integração com `message_worker.py` existente

2. **Integração Completa do Bot com Metadados**
   - Usar metadados do serviço nas respostas
   - Personalizar perguntas por categoria
   - Incluir requisitos e pós-cuidados nas confirmações

3. **Migração de Banco de Dados**
   - Criar migration para adicionar colunas JSONB:
     - `users.notification_preferences`
     - `users.profile_metadata`
     - `services.metadata`
     - `services.notification_settings`

## 📝 Testes Recomendados

### Teste de Detecção de Mídia
1. Enviar áudio pelo WhatsApp
2. Verificar se alerta foi enviado ao prestador
3. Verificar resposta ao cliente
4. Verificar métricas

### Teste de Handoff
1. Enviar "quero falar com alguém"
2. Verificar handoff marcado no estado
3. Verificar alerta enviado
4. Verificar métricas

### Teste de Preferências
1. Atualizar preferências via API
2. Enviar mídia
3. Verificar se respeitou configurações
4. Testar horários silenciosos

## 📂 Arquivos Modificados

- ✅ `backend/app/services/bot/templates.py`
- ✅ `backend/app/services/bot/conversation_state.py`
- ✅ `backend/app/services/bot/bot_metrics.py`
- ✅ `backend/app/services/bot/bot_service.py`
- ✅ `backend/app/services/notification_service.py`
- ✅ `backend/app/api/webhooks.py`
- ✅ `backend/app/api/users.py`
- ✅ `backend/app/api/services.py`
- ✅ `backend/app/schemas/user.py`
- ✅ `backend/app/schemas/service.py`
- ✅ `backend/app/models/user.py`
- ✅ `backend/app/models/service.py`

## 🎯 Resumo de Endpoints Novos

### Usuários
- `PATCH /api/users/preferences/notifications`
- `GET /api/users/preferences/notifications`
- `PATCH /api/users/profile/business`
- `GET /api/users/profile/business`

### Serviços
- `PATCH /api/services/{id}/metadata`
- `GET /api/services/{id}/metadata`
- `PATCH /api/services/{id}/notifications`
- `GET /api/services/{id}/notifications`

## 💡 Observações Importantes

1. **Migrations**: Necessário criar migrações Alembic para as novas colunas JSONB antes de usar em produção.

2. **Redis**: Todas as features de estado de conversa dependem de Redis disponível.

3. **SMTP/Twilio**: Alertas por email/WhatsApp requerem configurações apropriadas no `config.py`.

4. **Validações**: Schemas Pydantic validam tipos de dados e formatos.

5. **Performance**: JSONB no PostgreSQL permite queries eficientes em metadados.

6. **Extensibilidade**: Estrutura permite adicionar novos campos aos metadados sem alterar schema de BD.


