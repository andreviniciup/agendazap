import os
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from types import SimpleNamespace
from app.main import app
from app.dependencies import get_current_active_user, get_service_service


class FakeService:
    async def create_service(self, data, user):
        return SimpleNamespace(
            id="00000000-0000-0000-0000-000000000000",
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
            created_at=None,
            updated_at=None,
            category=None,
        )


async def override_user():
    return SimpleNamespace(id="u", email="e", is_active_bool=True, template_type="consultation")


async def override_service():
    return FakeService()


app.dependency_overrides[get_current_active_user] = override_user
app.dependency_overrides[get_service_service] = override_service

client = TestClient(app)
resp = client.post(
    "/api/services/",
    json={"name": "x", "description": "d", "duration": 30},
    headers={"Authorization": "Bearer x"},
)
print(resp.status_code)
print(resp.text)


