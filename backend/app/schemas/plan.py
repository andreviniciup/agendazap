"""
Schemas Pydantic para planos e uso
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.utils.enums import PlanType


class PlanLimits(BaseModel):
    """Schema para limites de um plano"""
    appointments_per_month: int
    whatsapp_messages_per_month: int
    services_limit: int
    custom_domain: bool
    analytics: bool
    price: float


class UsageStats(BaseModel):
    """Schema para estatísticas de uso"""
    appointments_this_month: int = 0
    whatsapp_messages_this_month: int = 0
    services_count: int = 0


class UsagePercentages(BaseModel):
    """Schema para porcentagens de uso"""
    appointments_per_month: float = 0.0
    whatsapp_messages_per_month: float = 0.0
    services_limit: float = 0.0


class PlanAlerts(BaseModel):
    """Schema para alertas de uso"""
    appointments: bool = False
    messages: bool = False
    services: bool = False


class PlanInfo(BaseModel):
    """Schema para informações completas do plano"""
    plan_type: str
    limits: PlanLimits
    usage: UsageStats
    usage_percentages: UsagePercentages
    alerts: PlanAlerts


class PlanUpgradeRequest(BaseModel):
    """Schema para requisição de upgrade de plano"""
    target_plan: PlanType
    
    class Config:
        use_enum_values = True


class PlanUpgradeResponse(BaseModel):
    """Schema para resposta de upgrade de plano"""
    message: str
    old_plan: str
    new_plan: str
    new_limits: PlanLimits
    upgrade_date: datetime


class UsageAlert(BaseModel):
    """Schema para alerta de uso"""
    limit_type: str
    current_usage: int
    limit_value: int
    percentage: float
    message: str
    upgrade_recommended: bool


class PlanComparison(BaseModel):
    """Schema para comparação de planos"""
    current_plan: PlanType
    available_plans: Dict[str, PlanLimits]
    recommended_plan: Optional[PlanType] = None
    upgrade_benefits: Dict[str, Any] = {}


class BillingInfo(BaseModel):
    """Schema para informações de cobrança"""
    plan_type: PlanType
    monthly_price: float
    next_billing_date: datetime
    payment_method: Optional[str] = None
    billing_history: list = []


class PlanFeature(BaseModel):
    """Schema para feature de um plano"""
    name: str
    description: str
    included: bool
    limit: Optional[int] = None
    unlimited: bool = False


class PlanDetails(BaseModel):
    """Schema para detalhes completos de um plano"""
    plan_type: PlanType
    name: str
    description: str
    price: float
    features: list[PlanFeature]
    limits: PlanLimits
    popular: bool = False
    recommended: bool = False

