import pytest
import os
import sys
import uuid
from httpx import AsyncClient, ASGITransport

# Ensure app is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app

@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app, root_path="")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200
        assert "Welcome" in resp.text

@pytest.mark.asyncio
async def test_full_query_lifecycle():
    transport = ASGITransport(app=app, root_path="")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_resp = await ac.post("/token", data={
            "username": "testuser2",
            "password": os.getenv("TEST_USER_PASSWORD", "your_actual_password_here")
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "question": "List all products",
            "connection_name": "northwind_small.sqlite",
            "save": True,
            "query_key": "pytest_test_query"
        }
        answer_resp = await ac.get("/answer", headers=headers, params=params)
        assert answer_resp.status_code == 200
        assert "answer" in answer_resp.json()

        list_resp = await ac.get("/list_saved_queries", headers=headers)
        assert list_resp.status_code == 200
        assert any(q["query_key"] == "pytest_test_query" for q in list_resp.json()["saved_queries"])

        delete_resp = await ac.delete("/delete_query", headers=headers, params={"query_key": "pytest_test_query"})
        assert delete_resp.status_code == 200

@pytest.mark.asyncio
async def test_register_and_new_connection_and_list():
    transport = ASGITransport(app=app, root_path="")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        username = f"pytest_user_{uuid.uuid4().hex[:8]}"
        password = "testpass123"

        register_resp = await ac.post("/register", json={
            "name": username,
            "password": password,
            "email": f"{username}@example.com"
        })
        assert register_resp.status_code == 200

        login_resp = await ac.post("/token", data={"username": username, "password": password})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        new_conn_resp = await ac.post("/new_connection", headers=headers, json={
            "db_user": "admin",
            "db_password": "password",
            "db_host": "localhost",
            "db_port": 5432,
            "db_type": "sqlite",
            "connection_name": "northwind_small.sqlite"
        })
        assert new_conn_resp.status_code == 200
        assert "connection_id" in new_conn_resp.json()

        list_resp = await ac.get("/list_connections", headers=headers)
        assert list_resp.status_code == 200
        assert any(conn["connection_name"] == "northwind_small.sqlite" for conn in list_resp.json())

@pytest.mark.asyncio
async def test_get_db_info():
    transport = ASGITransport(app=app, root_path="")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        username = f"pytest_user_{uuid.uuid4().hex[:8]}"
        password = "testpass123"

        register_resp = await ac.post("/register", json={
            "name": username,
            "password": password,
            "email": f"{username}@example.com"
        })
        assert register_resp.status_code == 200

        login_resp = await ac.post("/token", data={"username": username, "password": password})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await ac.post("/new_connection", headers=headers, json={
            "db_user": "admin",
            "db_password": "password",
            "db_host": "localhost",
            "db_port": 5432,
            "db_type": "sqlite",
            "connection_name": "northwind_small.sqlite"
        })

        resp = await ac.get("/db_info", headers=headers, params={
            "db_name": "northwind_small.sqlite"
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

@pytest.mark.asyncio
async def test_save_query_explicit_endpoint():
    transport = ASGITransport(app=app, root_path="")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_resp = await ac.post("/token", data={
            "username": "testuser2",
            "password": os.getenv("TEST_USER_PASSWORD", "your_actual_password_here")
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        save_resp = await ac.post("/save_query", headers=headers, params={
            "query_key": "pytest_explicit_query",
            "question": "List customers",
            "sql_query": "SELECT * FROM customers"
        })
        assert save_resp.status_code == 200
        assert "message" in save_resp.json()

        delete_resp = await ac.delete("/delete_query", headers=headers, params={"query_key": "pytest_explicit_query"})
        assert delete_resp.status_code == 200
