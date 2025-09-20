#!/usr/bin/env python3
"""
Script para iniciar workers de mensagens
"""

import asyncio
import sys
import signal
import logging
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Função principal para iniciar workers"""
    try:
        from app.workers import worker_manager
        
        logger.info("🚀 Iniciando workers de mensagens...")
        
        # Iniciar workers
        await worker_manager.start_workers()
        
        # Manter o script rodando
        logger.info("✅ Workers iniciados com sucesso! Pressione Ctrl+C para parar.")
        
        # Aguardar indefinidamente
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Parando workers...")
        await worker_manager.stop_workers()
        logger.info("✅ Workers parados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar workers: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handler para sinais do sistema"""
    logger.info(f"Recebido sinal {signum}, parando workers...")
    sys.exit(0)


if __name__ == "__main__":
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Executar
    asyncio.run(main())

