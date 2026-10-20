import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest

import config
from api import app
from db import get_db
from main import is_valid_nip, extract_nip_from_eml

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "OLLAMA_HOST", "http://127.0.0.1:11434")


def make_chunk(
    thinking="",
    content="",
    tool_calls=None,
    done=False,
    prompt_eval_count=None,
    eval_count=None,
):
    msg = MagicMock()
    msg.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "thinking": thinking,
        "tool_calls": tool_calls,
    }
    return MagicMock(
        message=msg,
        done=done,
        prompt_eval_count=prompt_eval_count,
        eval_count=eval_count,
    )


def make_stream(*chunks):
    async def _gen():
        for c in chunks:
            yield c

    return _gen()


def parse_sse(text: str) -> list[dict]:
    return [
        json.loads(block[6:])
        for block in text.strip().split("\n\n")
        if block.startswith("data: ")
    ]


def test_order_maker_config_defaults_and_update():
    res = client.get("/api/order-maker/config")
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["search_tool"] == "search_product"
    assert cfg["set_request_tool"] == "set_order_text"
    assert cfg["set_product_tool"] == "set_order_product"
    assert cfg["search_row_template"] == "{rank}. {name} (ID: {id})"
    assert cfg["search_empty_template"] == "No products found."
    assert cfg["set_text_template"] == "Saved order text at {at}: {text}"
    assert (
        cfg["set_product_template"]
        == "Set product at {at}: {name} (ID: {product_id}), amount: {amount}"
    )
    assert cfg["set_product_not_found_template"] == "Product {product_id} not found."
    assert (
        cfg["set_product_no_text_template"]
        == "No order text at {at}. Set order text first."
    )

    update_payload = {
        "model": "qwen2.5:14b",
        "system_prompt": "Custom system prompt",
        "search_tool": "szukaj_produktu",
        "set_request_tool": "ustaw_tekst",
        "set_product_tool": "ustaw_produkt",
        "search_row_template": "[{id}] {name} - {price} PLN",
        "search_empty_template": "Brak wynikow.",
        "set_text_template": "Zapisano tekst dla {at}: {text}",
        "set_product_template": "Przypisano {name} x{amount} na pozycji {at}",
        "set_product_not_found_template": "Nie ma produktu {product_id}",
        "set_product_no_text_template": "Brak tekstu na pozycji {at} przed dodaniem {product_id}",
        "resolve_ambiguity_tool": "rozstrzygnij_niejednoznacznosc",
        "resolve_ambiguity_template": "Rozstrzygnieto: {name} (ID: {id})",
        "resolve_ambiguity_none_template": "Brak reguly dla {ids}.",
    }
    res_put = client.put("/api/order-maker/config", json=update_payload)
    assert res_put.status_code == 200
    assert res_put.json()["search_tool"] == "szukaj_produktu"

    res_get2 = client.get("/api/order-maker/config")
    assert res_get2.status_code == 200
    assert res_get2.json() == update_payload


def test_order_maker_run_tools_and_streaming():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (42, 'Młotek ślusarski 500g', 3500, 23, 2000, 'http://img.com/hammer.jpg', 1, 'http://shop/hammer', 10)
            """
        )

    stream_1 = make_stream(
        make_chunk(thinking="Searching "),
        make_chunk(
            thinking="catalog...",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_text",
                        "arguments": {"at": 0, "text": "2x Mlotek slusarski"},
                    }
                },
                {
                    "function": {
                        "name": "search_product",
                        "arguments": {"phrase": "Mlotek", "limit": 5, "page": 1},
                    }
                },
            ],
            done=True,
            prompt_eval_count=20,
            eval_count=10,
        ),
    )

    stream_2 = make_stream(
        make_chunk(
            thinking="Assigning product 42...",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 0, "product_id": 42, "amount": 2},
                    }
                }
            ],
            done=True,
            prompt_eval_count=30,
            eval_count=15,
        )
    )

    stream_3 = make_stream(
        make_chunk(thinking="Do"),
        make_chunk(
            thinking="ne.",
            content="Added 2x Młotek ślusarski to the cart.",
            done=True,
            prompt_eval_count=40,
            eval_count=8,
        ),
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(side_effect=[stream_1, stream_2, stream_3])

        run_res = client.post(
            "/api/order-maker/run",
            json={
                "model": "qwen2.5:14b",
                "system_prompt": "Order assistant prompt",
                "messages": [
                    {"role": "user", "content": "Please order 2x Mlotek slusarski"}
                ],
                "cart": {},
            },
        )
        assert run_res.status_code == 200
        assert "text/event-stream" in run_res.headers["content-type"]

        events = parse_sse(run_res.text)
        assistant_events = [e for e in events if e["type"] == "assistant"]
        assert assistant_events[0]["message"]["thinking"] == "Searching "
        assert assistant_events[1]["message"]["thinking"] == "Searching catalog..."

        data = events[-1]
        assert data["type"] == "done"

        assert "0" in data["cart"]
        segment = data["cart"]["0"]
        assert segment["at"] == 0
        assert segment["text"] == "2x Mlotek slusarski"
        assert "42" in segment["products"]
        item = segment["products"]["42"]
        assert item["product_id"] == 42
        assert item["amount"] == 2
        assert item["product"]["name"] == "Młotek ślusarski 500g"
        assert item["product"]["price_cents"] == 3500

        tool_messages = [m for m in data["messages"] if m.get("role") == "tool"]
        assert len(tool_messages) == 3
        assert (
            tool_messages[0]["content"]
            == "Saved order text at 0: 2x Mlotek slusarski"
        )
        assert "1. Młotek ślusarski 500g (ID: 42)" in tool_messages[1]["content"]
        assert (
            tool_messages[2]["content"]
            == "Set product at 0: Młotek ślusarski 500g (ID: 42), amount: 2"
        )
        assert data["stats"]["prompt_tokens"] == 90
        assert data["stats"]["eval_tokens"] == 33
        order_id = data["order_id"]

        res_list = client.get("/api/order-maker/orders")
        assert res_list.status_code == 200
        orders = res_list.json()["orders"]
        assert len(orders) == 1
        assert orders[0]["id"] == order_id

        res_detail = client.get(f"/api/order-maker/orders/{order_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["id"] == order_id
        assert "0" in detail["cart"]
        assert len(detail["messages"]) > 0

        updated_cart = {
            "0": {
                "at": 0,
                "text": "2x Mlotek slusarski",
                "products": {
                    "42": {
                        "product_id": 42,
                        "amount": 5,
                    }
                },
            }
        }
        res_upd = client.put(
            f"/api/order-maker/orders/{order_id}",
            json={"cart": updated_cart},
        )
        assert res_upd.status_code == 200
        res_detail2 = client.get(f"/api/order-maker/orders/{order_id}")
        assert res_detail2.json()["cart"]["0"]["products"]["42"]["amount"] == 5

        res_del = client.delete(f"/api/order-maker/orders/{order_id}")
        assert res_del.status_code == 200
        res_list2 = client.get("/api/order-maker/orders")
        assert len(res_list2.json()["orders"]) == 0


def test_ambiguity_pairs_crud():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, active)
            VALUES (101, 'Szpachla 80mm A', 1500, 23, 800, 1),
                   (102, 'Szpachla 80mm B', 1700, 23, 900, 1)
            """
        )

    res_create = client.post(
        "/api/order-maker/ambiguity-pairs",
        json={
            "product_id_a": 102,
            "product_id_b": 101,
            "chosen_product_id": 101,
        },
    )
    assert res_create.status_code == 200

    res_list = client.get("/api/order-maker/ambiguity-pairs")
    assert res_list.status_code == 200
    pairs = res_list.json()["pairs"]
    assert len(pairs) == 1
    p = pairs[0]
    assert p["product_id_a"] == 101
    assert p["product_id_b"] == 102
    assert p["chosen_product_id"] == 101
    assert p["name_a"] == "Szpachla 80mm A"
    assert p["name_b"] == "Szpachla 80mm B"
    assert p["chosen_name"] == "Szpachla 80mm A"

    res_del = client.delete(f"/api/order-maker/ambiguity-pairs/{p['id']}")
    assert res_del.status_code == 200
    assert len(client.get("/api/order-maker/ambiguity-pairs").json()["pairs"]) == 0


def test_resolve_ambiguity_in_run():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, active)
            VALUES (201, 'Klej montażowy Szybki', 2500, 23, 1200, 1),
                   (202, 'Klej montażowy Standard', 2000, 23, 1000, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO ambiguity_pairs (product_id_a, product_id_b, chosen_product_id)
            VALUES (201, 202, 201)
            """
        )

    stream_1 = make_stream(
        make_chunk(
            thinking="Resolving between 202 and 201...",
            tool_calls=[
                {
                    "function": {
                        "name": "resolve_ambiguity",
                        "arguments": {"ids": [202, 201]},
                    }
                }
            ],
            done=True,
            prompt_eval_count=25,
            eval_count=10,
        )
    )
    stream_2 = make_stream(
        make_chunk(
            thinking="Done.",
            content="Selected Klej montażowy Szybki.",
            done=True,
            prompt_eval_count=35,
            eval_count=12,
        )
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(side_effect=[stream_1, stream_2])

        run_res = client.post(
            "/api/order-maker/run",
            json={
                "model": "qwen2.5:14b",
                "system_prompt": "Order prompt",
                "messages": [{"role": "user", "content": "Klej montazowy"}],
            },
        )
        assert run_res.status_code == 200
        events = parse_sse(run_res.text)
        data = events[-1]
        tool_messages = [m for m in data["messages"] if m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert (
            tool_messages[0]["content"]
            == "Resolved ambiguity: chosen product is Klej montażowy Szybki (ID: 201)"
        )


def test_order_maker_file_content_persistence():
    eml_sample = "From: client@example.com\nSubject: Order 123\n\nPlease send 5 widgets."
    res_create = client.post(
        "/api/order-maker/orders",
        json={
            "filename": "order_123.eml",
            "file_content": eml_sample,
        },
    )
    assert res_create.status_code == 200
    order_id = res_create.json()["id"]

    res_get = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["filename"] == "order_123.eml"
    assert detail["file_content"] == eml_sample

    updated_eml = "From: client@example.com\nSubject: Updated Order\n\nUpdated body"
    res_update = client.put(
        f"/api/order-maker/orders/{order_id}",
        json={"filename": "order_updated.eml", "file_content": updated_eml},
    )
    assert res_update.status_code == 200

    res_get2 = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_get2.status_code == 200
    detail2 = res_get2.json()
    assert detail2["filename"] == "order_updated.eml"
    assert detail2["file_content"] == updated_eml


def test_is_valid_nip():
    assert is_valid_nip("5260250274") is True
    assert is_valid_nip("5252674798") is True
    assert is_valid_nip("1234563218") is True

    # Invalid checksum
    assert is_valid_nip("1234567890") is False
    assert is_valid_nip("5260250275") is False


def test_extract_nip_from_eml(monkeypatch):
    # Standard format with hyphens
    eml_hyphens = "From: buyer@test.pl\nSubject: Order\n\nDane do faktury:\nNIP: 526-025-02-74\n"
    assert extract_nip_from_eml(eml_hyphens) == "5260250274"

    # Space separated
    eml_spaces = "From: buyer@test.pl\nSubject: Order\n\nFaktura VAT: 525 26 74 798\n"
    assert extract_nip_from_eml(eml_spaces) == "5252674798"

    # PL prefix without separator
    eml_pl = "From: buyer@test.pl\nSubject: Order\n\nNabywca PL5260250274 Jan Kowalski\n"
    assert extract_nip_from_eml(eml_pl) == "5260250274"

    # No NIP in email
    eml_none = "From: buyer@test.pl\nSubject: Order\n\nProsze o przeslanie 2 sztuk.\n"
    assert extract_nip_from_eml(eml_none) is None

    # Invalid checksum 10-digit number is not picked
    eml_invalid = "From: buyer@test.pl\nSubject: Order\n\nKod: 1234567890\n"
    assert extract_nip_from_eml(eml_invalid) is None

    # Ignores MY_NIP from env
    monkeypatch.setattr(config, "MY_NIP", "525-26-74-798")
    eml_with_both = (
        "From: store@mycompany.pl\n"
        "Subject: Re: Zamowienie\n\n"
        "Sprzedawca: Sklep Sp. z o.o., NIP: 525-26-74-798\n"
        "Klient: Firma B, NIP: 526-025-02-74\n"
    )
    assert extract_nip_from_eml(eml_with_both) == "5260250274"

    # If only MY_NIP is in email, returns None
    eml_only_my_nip = (
        "From: store@mycompany.pl\n"
        "Subject: Re: Zamowienie\n\n"
        "Sprzedawca: Sklep Sp. z o.o., NIP: 525-26-74-798\n"
    )
    assert extract_nip_from_eml(eml_only_my_nip) is None


def test_order_maker_nip_persistence():
    eml_buyer = (
        "From: buyer@firma.pl\n"
        "Subject: Zamowienie hurtowe\n\n"
        "Prosze wystawic fakture na NIP: 526-025-02-74\n"
    )
    res_create = client.post(
        "/api/order-maker/orders",
        json={"filename": "order_buyer.eml", "file_content": eml_buyer},
    )
    assert res_create.status_code == 200
    data = res_create.json()
    order_id = data["id"]
    assert data["nip"] == "5260250274"

    res_get = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_get.status_code == 200
    assert res_get.json()["nip"] == "5260250274"

    # Update with an email having a different NIP
    eml_buyer_2 = (
        "From: buyer2@firma.pl\n"
        "Subject: Nowe zamowienie\n\n"
        "NIP: 525-26-74-798\n"
    )
    res_update = client.put(
        f"/api/order-maker/orders/{order_id}",
        json={"filename": "order_buyer_2.eml", "file_content": eml_buyer_2},
    )
    assert res_update.status_code == 200
    assert res_update.json()["nip"] == "5252674798"

    res_get2 = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_get2.status_code == 200
    assert res_get2.json()["nip"] == "5252674798"


def test_get_company_not_found():
    res = client.get("/api/companies/5260250274")
    assert res.status_code == 404


def test_fetch_company_tool():
    mock_chat_response = MagicMock()
    mock_chat_response.message.model_dump.return_value = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "set_company_info",
                    "arguments": {
                        "nip": "526-025-02-74",
                        "name": "Super Firma Sp. z o.o.",
                        "adress": "ul. Prosta 10",
                        "zip_code": "00-850",
                        "city": "Warszawa",
                    },
                }
            }
        ],
    }

    with patch("llm.AsyncClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = AsyncMock(return_value=mock_chat_response)

        res = client.post(
            "/api/order-maker/fetch-company",
            json={
                "content": "Dane firmy:\nNIP: 526-025-02-74\nSuper Firma Sp. z o.o.\nul. Prosta 10, 00-850 Warszawa",
                "model": "qwen2.5:14b",
                "system_prompt": "Extract company info",
                "set_company_tool": "set_company_info",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["nip"] == "5260250274"
        assert data["company"] == {
            "nip": "5260250274",
            "name": "Super Firma Sp. z o.o.",
            "address": "ul. Prosta 10",
            "zip_code": "00-850",
            "city": "Warszawa",
            "discount": 0.0,
            "deadline": 0,
        }

        # Verify it was saved in DB
        res_get = client.get("/api/companies/5260250274")
        assert res_get.status_code == 200
        assert res_get.json() == data["company"]

        # Calling again with updated address upserts the company
        mock_chat_response_2 = MagicMock()
        mock_chat_response_2.message.model_dump.return_value = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "set_company_info",
                        "arguments": {
                            "nip": "5260250274",
                            "name": "Super Firma Sp. z o.o.",
                            "adress": "ul. Jasna 1",
                            "zip_code": "00-851",
                            "city": "Warszawa",
                        },
                    }
                }
            ],
        }
        instance.chat = AsyncMock(return_value=mock_chat_response_2)
        res_upsert = client.post(
            "/api/order-maker/fetch-company",
            json={
                "content": "Nowy adres",
                "model": "qwen2.5:14b",
                "system_prompt": "Extract company info",
                "set_company_tool": "set_company_info",
            },
        )
        assert res_upsert.status_code == 200
        assert res_upsert.json()["company"]["address"] == "ul. Jasna 1"


def test_order_maker_company_integration():
    # 1. Company in DB beforehand
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO companies (nip, name, address, zip_code, city, created_at, updated_at)
            VALUES ('5260250274', 'Testowa Firma', 'ul. Testowa 1', '01-234', 'Krakow', '2026-01-01', '2026-01-01')
            """
        )

    eml_with_nip = "From: buyer@test.pl\nSubject: Zamowienie\n\nNIP: 526-025-02-74\n"
    res_create = client.post(
        "/api/order-maker/orders",
        json={"filename": "order1.eml", "file_content": eml_with_nip},
    )
    assert res_create.status_code == 200
    create_data = res_create.json()
    order_id = create_data["id"]
    assert create_data["nip"] == "5260250274"
    assert create_data["company"] is not None
    assert create_data["company"]["name"] == "Testowa Firma"

    res_get = client.get(f"/api/order-maker/orders/{order_id}")
    assert res_get.status_code == 200
    assert res_get.json()["company"]["name"] == "Testowa Firma"

    # 2. Company not in DB -> fetch_company updates order
    eml_without_db_nip = "From: new@test.pl\nSubject: Nowe\n\nNIP: 525-26-74-798\n"
    res_create2 = client.post(
        "/api/order-maker/orders",
        json={"filename": "order2.eml", "file_content": eml_without_db_nip},
    )
    assert res_create2.status_code == 200
    order_id_2 = res_create2.json()["id"]
    assert res_create2.json()["company"] is None

    mock_chat = MagicMock()
    mock_chat.message.model_dump.return_value = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "set_company_info",
                    "arguments": {
                        "nip": "525-26-74-798",
                        "name": "Druga Firma",
                        "adress": "ul. Druga 2",
                        "zip_code": "02-345",
                        "city": "Poznan",
                    },
                }
            }
        ],
    }
    with patch("llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = AsyncMock(return_value=mock_chat)
        res_fetch = client.post(
            "/api/order-maker/fetch-company",
            json={
                "order_id": order_id_2,
                "content": eml_without_db_nip,
                "model": "qwen2.5:14b",
                "system_prompt": "Extract",
                "set_company_tool": "set_company_info",
            },
        )
        assert res_fetch.status_code == 200
        assert res_fetch.json()["company"]["name"] == "Druga Firma"

    res_get2 = client.get(f"/api/order-maker/orders/{order_id_2}")
    assert res_get2.status_code == 200
    assert res_get2.json()["nip"] == "5252674798"
    assert res_get2.json()["company"]["name"] == "Druga Firma"


def test_companies_crud():
    # 1. Create company with discount
    res_post = client.post(
        "/api/companies",
        json={
            "nip": "526-025-02-74",
            "name": "Alpha Corp",
            "address": "ul. Glowna 1",
            "zip_code": "00-001",
            "city": "Warszawa",
            "discount": 12.5,
        },
    )
    assert res_post.status_code == 200
    assert res_post.json()["nip"] == "5260250274"
    assert res_post.json()["name"] == "Alpha Corp"
    assert res_post.json()["discount"] == 12.5

    # 2. List companies
    res_list = client.get("/api/companies")
    assert res_list.status_code == 200
    comps = res_list.json()["companies"]
    matching = [c for c in comps if c["nip"] == "5260250274"]
    assert len(matching) == 1
    assert matching[0]["discount"] == 12.5

    # 3. Update company
    res_put = client.put(
        "/api/companies/5260250274",
        json={
            "name": "Alpha Corp Sp. z o.o.",
            "address": "ul. Nowa 5",
            "zip_code": "00-002",
            "city": "Warszawa",
            "discount": 15.0,
        },
    )
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "Alpha Corp Sp. z o.o."
    assert res_put.json()["address"] == "ul. Nowa 5"
    assert res_put.json()["discount"] == 15.0

    # 4. Update non-existent
    res_put_404 = client.put(
        "/api/companies/9999999999",
        json={
            "name": "None",
            "address": "None",
            "zip_code": "00-000",
            "city": "None",
        },
    )
    assert res_put_404.status_code == 404

    # 5. Delete company
    res_del = client.delete("/api/companies/5260250274")
    assert res_del.status_code == 200
    res_get_del = client.get("/api/companies/5260250274")
    assert res_get_del.status_code == 404


def test_connect_disconnect_email_and_auto_fill_nip():
    # Setup company
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO companies (nip, name, address, zip_code, city, created_at, updated_at)
            VALUES ('5260250274', 'Auto NIP Corp', 'ul. Test 1', '00-001', 'Warszawa', '2026-01-01', '2026-01-01')
            """
        )

    # 1. Connect email to NIP
    res_conn = client.post(
        "/api/companies/connect-email",
        json={"email": "klient@example.com", "nip": "526-025-02-74"},
    )
    assert res_conn.status_code == 200
    assert res_conn.json()["ok"] is True
    assert res_conn.json()["email"] == "klient@example.com"
    assert res_conn.json()["nip"] == "5260250274"
    assert res_conn.json()["company"]["name"] == "Auto NIP Corp"

    # 2. Upload EML from that sender that has NO NIP inside the email body
    eml_no_nip = "From: Jan Kowalski <klient@example.com>\nSubject: Zamowienie\n\nPoprosze 5 sztuk produktu.\n"
    res_order = client.post(
        "/api/order-maker/orders",
        json={"filename": "order_auto.eml", "file_content": eml_no_nip},
    )
    assert res_order.status_code == 200
    data = res_order.json()
    assert data["nip"] == "5260250274"  # Automatically filled from connected email!
    assert data["is_connected"] is True
    assert data["company"]["name"] == "Auto NIP Corp"

    # 3. Disconnect email
    res_disc = client.post(
        "/api/companies/disconnect-email",
        json={"email": "klient@example.com", "order_id": data["id"]},
    )
    assert res_disc.status_code == 200
    assert res_disc.json()["ok"] is True

    # 4. Next order from that sender without NIP in body is no longer auto-filled
    res_order2 = client.post(
        "/api/order-maker/orders",
        json={"filename": "order_auto_2.eml", "file_content": eml_no_nip},
    )
    assert res_order2.status_code == 200
    data2 = res_order2.json()
    assert data2["nip"] is None
    assert data2["is_connected"] is False
    assert data2["company"] is None


def test_order_maker_segment_cart_multiple_products():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (601, 'Puzzle 60 el. Zwierzęta', 2500, 23, 1000, NULL, 1, NULL, 5),
                   (602, 'Puzzle 60 el. Pojazdy', 2800, 23, 1100, NULL, 1, NULL, 8)
            """
        )

    stream_1 = make_stream(
        make_chunk(
            thinking="Setting segment 1 and adding two 60-element puzzle products...",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_text",
                        "arguments": {"at": 1, "text": "all puzzles with 60 elems"},
                    }
                },
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 1, "product_id": 601, "amount": 1},
                    }
                },
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 1, "product_id": 602, "amount": 2},
                    }
                },
            ],
            done=True,
            prompt_eval_count=25,
            eval_count=12,
        )
    )

    stream_2 = make_stream(
        make_chunk(
            content="Added 2 puzzle products to segment 1.",
            done=True,
            prompt_eval_count=15,
            eval_count=6,
        )
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(side_effect=[stream_1, stream_2])

        run_res = client.post(
            "/api/order-maker/run",
            json={
                "model": "qwen2.5:14b",
                "system_prompt": "Order assistant prompt",
                "messages": [
                    {"role": "user", "content": "I want all puzzles with 60 elems"}
                ],
                "cart": {},
            },
        )
        assert run_res.status_code == 200
        events = parse_sse(run_res.text)
        done_event = events[-1]
        assert done_event["type"] == "done"

        cart = done_event["cart"]
        assert "1" in cart
        segment = cart["1"]
        assert segment["at"] == 1
        assert segment["text"] == "all puzzles with 60 elems"
        assert len(segment["products"]) == 2
        assert "601" in segment["products"]
        assert "602" in segment["products"]
        assert segment["products"]["601"]["amount"] == 1
        assert segment["products"]["601"]["product"]["name"] == "Puzzle 60 el. Zwierzęta"
        assert segment["products"]["602"]["amount"] == 2
        assert segment["products"]["602"]["product"]["name"] == "Puzzle 60 el. Pojazdy"


def test_submit_woocommerce_order_unconfigured(monkeypatch):
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", None)
    res = client.post("/api/order-maker/orders/1/submit-woocommerce")
    assert res.status_code == 500
    assert "not configured" in res.json()["detail"]


def test_submit_woocommerce_order_not_found(monkeypatch):
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")
    res = client.post("/api/order-maker/orders/99999/submit-woocommerce")
    assert res.status_code == 404
    assert res.json()["detail"] == "Order not found"


def test_submit_woocommerce_order_empty_cart(monkeypatch):
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")

    create_res = client.post(
        "/api/order-maker/orders",
        json={"filename": "test.eml", "file_content": "Subject: Test\nFrom: test@example.com\n\nBody"},
    )
    order_id = create_res.json()["id"]

    # 1. Missing NIP -> 400
    res_no_nip = client.post(f"/api/order-maker/orders/{order_id}/submit-woocommerce", json={"confirmed": True})
    assert res_no_nip.status_code == 400
    assert "NIP is required" in res_no_nip.json()["detail"]

    client.put(
        f"/api/order-maker/orders/{order_id}",
        json={"file_content": "Subject: Test\nFrom: test@example.com\n\nNIP: 5252674798\nBody"},
    )

    # 2. Missing confirmation -> 400
    res_unconf = client.post(f"/api/order-maker/orders/{order_id}/submit-woocommerce", json={"confirmed": False})
    assert res_unconf.status_code == 400
    assert "Confirmation required" in res_unconf.json()["detail"]

    # 3. Confirmed but empty cart -> 400
    res = client.post(f"/api/order-maker/orders/{order_id}/submit-woocommerce", json={"confirmed": True})
    assert res.status_code == 400
    assert res.json()["detail"] == "Cart has no products"


def test_submit_woocommerce_order_success(monkeypatch):
    import httpx
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")
    monkeypatch.setattr(config, "FAKTUROWNIA_URL", "https://demo.fakturownia.pl")
    monkeypatch.setattr(config, "FAKTUROWNIA_API_TOKEN", "tok_test")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (101, 'Book Alpha', 5000, 5, 2000, NULL, 1, 'https://example.com/p/101', 10)
            """
        )
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (102, 'Toy Beta', 3000, 23, 1000, NULL, 1, 'https://example.com/p/102', 5)
            """
        )

    create_res = client.post(
        "/api/order-maker/orders",
        json={"filename": "test.eml", "file_content": "Subject: Order\nFrom: buyer@firm.com\n\nNIP: 5252674798\nPlease send items."},
    )
    order_id = create_res.json()["id"]

    client.post(
        "/api/companies",
        json={"nip": "5252674798", "name": "Firm Sp. z o.o.", "address": "ul. Prosta 1", "zip_code": "00-001", "city": "Warszawa", "discount": 10.0, "deadline": 14},
    )
    shipping_res = client.post(
        "/api/shippings",
        json={"nip": "5252674798", "name": "Jan Kowalski", "address": "ul. Kwiatowa 5", "zip_code": "01-002", "city": "Warszawa", "phone": "123456789", "email": "jan@kowalski.pl"},
    )
    shipping_id = shipping_res.json()["id"]
    client.post(f"/api/order-maker/orders/{order_id}/connect-shipping", json={"shipping_id": shipping_id})

    # Cart with 2 segments, one of which shares a product to verify aggregation
    cart = {
        "1": {
            "at": 1,
            "text": "Book Alpha",
            "products": {
                "101": {
                    "product_id": 101,
                    "amount": 2,
                    "product": {"id": 101, "name": "Book Alpha", "price_cents": 5000},
                }
            },
        },
        "2": {
            "at": 2,
            "text": "Book Alpha again and Toy Beta",
            "products": {
                "101": {
                    "product_id": 101,
                    "amount": 1,
                    "product": {"id": 101, "name": "Book Alpha", "price_cents": 5000},
                },
                "102": {
                    "product_id": 102,
                    "amount": 3,
                    "product": {"id": 102, "name": "Toy Beta", "price_cents": 3000},
                },
            },
        },
    }
    client.put(f"/api/order-maker/orders/{order_id}", json={"cart": cart})

    captured_requests = []

    async def mock_post(url, *args, **kwargs):
        json_body = kwargs.get("json")
        auth = kwargs.get("auth") or (args[0] if len(args) > 0 else None)
        captured_requests.append({"url": str(url), "auth": auth, "json": json_body})
        if "fakturownia.pl" in str(url):
            return httpx.Response(
                201,
                json={"id": 77665, "number": "FV 55/2026", "token": "faktoken123"},
                request=httpx.Request("POST", str(url)),
            )
        return httpx.Response(201, json={"id": 88442, "status": "on-hold"}, request=httpx.Request("POST", str(url)))

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        res = client.post(
            f"/api/order-maker/orders/{order_id}/submit-woocommerce",
            json={"customer_note": "Handle with care", "confirmed": True},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["woocommerce_order_id"] == 88442
        assert data["fakturownia_id"] == 77665
        assert data["fakturownia_number"] == "FV 55/2026"
        assert data["fakturownia_url"] == "https://demo.fakturownia.pl/invoices/77665"
        assert data["order_url"] == "https://example.com/wp-admin/post.php?post=88442&action=edit"

    assert len(captured_requests) == 2
    # 1. Fakturownia request
    fak_req = captured_requests[0]
    assert fak_req["url"] == "https://demo.fakturownia.pl/invoices.json"
    assert fak_req["json"]["invoice"]["payment_to_kind"] == 14
    assert fak_req["json"]["invoice"]["positions"][0]["discount_percent"] == 10.0

    # 2. WooCommerce request
    req = captured_requests[1]
    assert req["url"] == "https://example.com/wp-json/wc/v3/orders"
    assert req["auth"] == ("ck_test", "cs_test")

    payload = req["json"]
    assert payload["customer_id"] == 1
    assert payload["status"] == "on-hold"
    assert payload["customer_note"] == "Handle with care"
    assert payload["meta_data"] == [
        {"key": "_billing_nip", "value": "5252674798"},
        {"key": "_woo_fakturownia_faktura", "value": {"id": 77665, "numer": "FV 55/2026"}},
        {"key": "_woo_fakturownia_faktura_hash", "value": "faktoken123"},
    ]
    assert payload["billing"]["company"] == "Firm Sp. z o.o."
    assert payload["billing"]["address_1"] == "ul. Prosta 1"
    assert payload["billing"]["city"] == "Warszawa"
    assert payload["billing"]["postcode"] == "00-001"
    assert payload["billing"]["email"] == "jan@kowalski.pl"
    assert payload["billing"]["phone"] == "123456789"

    assert payload["shipping"]["first_name"] == "Jan Kowalski"
    assert payload["shipping"]["address_1"] == "ul. Kwiatowa 5"
    assert payload["shipping"]["city"] == "Warszawa"
    assert payload["shipping"]["postcode"] == "01-002"
    assert payload["shipping"]["phone"] == "123456789"

    # Line items check:
    # 101 (tax 5%): gross 50.00 -> net unit 5000*100/105 = 4761.90 cents.
    # Quantity 3: subtotal 142.86, with 10% discount total 128.57
    # 102 (tax 23%): gross 30.00 -> net unit 3000*100/123 = 2439.02 cents.
    # Quantity 3: subtotal 73.17, with 10% discount total 65.85
    items_by_id = {item["product_id"]: item for item in payload["line_items"]}
    assert items_by_id[101]["quantity"] == 3
    assert items_by_id[101]["subtotal"] == "142.86"
    assert items_by_id[101]["total"] == "128.57"

    assert items_by_id[102]["quantity"] == 3
    assert items_by_id[102]["subtotal"] == "73.17"
    assert items_by_id[102]["total"] == "65.85"

    # Verify persisted in database
    get_res = client.get(f"/api/order-maker/orders/{order_id}")
    assert get_res.status_code == 200
    assert get_res.json()["woocommerce_order_id"] == 88442

    list_res = client.get("/api/order-maker/orders")
    assert list_res.status_code == 200
    summary = next(o for o in list_res.json()["orders"] if o["id"] == order_id)
    assert summary["woocommerce_order_id"] == 88442


def test_submit_woocommerce_order_without_discount_uses_net_price(monkeypatch):
    import httpx
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")
    monkeypatch.setattr(config, "FAKTUROWNIA_URL", "https://demo.fakturownia.pl")
    monkeypatch.setattr(config, "FAKTUROWNIA_API_TOKEN", "tok_test")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (201, 'Book Beta', 10500, 5, 5000, NULL, 1, 'https://example.com/p/201', 10)
            """
        )

    create_res = client.post(
        "/api/order-maker/orders",
        json={"filename": "order2.eml", "file_content": "Subject: Order 2\nFrom: guest@example.com\n\nNIP: 5252674798\nItems please"},
    )
    order_id = create_res.json()["id"]

    cart = {
        "1": {
            "at": 1,
            "text": "Book Beta",
            "products": {
                "201": {
                    "product_id": 201,
                    "amount": 2,
                    "product": {"id": 201, "name": "Book Beta", "price_cents": 10500, "tax_class": 5},
                }
            },
        }
    }
    client.put(f"/api/order-maker/orders/{order_id}", json={"cart": cart})

    captured_requests = []

    async def mock_post(url, *args, **kwargs):
        json_body = kwargs.get("json")
        auth = kwargs.get("auth") or (args[0] if len(args) > 0 else None)
        captured_requests.append({"url": str(url), "auth": auth, "json": json_body})
        if "fakturownia.pl" in str(url):
            return httpx.Response(
                201,
                json={"id": 88001, "number": "FV 101/2026", "token": "tok88"},
                request=httpx.Request("POST", str(url)),
            )
        return httpx.Response(201, json={"id": 99001, "status": "on-hold"}, request=httpx.Request("POST", str(url)))

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        res = client.post(f"/api/order-maker/orders/{order_id}/submit-woocommerce", json={"confirmed": True})
        assert res.status_code == 200

    wc_req = next(r for r in captured_requests if "wc/v3/orders" in r["url"])
    payload = wc_req["json"]
    # 105.00 gross with 5% tax is 100.00 net. Quantity 2 -> subtotal 200.00, total 200.00
    item = payload["line_items"][0]
    assert item["product_id"] == 201
    assert item["quantity"] == 2
    assert item["subtotal"] == "200.00"
    assert item["total"] == "200.00"




