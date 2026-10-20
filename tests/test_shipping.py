import json
from unittest.mock import AsyncMock, MagicMock, patch
from email.message import EmailMessage
from fastapi.testclient import TestClient
import pytest

import config
from api import app
from db import get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "OLLAMA_HOST", "http://127.0.0.1:11434")


def test_shipping_crud():
    # 1. Initially empty
    res = client.get("/api/shippings")
    assert res.status_code == 200
    assert res.json()["shippings"] == []

    # 2. Create shipping
    payload = {
        "nip": "5260250274",
        "name": "Magazyn Centralny",
        "address": "ul. Logistyczna 10",
        "zip_code": "01-234",
        "city": "Warszawa",
        "phone": "+48 123 456 789",
        "email": "magazyn@example.com",
    }
    res_create = client.post("/api/shippings", json=payload)
    assert res_create.status_code == 200
    created = res_create.json()
    assert created["id"] > 0
    assert created["name"] == "Magazyn Centralny"
    assert created["nip"] == "5260250274"
    assert created["phone"] == "+48 123 456 789"
    ship_id = created["id"]

    # 3. Get by ID
    res_get = client.get(f"/api/shippings/{ship_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Magazyn Centralny"

    # 4. Filter by NIP
    res_filter = client.get("/api/shippings?nip=526-025-02-74")
    assert res_filter.status_code == 200
    assert len(res_filter.json()["shippings"]) == 1

    res_filter_none = client.get("/api/shippings?nip=9999999999")
    assert res_filter_none.status_code == 200
    assert len(res_filter_none.json()["shippings"]) == 0

    # 5. Update
    update_payload = {
        "nip": "5260250274",
        "name": "Magazyn Główny",
        "address": "ul. Nowa 5",
        "zip_code": "01-235",
        "city": "Warszawa",
        "phone": "555-123",
        "email": "glowny@example.com",
    }
    res_update = client.put(f"/api/shippings/{ship_id}", json=update_payload)
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Magazyn Główny"
    assert res_update.json()["phone"] == "555-123"

    # 6. Delete
    res_del = client.delete(f"/api/shippings/{ship_id}")
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True

    res_get_deleted = client.get(f"/api/shippings/{ship_id}")
    assert res_get_deleted.status_code == 404


def test_order_shipping_connection():
    # Create order
    res_order = client.post(
        "/api/order-maker/orders",
        json={"filename": "order1.eml", "file_content": "From: test@example.com\nSubject: Order\n"},
    )
    assert res_order.status_code == 200
    order_id = res_order.json()["id"]

    # Create shipping
    res_ship = client.post(
        "/api/shippings",
        json={
            "nip": "5260250274",
            "name": "Oddział Kraków",
            "address": "ul. Krakowska 1",
            "zip_code": "30-001",
            "city": "Kraków",
            "phone": "123456",
            "email": "krakow@example.com",
        },
    )
    assert res_ship.status_code == 200
    shipping_id = res_ship.json()["id"]

    # Connect shipping
    res_conn = client.post(
        f"/api/order-maker/orders/{order_id}/connect-shipping",
        json={"shipping_id": shipping_id},
    )
    assert res_conn.status_code == 200
    assert res_conn.json()["ok"] is True
    assert res_conn.json()["shipping_id"] == shipping_id
    assert res_conn.json()["shipping"]["name"] == "Oddział Kraków"

    # Verify order has shipping
    res_order_get = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_order_get.status_code == 200
    assert res_order_get.json()["shipping_id"] == shipping_id
    assert res_order_get.json()["shipping"]["name"] == "Oddział Kraków"

    # Disconnect shipping
    res_disc = client.post(f"/api/order-maker/orders/{order_id}/disconnect-shipping")
    assert res_disc.status_code == 200
    assert res_disc.json()["ok"] is True

    # Verify disconnected
    res_order_get2 = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_order_get2.status_code == 200
    assert res_order_get2.json()["shipping_id"] is None
    assert res_order_get2.json()["shipping"] is None


def test_fetch_shipping_tool_call():
    # Create order with NIP
    res_order = client.post(
        "/api/order-maker/orders",
        json={
            "filename": "order_nip.eml",
            "file_content": "From: test@example.com\nSubject: Order\n\nNIP: 5260250274\n",
        },
    )
    assert res_order.status_code == 200
    order_id = res_order.json()["id"]

    mock_tool_call = {
        "function": {
            "name": "set_shipping_info",
            "arguments": {
                "nip": "5260250274",
                "name": "Jan Kowalski",
                "address": "ul. Polna 12",
                "zip_code": "00-111",
                "city": "Warszawa",
                "phone": "+48 987 654 321",
                "email": "jan@example.com",
            },
        }
    }
    mock_msg = MagicMock()
    mock_msg.model_dump.return_value = {
        "role": "assistant",
        "content": "",
        "tool_calls": [mock_tool_call],
    }
    mock_res = MagicMock(message=mock_msg)

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=mock_res)

        res_fetch = client.post(
            "/api/order-maker/fetch-shipping",
            json={
                "order_id": order_id,
                "content": "Deliver to Jan Kowalski, ul. Polna 12, 00-111 Warszawa, tel 987654321",
            },
        )
        assert res_fetch.status_code == 200
        data = res_fetch.json()
        assert data["ok"] is True
        shipping = data["shipping"]
        assert shipping["name"] == "Jan Kowalski"
        assert shipping["address"] == "ul. Polna 12"
        assert shipping["city"] == "Warszawa"
        assert shipping["phone"] == "+48 987 654 321"

        # Verify connected to order
        res_order_get = client.get(f"/api/order-maker/orders/{order_id}")
        assert res_order_get.status_code == 200
        assert res_order_get.json()["shipping_id"] == shipping["id"]
        assert res_order_get.json()["shipping"]["name"] == "Jan Kowalski"


def test_fetch_shipping_from_eml():
    eml = EmailMessage()
    eml["From"] = "sender@example.com"
    eml["To"] = "store@example.com"
    eml["Subject"] = "Delivery info"
    eml.set_content("Adres dostawy: Anna Nowak, ul. Kwiatowa 3, 20-001 Lublin, tel 600700800, email: anna@nowak.pl")

    mock_tool_call = {
        "function": {
            "name": "set_shipping_info",
            "arguments": {
                "nip": "",
                "name": "Anna Nowak",
                "address": "ul. Kwiatowa 3",
                "zip_code": "20-001",
                "city": "Lublin",
                "phone": "600700800",
                "email": "anna@nowak.pl",
            },
        }
    }
    mock_msg = MagicMock()
    mock_msg.model_dump.return_value = {
        "role": "assistant",
        "content": "",
        "tool_calls": [mock_tool_call],
    }
    mock_res = MagicMock(message=mock_msg)

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=mock_res)

        res = client.post(
            "/api/shippings/fetch-from-eml",
            files={"file": ("order.eml", eml.as_bytes(), "message/rfc822")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["shipping"]["name"] == "Anna Nowak"
        assert data["shipping"]["city"] == "Lublin"
        assert data["shipping"]["phone"] == "600700800"


def test_shipping_with_company_name():
    # Create company
    client.post(
        "/api/companies",
        json={
            "nip": "5260250274",
            "name": "Acme Corp",
            "address": "ul. Prosta 1",
            "zip_code": "00-001",
            "city": "Warszawa",
        },
    )

    # Create shipping with same NIP
    res = client.post(
        "/api/shippings",
        json={
            "nip": "5260250274",
            "name": "Acme Warehouse",
            "address": "ul. Magazynowa 2",
            "zip_code": "00-002",
            "city": "Warszawa",
        },
    )
    assert res.status_code == 200
    assert res.json()["company_name"] == "Acme Corp"

    # List shippings
    res_list = client.get("/api/shippings")
    assert res_list.status_code == 200
    shippings = res_list.json()["shippings"]
    assert any(s["name"] == "Acme Warehouse" and s["company_name"] == "Acme Corp" for s in shippings)


def test_shipping_config_crud():
    res = client.get("/api/shipping/config")
    assert res.status_code == 200
    cfg = res.json()
    assert "model" in cfg
    assert "system_prompt" in cfg

    update_payload = {
        "model": "qwen2.5:14b",
        "system_prompt": "Custom shipping prompt",
    }
    res_put = client.put("/api/shipping/config", json=update_payload)
    assert res_put.status_code == 200
    assert res_put.json()["model"] == "qwen2.5:14b"
    assert res_put.json()["system_prompt"] == "Custom shipping prompt"

    res_get2 = client.get("/api/shipping/config")
    assert res_get2.status_code == 200
    assert res_get2.json()["model"] == "qwen2.5:14b"
    assert res_get2.json()["system_prompt"] == "Custom shipping prompt"


def test_extract_shipping_structured_output():
    json_content = json.dumps({
        "nip": "526-025-02-74",
        "name": "Jan Kowalski",
        "address": "ul. Kwiatowa 5",
        "zip_code": "00-123",
        "city": "Warszawa",
        "phone": "+48 500 600 700",
        "email": "jan@example.com",
    })
    mock_msg = MagicMock(content=json_content)
    mock_res = MagicMock(message=mock_msg)

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=mock_res)

        res = client.post(
            "/api/shippings/extract",
            json={"text": "Wysyłka: Jan Kowalski, ul. Kwiatowa 5, 00-123 Warszawa, tel 500 600 700, NIP: 526-025-02-74"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        shipping = data["shipping"]
        assert shipping["nip"] == "5260250274"
        assert shipping["name"] == "Jan Kowalski"
        assert shipping["address"] == "ul. Kwiatowa 5"
        assert shipping["zip_code"] == "00-123"
        assert shipping["city"] == "Warszawa"
        assert shipping["phone"] == "+48 500 600 700"
        assert shipping["email"] == "jan@example.com"

        call_kwargs = mock_instance.chat.call_args.kwargs
        assert "format" in call_kwargs
        assert call_kwargs["format"]["type"] == "object"


def test_extract_shipping_empty_text():
    res = client.post("/api/shippings/extract", json={"text": "   "})
    assert res.status_code == 400


