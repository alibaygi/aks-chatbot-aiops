"""tests/test_auth.py — registration and login endpoint tests."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "strongpass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "id" in data


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "bob@example.com", "password": "strongpass123"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "charlie@example.com", "password": "mypassword"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "charlie@example.com", "password": "mypassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "diana@example.com", "password": "correctpassword"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "diana@example.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "eve@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "eve@example.com"
