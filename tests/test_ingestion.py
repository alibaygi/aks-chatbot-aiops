"""tests/test_ingestion.py — document ingestion endpoint tests."""

import io
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str, password: str) -> str:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


SAMPLE_MARKDOWN = b"# Hello\n\nThis is a test document for ingestion."


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_ingest_markdown(client: AsyncClient):
    """Uploading a .md file should create document chunks and return 200."""
    token = await _register_and_login(client, "ingest1@example.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.ingestion.service.OpenAIEmbeddings.aembed_documents",
        new_callable=AsyncMock,
        return_value=[[0.1] * 1536],
    ):
        response = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("test.md", io.BytesIO(SAMPLE_MARKDOWN), "text/markdown")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.md"
    assert data["chunk_count"] >= 1


async def test_list_documents_empty(client: AsyncClient):
    token = await _register_and_login(client, "ingest2@example.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_ingest_unsupported_type(client: AsyncClient):
    token = await _register_and_login(client, "ingest3@example.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("data.csv", io.BytesIO(b"a,b,c"), "text/csv")},
    )
    assert response.status_code == 400


async def test_delete_document_not_found(client: AsyncClient):
    token = await _register_and_login(client, "ingest4@example.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.delete("/api/v1/documents/nonexistent.md", headers=headers)
    assert response.status_code == 404


async def test_documents_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401
