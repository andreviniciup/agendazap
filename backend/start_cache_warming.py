#!/usr/bin/env python3
"""
Script para iniciar o serviço de cache warming
"""

import asyncio
import logging
import signal
import sys
from app.services.cache_warming_service import start_cache_warming, stop_cache_warming

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handler para sinais de interrupção"""
    logger.info("🛑 Recebido sinal de interrupção, parando serviço de cache warming...")
    stop_cache_warming()
    sys.exit(0)


async def main():
    """Função principal"""
    # Registrar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Iniciando serviço de cache warming...")
    
    try:
        await start_cache_warming()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro no serviço de cache warming: {e}")
    finally:
        stop_cache_warming()
        logger.info("✅ Serviço de cache warming finalizado")


if __name__ == "__main__":
    asyncio.run(main())




