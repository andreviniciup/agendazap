import os
os.environ["ENVIRONMENT"] = "development"

import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from uuid import uuid4

from app.main import app
from app.dependencies import get_current_active_user, get_plan_service
from app.database import get_db
from app.utils.enums import PlanType, TemplateType


@pytest.fixture()
def fake_user():
    return SimpleNamespace(
        id=uuid4(),
        email="user@test.com",
        name="User Test",
        plan_type=PlanType.FREE,
        template_type=TemplateType.CONSULTATION,
        is_active_bool=True,
        notification_preferences=None,
        profile_metadata=None,
    )


@pytest.fixture()
def client(fake_user):
    # Sobrescrever dependências para evitar autenticação real e DB
    async def override_get_current_active_user():
        return fake_user

    class FakeDB:
        def commit(self):
            return None

        def refresh(self, _):
            return None

        def query(self, *_args, **_kwargs):
            class _Q:
                def filter(self, *_a, **_k):
                    return self

                def first(self):
                    return None

            return _Q()

    async def override_get_db():
        yield FakeDB()

    app.dependency_overrides = {
        # Auth
        get_current_active_user: override_get_current_active_user,
        # DB
        get_db: override_get_db,
    }

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}


def test_get_profile_returns_current_user(client, fake_user):
    resp = client.get("/api/users/profile", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == fake_user.email
    assert data["plan_type"] == fake_user.plan_type.value


def test_get_notification_preferences_defaults_merge(client, fake_user):
    # Sem preferences setadas, deve retornar defaults mesclados
    resp = client.get("/api/users/preferences/notifications", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    # Defaults esperados pelo handler
    assert data["alert_channels"] == ["email"]
    assert isinstance(data["handoff_threshold"], (float, int))
    assert data["trigger_on_media"] is True
    assert data["include_conversation_snippet"] is True


def test_update_notification_preferences_updates_fields(client, fake_user):
    body = {
        "alert_channels": ["email", "whatsapp"],
        "handoff_threshold": 0.7,
        "quiet_hours": {"start": "22:00", "end": "07:00"},
    }
    resp = client.patch(
        "/api/users/preferences/notifications",
        json=body,
        headers={"Authorization": "Bearer x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    prefs = data["preferences"]
    assert prefs["alert_channels"] == ["email", "whatsapp"]
    assert prefs["handoff_threshold"] == 0.7
    assert prefs["quiet_hours"] == {"start": "22:00", "end": "07:00"}


def test_get_business_profile_empty_object(client):
    resp = client.get("/api/users/profile/business", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    assert resp.json() == {}


def test_update_business_profile_sets_metadata(client):
    body = {"business_name": "Studio X", "address": "Rua A"}
    resp = client.patch(
        "/api/users/profile/business",
        json=body,
        headers={"Authorization": "Bearer x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["metadata"]["business_name"] == "Studio X"
    assert data["metadata"]["address"] == "Rua A"


def test_get_plan_calls_service_and_returns_info(client, monkeypatch, fake_user):
    class FakePlanService:
        async def get_plan_info(self, _user):
            return {"plan": fake_user.plan_type.value, "limits": {}}

    async def override_get_plan_service(*_a, **_k):  # noqa: ARG001
        return FakePlanService()

    app.dependency_overrides[get_plan_service] = override_get_plan_service

    resp = client.get("/api/users/plan", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    assert resp.json()["plan"] == fake_user.plan_type.value


def test_upgrade_plan_allows_only_upgrade_direction(client, fake_user):
    # Simula serviço de planos que permite upgrade apenas para cima
    class FakePlanService:
        def can_upgrade_plan(self, current, target):
            order = [PlanType.FREE, PlanType.STARTER, PlanType.PRO, PlanType.ENTERPRISE]
            return order.index(target) > order.index(current)

        def get_plan_limits(self, _p):
            return {"services_limit": 5}

    async def override_get_plan_service(*_a, **_k):  # noqa: ARG001
        return FakePlanService()

    app.dependency_overrides[get_plan_service] = override_get_plan_service

    # Tenta upgrade válido
    resp_ok = client.post(
        "/api/users/upgrade",
        json={"target_plan": PlanType.STARTER.value},
        headers={"Authorization": "Bearer x"},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["new_plan"] == PlanType.STARTER.value

    # Tenta downgrade (deve falhar)
    resp_bad = client.post(
        "/api/users/upgrade",
        json={"target_plan": PlanType.FREE.value},
        headers={"Authorization": "Bearer x"},
    )
    assert resp_bad.status_code == 400

