#!/usr/bin/env python3
import os, sys, random
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "seed_secret_key_long_enough_1234567890")
_here = Path(__file__).resolve().parent
_db_path = (_here / "seed.db").as_posix()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")
sys.path.insert(0, str(Path(__file__).parent))

from app.services.bot.data_collector import DataCollector, LabelQuality

c = DataCollector()

# Dados variados para cada intenção
dados = {
    'price': [f'{p} {s}' for p in ['quanto custa', 'qual o valor', 'quanto é', 'preço de', 'valor do', 'custa quanto', 'quanto sai', 'quanto fica', 'me fala o preço', 'qual o preço'] for s in ['', 'isso', 'consulta', 'procedimento', 'sessão', 'tratamento', 'corte', 'limpeza', 'avaliação', 'exame']] * 3,
    
    'availability': [f'{p} {d}' for p in ['tem vaga', 'tem horário', 'tem disponível', 'quando tem', 'tem hoje', 'tem amanhã', 'que horas tem', 'qual horário disponível', 'horário livre', 'vaga disponível'] for d in ['', 'hoje', 'amanhã', 'essa semana', 'próxima semana', 'de manhã', 'de tarde', 'de noite']] * 2,
    
    'cancel': [f'{p} {r}' for p in ['quero cancelar', 'preciso cancelar', 'cancelar', 'desmarcar', 'não vou poder', 'não vou conseguir', 'tenho que cancelar', 'posso cancelar', 'cancela pra mim', 'desmarca pra mim'] for r in ['', 'meu horário', 'minha consulta', 'meu agendamento', 'hoje', 'amanhã', 'essa semana']] * 2,
    
    'reschedule': [f'{p} {r}' for p in ['quero remarcar', 'preciso remarcar', 'remarcar', 'mudar horário', 'trocar dia', 'pode remarcar', 'consigo remarcar', 'remarcar pra outro dia', 'mudar data', 'trocar horário'] for r in ['', 'meu horário', 'minha consulta', 'para outro dia', 'para semana que vem', 'para amanhã']] * 2,
    
    'services': [f'{p} {s}' for p in ['que serviços', 'quais serviços', 'o que fazem', 'que procedimentos', 'quais procedimentos', 'fazem o que', 'serviços disponíveis', 'me fala os serviços', 'lista de serviços', 'que tratamentos'] for s in ['', 'vocês têm', 'vocês fazem', 'tem aí', 'oferecem', 'disponíveis']] * 2,
    
    'address': [f'{p} {e}' for p in ['onde fica', 'qual o endereço', 'endereço', 'como chego', 'localização', 'fica onde', 'onde vocês ficam', 'onde é', 'qual a localização', 'me manda o endereço'] for e in ['', 'aí', 'da clínica', 'do consultório', 'do estabelecimento']] * 2,
    
    'payment': [f'{p} {m}' for p in ['aceita cartão', 'aceita pix', 'aceita dinheiro', 'formas de pagamento', 'como pagar', 'qual pagamento', 'pode pagar com', 'pagamento', 'aceita débito', 'aceita crédito'] for m in ['', 'aí', 'cartão', 'pix', 'dinheiro', 'débito', 'crédito']] * 2,
    
    'business_hours': [f'{p} {h}' for p in ['horário de funcionamento', 'que horas abre', 'que horas fecha', 'funciona quando', 'abre que horas', 'fecha que horas', 'horário', 'funciona que dias', 'aberto quando', 'horário de atendimento'] for h in ['', 'hoje', 'amanhã', 'no sábado', 'no domingo', 'na semana']] * 2,
    
    'about': [f'{p} {i}' for p in ['como funciona', 'me explica', 'quero saber', 'informações', 'funciona como', 'o que é', 'pode explicar', 'não entendi', 'como é', 'me conta'] for i in ['', 'isso', 'o processo', 'o procedimento', 'o tratamento', 'como funciona']] * 2,
    
    'human': [f'{p} {a}' for p in ['falar com atendente', 'quero falar com pessoa', 'atendimento humano', 'preciso falar com alguém', 'tem alguém', 'quero falar com alguém', 'atendente', 'pessoa real', 'falar com gente', 'quero ajuda humana'] for a in ['', 'por favor', 'agora', 'urgente']] * 2
}

print("🚀 Gerando dados em lote...")
total = 0
for intent, textos in dados.items():
    for texto in textos:
        if texto.strip():
            c.log_interaction(
                text=texto.strip(),
                intent=intent,
                confidence=random.uniform(0.75, 0.95),
                label_quality=LabelQuality.CONFIDENT.value,
                user_whatsapp=f'5511999{random.randint(1000,9999)}',
                context={'source': 'batch_gen'}
            )
            total += 1
    print(f"  ✅ {intent}: {len(textos)} exemplos")

stats = c.get_stats()
print(f"\n📊 TOTAL GERADO: {total} exemplos")
print(f"📊 TOTAL NO BANCO: {stats['total_examples']}")
print(f"📊 PRONTOS PARA TREINO: {stats['ready_to_train']}")

