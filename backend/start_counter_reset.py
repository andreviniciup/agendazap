#!/usr/bin/env python3
"""
Script para iniciar o serviço de reset automático de contadores
"""

import asyncio
import logging
import signal
import sys
from app.dependencies import get_redis
from app.services.counter_reset_service import counter_reset_service

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Função principal"""
    try:
        logger.info("🚀 Iniciando serviço de reset automático de contadores...")
        
        # Obter cliente Redis
        redis_client = await get_redis()
        if not redis_client:
            logger.error("❌ Redis não disponível, não é possível iniciar o serviço")
            sys.exit(1)
        
        # Configurar serviço
        counter_reset_service.redis = redis_client
        
        # Iniciar agendador
        await counter_reset_service.start_monthly_reset_scheduler()
        
        logger.info("✅ Serviço de reset automático iniciado com sucesso!")
        
        # Manter o script rodando
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Recebido sinal de interrupção, parando serviço...")
        finally:
            await counter_reset_service.stop_monthly_reset_scheduler()
            logger.info("✅ Serviço parado com sucesso!")
            
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar serviço: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handler para sinais do sistema"""
    logger.info(f"🛑 Recebido sinal {signum}, parando serviço...")
    sys.exit(0)


if __name__ == "__main__":
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Executar
    asyncio.run(main())
