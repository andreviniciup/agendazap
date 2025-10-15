"""
Endpoints de usuários
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.database import get_db
from app.dependencies import get_current_active_user, get_plan_limits, get_plan_service
from app.schemas.user import (
    UserResponse, UserUpdate, UserPlanInfo,
    NotificationPreferencesUpdate, BusinessProfileUpdate,
    NotificationPreferences, BusinessProfileMetadata
)
from app.schemas.plan import PlanInfo, PlanUpgradeRequest, PlanUpgradeResponse, PlanComparison
from app.models.user import User
from app.utils.enums import PlanType
from app.services.plan_service import PlanService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Obter perfil do usuário"""
    try:
        logger.info(f"Perfil solicitado para usuário: {current_user.email}")
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        logger.error(f"Erro ao obter perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Atualizar perfil do usuário"""
    try:
        # Verificar se email já existe (se estiver sendo alterado)
        if user_update.email and user_update.email != current_user.email:
            existing_user = db.query(User).filter(
                User.email == user_update.email,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já está em uso"
                )
        
        # Atualizar campos fornecidos
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Perfil atualizado para usuário: {current_user.email}")
        return UserResponse.from_orm(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.patch("/preferences/notifications")
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Atualizar preferências de notificação do prestador"""
    try:
        # Obter preferências atuais ou criar novo dict
        current_prefs = current_user.notification_preferences or {}
        
        # Atualizar apenas os campos fornecidos
        update_data = preferences.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "quiet_hours" and value:
                current_prefs[field] = value.dict()
            elif value is not None:
                current_prefs[field] = value
        
        # Salvar
        current_user.notification_preferences = current_prefs
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Preferências de notificação atualizadas para usuário: {current_user.email}")
        return {
            "success": True,
            "message": "Preferências atualizadas com sucesso",
            "preferences": current_prefs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar preferências: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/preferences/notifications")
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """Obter preferências de notificação do prestador"""
    try:
        prefs = current_user.notification_preferences or {}
        
        # Aplicar defaults
        default_prefs = {
            "alert_channels": ["email"],
            "handoff_threshold": 0.5,
            "trigger_on_media": True,
            "include_conversation_snippet": True
        }
        
        return {**default_prefs, **prefs}
        
    except Exception as e:
        logger.error(f"Erro ao obter preferências: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.patch("/profile/business")
async def update_business_profile(
    profile: BusinessProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Atualizar perfil do negócio"""
    try:
        # Obter metadados atuais ou criar novo dict
        current_metadata = current_user.profile_metadata or {}
        
        # Atualizar apenas os campos fornecidos
        update_data = profile.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                current_metadata[field] = value
        
        # Salvar
        current_user.profile_metadata = current_metadata
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Perfil do negócio atualizado para usuário: {current_user.email}")
        return {
            "success": True,
            "message": "Perfil do negócio atualizado com sucesso",
            "metadata": current_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil do negócio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/profile/business")
async def get_business_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Obter perfil do negócio"""
    try:
        metadata = current_user.profile_metadata or {}
        return metadata
        
    except Exception as e:
        logger.error(f"Erro ao obter perfil do negócio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/plan", response_model=PlanInfo)
async def get_plan(
    current_user: User = Depends(get_current_active_user),
    plan_service: PlanService = Depends(get_plan_service)
):
    """Obter informações completas do plano"""
    try:
        plan_info = await plan_service.get_plan_info(current_user)
        
        logger.info(f"Informações de plano solicitadas para usuário: {current_user.email}")
        return plan_info
        
    except Exception as e:
        logger.error(f"Erro ao obter informações do plano: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.post("/upgrade", response_model=PlanUpgradeResponse)
async def upgrade_plan(
    upgrade_request: PlanUpgradeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    plan_service: PlanService = Depends(get_plan_service)
):
    """Upgrade do plano"""
    try:
        new_plan = upgrade_request.target_plan
        
        # Verificar se é possível fazer upgrade
        if not plan_service.can_upgrade_plan(current_user.plan_type, new_plan):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas upgrades são permitidos"
            )
        
        # Obter limites do novo plano
        new_limits = plan_service.get_plan_limits(new_plan)
        
        # Atualizar plano
        old_plan = current_user.plan_type
        current_user.plan_type = new_plan
        db.commit()
        
        logger.info(f"Plano atualizado de {old_plan.value} para {new_plan.value} para usuário: {current_user.email}")
        
        return PlanUpgradeResponse(
            message=f"Plano atualizado para {new_plan.value} com sucesso",
            old_plan=old_plan.value,
            new_plan=new_plan.value,
            new_limits=new_limits,
            upgrade_date=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer upgrade do plano: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/usage", response_model=dict)
async def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    plan_service: PlanService = Depends(get_plan_service)
):
    """Obter estatísticas de uso do usuário"""
    try:
        usage = await plan_service.get_user_usage(str(current_user.id))
        plan_info = await plan_service.get_plan_info(current_user)
        
        return {
            "usage": usage,
            "plan_info": plan_info,
            "alerts": plan_info["alerts"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de uso: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.get("/plans/compare", response_model=PlanComparison)
async def compare_plans(
    current_user: User = Depends(get_current_active_user),
    plan_service: PlanService = Depends(get_plan_service)
):
    """Comparar planos disponíveis"""
    try:
        # Obter informações de todos os planos
        all_plans = {}
        for plan_type in PlanType:
            all_plans[plan_type.value] = plan_service.get_plan_limits(plan_type)
        
        # Determinar plano recomendado baseado no uso atual
        usage = await plan_service.get_user_usage(str(current_user.id))
        recommended_plan = None
        
        # Lógica simples de recomendação
        if usage["appointments_this_month"] > 10 or usage["whatsapp_messages_this_month"] > 50:
            recommended_plan = PlanType.STARTER
        elif usage["appointments_this_month"] > 50 or usage["whatsapp_messages_this_month"] > 200:
            recommended_plan = PlanType.PRO
        elif usage["appointments_this_month"] > 100 or usage["whatsapp_messages_this_month"] > 500:
            recommended_plan = PlanType.ENTERPRISE
        
        return PlanComparison(
            current_plan=current_user.plan_type,
            available_plans=all_plans,
            recommended_plan=recommended_plan,
            upgrade_benefits={
                "more_appointments": "Agendamentos ilimitados",
                "more_messages": "Mais mensagens WhatsApp",
                "more_services": "Mais serviços disponíveis",
                "analytics": "Relatórios e analytics",
                "custom_domain": "Domínio personalizado"
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao comparar planos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deletar conta do usuário"""
    try:
        # Marcar usuário como inativo em vez de deletar (soft delete)
        current_user.is_active_bool = False
        db.commit()
        
        logger.info(f"Conta desativada para usuário: {current_user.email}")
        
        return {"message": "Conta desativada com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao desativar conta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )
