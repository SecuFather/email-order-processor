from unittest.mock import patch
from fastapi.testclient import TestClient
import httpx
import pytest

import config
from api import app
from db import get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")


def test_variants_list_and_update():
    with get_db() as conn:
        conn.execute("INSERT INTO variants (id, name, stock) VALUES (1, 'Variant Alpha', 10)")
        conn.execute("INSERT INTO variants (id, name, stock) VALUES (2, 'Variant Beta', NULL)")

    # 1. GET /api/variants
    res = client.get("/api/variants")
    assert res.status_code == 200
    variants = res.json()["variants"]
    assert len(variants) == 2
    assert variants[0]["id"] == 1
    assert variants[0]["name"] == "Variant Alpha"
    assert variants[0]["stock"] == 10
    assert variants[1]["id"] == 2
    assert variants[1]["name"] == "Variant Beta"
    assert variants[1]["stock"] is None

    # 2. PUT /api/variants/{id} to update name and stock
    res_upd = client.put(
        "/api/variants/1",
        json={"name": "Variant Alpha Updated", "price_cents": 1999, "stock": 25, "product_name": "T-Shirt"},
    )
    assert res_upd.status_code == 200
    updated = res_upd.json()
    assert updated["id"] == 1
    assert updated["name"] == "Variant Alpha Updated"
    assert updated["price_cents"] == 1999
    assert updated["stock"] == 25
    assert updated["product_name"] == "T-Shirt"

    # 3. PUT non-existent variant returns 404
    res_404 = client.put("/api/variants/999", json={"name": "Non-existent", "stock": 0})
    assert res_404.status_code == 404


def test_delete_all_variants():
    with get_db() as conn:
        conn.execute("INSERT INTO variants (id, name, stock) VALUES (1, 'Variant A', 5)")

    res = client.delete("/api/variants")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
        assert count == 0


def test_variant_inherits_cost_and_active_from_parent_product():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, active)
            VALUES (500, 'Top Product 1', 9900, 23, 3350, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, active)
            VALUES (600, 'Top Inactive Product', 5000, 23, 1200, 0)
            """
        )
        conn.execute(
            """
            INSERT INTO variants (id, name, parent_id, stock)
            VALUES (501, 'Variant 501', 500, 10)
            """
        )
        conn.execute(
            """
            INSERT INTO variants (id, name, parent_id, stock)
            VALUES (601, 'Variant 601', 600, 2)
            """
        )

    res = client.get("/api/variants")
    assert res.status_code == 200
    vars_by_id = {v["id"]: v for v in res.json()["variants"]}

    v501 = vars_by_id[501]
    assert v501["prod_cost_cents"] == 3350
    assert v501["product_name"] == "Top Product 1"
    assert v501["active"] is True

    v601 = vars_by_id[601]
    assert v601["prod_cost_cents"] == 1200
    assert v601["product_name"] == "Top Inactive Product"
    assert v601["active"] is False


def test_sync_woocommerce_variable_products():
    mock_products = [
        {
            "id": 100,
            "name": "Koszulka",
            "price": "50.00",
            "tax_class": "",
            "date_modified": "2026-10-22T10:00:00",
            "type": "variable",
            "stock_quantity": None,
            "permalink": "https://example.com/p/koszulka",
            "meta_data": [{"key": "_prod_cost", "value": "22.50"}],
            "images": [{"src": "https://example.com/koszulka.jpg"}],
        }
    ]

    mock_variations = [
        {
            "id": 101,
            "name": "Koszulka - Czerwona, M",
            "stock_quantity": 7,
            "permalink": "https://example.com/var-ignored",
            "meta_data": [{"key": "_prod_cost", "value": "99.00"}],
            "image": {"src": "https://example.com/var-ignored.jpg"},
        },
        {
            "id": 102,
            "name": "",
            "attributes": [{"name": "Rozmiar", "option": "L"}],
            "stock_quantity": 0,
        },
    ]

    def mock_get(url, auth, params):
        if url.endswith("/products"):
            return httpx.Response(200, json=mock_products, request=httpx.Request("GET", url))
        elif "/products/100/variations" in url:
            return httpx.Response(200, json=mock_variations, request=httpx.Request("GET", url))
        raise AssertionError(f"Unexpected url: {url}")

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        res = client.post("/api/woocommerce/sync")
        assert res.status_code == 200
        data = res.json()
        assert data["synced_count"] == 1
        assert data["synced_variants_count"] == 2

    with get_db() as conn:
        v1 = conn.execute("SELECT * FROM variants WHERE id = 101").fetchone()
        assert v1["name"] == "Koszulka - Czerwona, M"
        assert v1["product_name"] == "Koszulka"
        assert v1["permalink"] == "https://example.com/p/koszulka"
        assert v1["image_src"] == "https://example.com/koszulka.jpg"
        assert v1["prod_cost_cents"] == 2250
        assert v1["stock"] == 7

        v2 = conn.execute("SELECT * FROM variants WHERE id = 102").fetchone()
        assert v2["name"] == "Koszulka - L"
        assert v2["product_name"] == "Koszulka"
        assert v2["permalink"] == "https://example.com/p/koszulka"
        assert v2["image_src"] == "https://example.com/koszulka.jpg"
        assert v2["prod_cost_cents"] == 2250
        assert v2["stock"] == 0

    # Test resync updates existing variants that had empty fields
    with get_db() as conn:
        conn.execute("UPDATE variants SET product_name = '', image_src = NULL, prod_cost_cents = NULL, permalink = NULL WHERE id = 101")

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        res2 = client.post("/api/woocommerce/sync")
        assert res2.status_code == 200

    with get_db() as conn:
        v1_updated = conn.execute("SELECT * FROM variants WHERE id = 101").fetchone()
        assert v1_updated["product_name"] == "Koszulka"
        assert v1_updated["image_src"] == "https://example.com/koszulka.jpg"
        assert v1_updated["prod_cost_cents"] == 2250
        assert v1_updated["permalink"] == "https://example.com/p/koszulka"
