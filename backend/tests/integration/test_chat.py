"""
Integration tests for Chat API endpoints.
Requires a running backend with test database.
"""
import pytest
from httpx import AsyncClient

from app.main import app

BASE = "/api/v1"


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    """Register and login a test user, return auth headers."""
    user = {
        "username": "chattest",
        "email": "chattest@example.com",
        "password": "testpassword123",
    }
    # Register
    resp = await async_client.post(f"{BASE}/auth/register", json=user)
    if resp.status_code != 201:
        # Already exists — just login
        resp = await async_client.post(f"{BASE}/auth/login", json={
            "email": user["email"],
            "password": user["password"],
        })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_conversation(async_client: AsyncClient, auth_headers: dict):
    """POST /chat/conversations creates a new conversation."""
    resp = await async_client.post(
        f"{BASE}/chat/conversations",
        json={"title": "Test conversation"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test conversation"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(async_client: AsyncClient, auth_headers: dict):
    """GET /chat/conversations returns paginated list."""
    resp = await async_client.get(
        f"{BASE}/chat/conversations",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_send_message_no_stream(async_client: AsyncClient, auth_headers: dict):
    """POST /chat/message (non-streaming) returns assistant response."""
    # First create a conversation
    conv_resp = await async_client.post(
        f"{BASE}/chat/conversations",
        json={"title": "Chat test"},
        headers=auth_headers,
    )
    conv_id = conv_resp.json()["id"]

    # Send message
    resp = await async_client.post(
        f"{BASE}/chat/message",
        json={
            "message": "Hello, what is 2 + 2?",
            "conversation_id": conv_id,
            "use_memory": False,
            "stream": False,
        },
        headers=auth_headers,
        timeout=60.0,
    )
    assert resp.status_code == 200
    assert "data: " in resp.text
    lines = [line.strip() for line in resp.text.split("\n") if line.startswith("data: ")]
    assert len(lines) > 0


@pytest.mark.asyncio
async def test_get_conversation_messages(async_client: AsyncClient, auth_headers: dict):
    """GET /chat/conversations/{id}/messages returns message list."""
    conv_resp = await async_client.post(
        f"{BASE}/chat/conversations",
        json={"title": "Messages test"},
        headers=auth_headers,
    )
    conv_id = conv_resp.json()["id"]

    resp = await async_client.get(
        f"{BASE}/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data


@pytest.mark.asyncio
async def test_delete_conversation(async_client: AsyncClient, auth_headers: dict):
    """DELETE /chat/conversations/{id} removes conversation."""
    conv_resp = await async_client.post(
        f"{BASE}/chat/conversations",
        json={"title": "To delete"},
        headers=auth_headers,
    )
    conv_id = conv_resp.json()["id"]

    del_resp = await async_client.delete(
        f"{BASE}/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code in (200, 204)

    # Verify it's gone
    get_resp = await async_client.get(
        f"{BASE}/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    """Requests without token return 401."""
    resp = await async_client.get(f"{BASE}/chat/conversations")
    assert resp.status_code == 401
