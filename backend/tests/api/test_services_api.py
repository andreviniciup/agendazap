import os
os.environ["ENVIRONMENT"] = "development"

import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from datetime import datetime
from uuid import uuid4

from app.main import app
from app.dependencies import get_current_active_user, get_service_service
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
    )


@pytest.fixture()
def client(fake_user):
    async def override_get_current_active_user():
        return fake_user

    class FakeService:
        def __init__(self):
            self._store = {}

        def get_services(self, _user, _search, page, per_page):
            items = list(self._store.values())
            start = (page - 1) * per_page
            end = start + per_page
            return {
                "services": items[start:end],
                "total": len(items),
                "page": page,
                "per_page": per_page,
                "total_pages": 1,
            }

        async def create_service(self, data, user):  # noqa: ARG002
            obj = SimpleNamespace(
                id=uuid4(),
                user_id=user.id,
                category_id=None,
                name=data.name,
                description=data.description,
                duration=data.duration,
                price=data.price,
                images=data.images,
                credentials=data.credentials,
                promotions=data.promotions,
                custom_fields=data.custom_fields,
                is_active=True,
                is_featured=False,
                sort_order=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                category=None,
                metadata={},
                notification_settings={},
            )
            self._store[obj.id] = obj
            return obj

        def get_service(self, service_id, _user):
            return self._store[service_id]

        def update_service(self, service_id, data, _user):
            obj = self._store[service_id]
            for k, v in data.dict(exclude_unset=True).items():
                setattr(obj, k, v)
            return obj

        def delete_service(self, service_id, _user):
            self._store.pop(service_id, None)

        def get_service_stats(self, _user):
            return {"total": len(self._store), "active": len(self._store)}

        def get_template_validation_rules(self, _template_type):
            return {"requires_price": True, "requires_images": False, "requires_credentials": False, "max_images": 5}

    fake_service = FakeService()

    async def override_get_service_service(*_a, **_k):  # noqa: ARG001
        return fake_service

    app.dependency_overrides = {
        get_current_active_user: override_get_current_active_user,
        get_service_service: override_get_service_service,
    }

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}


def test_create_and_get_service(client):
    body = {
        "name": "Corte de Cabelo",
        "description": "Corte masculino",
        "duration": 30,
    }
    r_create = client.post("/api/services/", json=body, headers={"Authorization": "Bearer x"})
    assert r_create.status_code == 200
    created = r_create.json()

    r_get = client.get(f"/api/services/{created['id']}", headers={"Authorization": "Bearer x"})
    assert r_get.status_code == 200
    assert r_get.json()["name"] == "Corte de Cabelo"


def test_list_services_with_pagination(client):
    # cria alguns serviços
    for i in range(3):
        client.post(
            "/api/services/",
            json={
                "name": f"S{i}",
                "description": "d",
                "duration": 10,
                "price": "1.0",
                "images": [],
                "credentials": None,
                "promotions": None,
                "custom_fields": None,
            },
            headers={"Authorization": "Bearer x"},
        )

    r_list = client.get("/api/services/?page=1&per_page=2", headers={"Authorization": "Bearer x"})
    assert r_list.status_code == 200
    data = r_list.json()
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert len(data["services"]) <= 2


def test_update_and_delete_service(client):
    r_create = client.post(
        "/api/services/",
        json={
            "name": "Inicial",
            "description": "d",
            "duration": 10,
            "price": "1.0",
            "images": [],
            "credentials": None,
            "promotions": None,
            "custom_fields": None,
        },
        headers={"Authorization": "Bearer x"},
    )
    service_id = r_create.json()["id"]

    r_upd = client.put(
        f"/api/services/{service_id}",
        json={"name": "Atualizado"},
        headers={"Authorization": "Bearer x"},
    )
    assert r_upd.status_code == 200
    assert r_upd.json()["name"] == "Atualizado"

    r_del = client.delete(f"/api/services/{service_id}", headers={"Authorization": "Bearer x"})
    assert r_del.status_code == 200
    assert r_del.json()["message"]


def test_service_stats_and_template_validation(client):
    r_stats = client.get("/api/services/stats/overview", headers={"Authorization": "Bearer x"})
    assert r_stats.status_code == 200
    assert "total" in r_stats.json()

    r_rules = client.get("/api/services/template/validation", headers={"Authorization": "Bearer x"})
    assert r_rules.status_code == 200
    rules = r_rules.json()
    assert "requires_price" in rules and "max_images" in rules


