"""
Endpoints de webhooks (n8n)
"""

from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/appointment")
async def appointment_webhook(request: Request):
    """Webhook para eventos de agendamento"""
    # TODO: Implementar webhook de agendamento
    data = await request.json()
    logger.info(f"Webhook de agendamento recebido: {data}")
    return {"message": "Webhook de agendamento processado"}


@router.post("/sync")
async def sync_webhook(request: Request):
    """Webhook para sincronização"""
    # TODO: Implementar webhook de sincronização
    data = await request.json()
    logger.info(f"Webhook de sincronização recebido: {data}")
    return {"message": "Webhook de sincronização processado"}


@router.post("/message")
async def message_webhook(request: Request):
    """Webhook para mensagens"""
    # TODO: Implementar webhook de mensagem
    data = await request.json()
    logger.info(f"Webhook de mensagem recebido: {data}")
    return {"message": "Webhook de mensagem processado"}
