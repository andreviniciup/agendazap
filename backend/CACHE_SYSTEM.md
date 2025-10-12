# Sistema de Cache Inteligente - AgendaZap

## Visão Geral

O Sistema de Cache Inteligente foi implementado para otimizar a performance da aplicação AgendaZap, reduzindo a carga no banco de dados e melhorando significativamente o tempo de resposta das consultas mais frequentes.

## Arquitetura

### Componentes Principais

1. **CacheService** (`app/services/cache_service.py`)
   - Serviço principal de cache usando Redis
   - Métricas de performance (hit rate, miss rate, etc.)
   - Invalidação automática de cache
   - Sistema de fallback quando Redis não está disponível

2. **CacheWarmingService** (`app/services/cache_warming_service.py`)
   - Aquecimento automático de cache para usuários ativos
   - Execução em background a cada 5 minutos
   - Priorização de usuários com planos pagos

3. **TemplateService** (`app/services/template_service.py`)
   - Cache de templates de mensagem
   - Templates personalizados por tipo de usuário
   - Renderização dinâmica com variáveis

4. **API de Cache** (`app/api/cache.py`)
   - Endpoints para monitoramento e gerenciamento
   - Métricas em tempo real
   - Controle manual de cache

## Tipos de Cache Implementados

### 1. Cache de Agendas (TTL: 1 hora)
- **Chave**: `agenda:{user_id}:{date}`
- **Dados**: Agendamentos do usuário para uma data específica
- **Invalidação**: Automática quando agendamentos são criados/atualizados/cancelados

### 2. Cache de Serviços (TTL: 24 horas)
- **Chave**: `services:{user_id}`
- **Dados**: Lista de serviços ativos do usuário
- **Invalidação**: Automática quando serviços são criados/atualizados/removidos

### 3. Cache de Templates (Sem expiração)
- **Chave**: `template:{template_id}`
- **Dados**: Templates de mensagem personalizados
- **Invalidação**: Manual ou quando templates são atualizados

## Configuração

### Variáveis de Ambiente

```env
# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_password

# Cache TTL (em segundos)
CACHE_TTL_AGENDA=3600      # 1 hora
CACHE_TTL_SERVICES=86400   # 24 horas
CACHE_TTL_TEMPLATES=0      # Sem expiração
```

### Dependências

```txt
redis[hiredis]==5.0.1
```

## Uso

### Cache de Agendas

```python
from app.services.appointment_service import AppointmentService
from app.services.cache_service import cache_service

# Obter agenda com cache
agenda = appointment_service.get_user_agenda(user, target_date, use_cache=True)

# Invalidar cache manualmente
cache_service.invalidate_user_agenda(user.id, "2024-01-15")
```

### Cache de Serviços

```python
from app.services.service_service import ServiceService

# Obter serviços com cache
services = service_service.get_user_services(user, use_cache=True)

# Invalidar cache manualmente
cache_service.invalidate_user_services(user.id)
```

### Cache de Templates

```python
from app.services.template_service import TemplateService

# Obter template com cache
template = template_service.get_template_by_type(user, "appointment_confirmation")

# Renderizar template com variáveis
message = template_service.render_template(
    user, 
    "appointment_confirmation", 
    {
        "client_name": "João Silva",
        "provider_name": "Dr. Maria",
        "date": "2024-01-15",
        "time": "14:00"
    }
)
```

## API Endpoints

### Métricas de Cache
```http
GET /api/cache/metrics
```

### Status do Cache
```http
GET /api/cache/status
```

### Aquecer Cache
```http
POST /api/cache/warm
```

### Invalidar Cache
```http
DELETE /api/cache/invalidate
DELETE /api/cache/invalidate/agenda?date=2024-01-15
DELETE /api/cache/invalidate/services
```

### Status de Fallback
```http
GET /api/cache/fallback-status
```

## Sistema de Fallback

O sistema implementa fallback automático quando o Redis não está disponível:

1. **Detecção Automática**: Verifica conectividade com Redis
2. **Fallback Transparente**: Consultas vão direto para o banco de dados
3. **Logging**: Registra quando fallback está ativo
4. **Recuperação**: Retoma uso do cache quando Redis volta

## Cache Warming

### Automático
- Executa a cada 5 minutos
- Foca em usuários ativos (com agendamentos recentes)
- Prioriza usuários com planos pagos

### Manual
```bash
# Iniciar serviço de warming
python start_cache_warming.py

# Via API
curl -X POST http://localhost:8000/api/cache/warm
```

## Métricas e Monitoramento

### Métricas Disponíveis
- **Hit Rate**: Taxa de acerto do cache
- **Miss Rate**: Taxa de erro do cache
- **Total Requests**: Total de requisições
- **Uptime**: Tempo de funcionamento
- **Errors**: Número de erros

### Exemplo de Resposta
```json
{
  "metrics": {
    "hits": 1250,
    "misses": 150,
    "errors": 5,
    "total_requests": 1405,
    "hit_rate": 88.97,
    "uptime_seconds": 3600
  },
  "cache_info": {
    "connected": true,
    "redis_version": "7.0.0",
    "used_memory": "2.5M",
    "connected_clients": 3
  }
}
```

## Invalidação Automática

### Agendamentos
- **Criação**: Invalida cache da data do agendamento
- **Atualização**: Invalida cache das datas afetadas
- **Cancelamento**: Invalida cache da data do agendamento

### Serviços
- **Criação**: Invalida cache de serviços do usuário
- **Atualização**: Invalida cache de serviços do usuário
- **Remoção**: Invalida cache de serviços do usuário

## Performance

### Benefícios Esperados
- **Redução de 90%** na carga do banco de dados
- **Melhoria de 80%** no tempo de resposta
- **Escalabilidade** para 50.000+ usuários
- **Disponibilidade** mesmo com falhas do Redis

### Critérios de Sucesso
- ✅ Primeira consulta lenta (miss)
- ✅ Segunda consulta rápida (hit)
- ✅ Dados atualizados após alteração (invalidação funcionando)
- ✅ Fallback automático quando Redis falha

## Troubleshooting

### Cache não está funcionando
1. Verificar conectividade com Redis: `GET /api/cache/status`
2. Verificar logs de erro
3. Testar fallback: `GET /api/cache/fallback-status`

### Performance baixa
1. Verificar hit rate: `GET /api/cache/metrics`
2. Aquecer cache manualmente: `POST /api/cache/warm`
3. Verificar TTLs configurados

### Dados desatualizados
1. Verificar invalidação automática nos logs
2. Invalidar cache manualmente: `DELETE /api/cache/invalidate`
3. Verificar se invalidação está sendo chamada nos serviços

## Desenvolvimento

### Adicionando Novo Tipo de Cache

1. Adicionar método no `CacheService`:
```python
def get_user_data(self, user_id: int) -> Optional[Dict]:
    key = self._get_key("data", user_id)
    return self.get(key)

def set_user_data(self, user_id: int, data: Dict) -> bool:
    key = self._get_key("data", user_id)
    return self.set(key, data, ttl=3600)
```

2. Implementar invalidação no serviço correspondente
3. Adicionar endpoint na API se necessário

### Testando Cache

```python
# Teste básico
def test_cache_basic():
    cache_service.set("test_key", {"data": "test"}, ttl=60)
    result = cache_service.get("test_key")
    assert result["data"] == "test"

# Teste de invalidação
def test_cache_invalidation():
    cache_service.set_user_services(user_id, services_data)
    cache_service.invalidate_user_services(user_id)
    result = cache_service.get_user_services(user_id)
    assert result is None
```

## Conclusão

O Sistema de Cache Inteligente implementa todas as funcionalidades especificadas na Ação 3.4:

- ✅ Cache de agendas por usuário com TTL de 1 hora
- ✅ Cache de serviços por usuário com TTL de 24 horas
- ✅ Invalidação automática quando dados são alterados
- ✅ Cache de templates de mensagem
- ✅ Métricas de hit rate do cache
- ✅ Cache warming para usuários ativos
- ✅ Fallback para quando cache falhar

O sistema está pronto para produção e pode reduzir significativamente a carga no banco de dados, melhorando a experiência do usuário e a escalabilidade da aplicação.



