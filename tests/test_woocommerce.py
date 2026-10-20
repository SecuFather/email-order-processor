import asyncio
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


def test_sync_products_mapping_and_insert_only():
    mock_products = [
        {
            "id": 8518,
            "name": "Wielka księga różnic",
            "price": "99.99",
            "tax_class": "obnizona-stawka",
            "date_modified": "2026-10-20T11:00:00",
            "stock_quantity": 5,
            "permalink": "https://example.com/p/8518",
            "meta_data": [
                {"id": 1, "key": "_some_key", "value": "xyz"},
                {"id": 2, "key": "_prod_cost", "value": "11.85"},
            ],
            "images": [{"src": "https://example.com/img1.jpg"}],
        },
        {
            "id": 9000,
            "name": "Standard Book",
            "price": "50.00",
            "tax_class": "",
            "date_modified": "2026-10-20T12:00:00",
            "stock_quantity": 0,
            "meta_data": [],
            "images": [],
        },
    ]

    def mock_get(url, auth, params):
        assert auth == ("ck_test", "cs_test")
        assert params == {
            "per_page": 100,
            "orderby": "modified",
            "order": "asc",
        }
        return httpx.Response(200, json=mock_products, request=httpx.Request("GET", url))

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        res = client.post("/api/woocommerce/sync")
        assert res.status_code == 200
        data = res.json()
        assert data == {
            "last_sync_date": "2026-10-20T12:00:00",
            "synced_count": 2,
            "has_more": False,
        }

    with get_db() as conn:
        p1 = conn.execute("SELECT * FROM products WHERE id = 8518").fetchone()
        assert p1["name"] == "Wielka księga różnic"
        assert p1["price_cents"] == 9999
        assert p1["tax_class"] == 5
        assert p1["prod_cost_cents"] == 1185
        assert p1["image_src"] == "https://example.com/img1.jpg"
        assert p1["active"] == 1
        assert p1["stock_quantity"] == 5
        assert p1["permalink"] == "https://example.com/p/8518"

        p2 = conn.execute("SELECT * FROM products WHERE id = 9000").fetchone()
        assert p2["name"] == "Standard Book"
        assert p2["price_cents"] == 5000
        assert p2["tax_class"] == 23
        assert p2["prod_cost_cents"] is None
        assert p2["image_src"] is None
        assert p2["active"] == 0
        assert p2["stock_quantity"] == 0

        conn.execute("UPDATE products SET name = 'Manually Edited Name' WHERE id = 8518")

    # Second sync: WooCommerce returns updated price, name, and stock for product 8518
    updated_remote = [
        {
            "id": 8518,
            "name": "Remote Changed Name",
            "price": "120.00",
            "tax_class": "",
            "date_modified": "2026-10-20T15:30:00",
            "stock_quantity": 42,
            "meta_data": [],
            "images": [],
        }
    ]

    def mock_get_second(url, auth, params):
        assert params["modified_after"] == "2026-10-20T12:00:00"
        return httpx.Response(200, json=updated_remote, request=httpx.Request("GET", url))

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get_second):
        res2 = client.post("/api/woocommerce/sync")
        assert res2.status_code == 200
        assert res2.json() == {
            "last_sync_date": "2026-10-20T15:30:00",
            "synced_count": 0,
            "has_more": False,
        }

    with get_db() as conn:
        p1_after = conn.execute("SELECT * FROM products WHERE id = 8518").fetchone()
        assert p1_after["name"] == "Manually Edited Name"
        assert p1_after["price_cents"] == 9999
        assert p1_after["stock_quantity"] == 42


def test_sync_batches_of_100_advances_last_sync_date():
    batch1 = [
        {
            "id": i,
            "name": f"P{i}",
            "price": "10.00",
            "tax_class": "",
            "date_modified": f"2026-10-20T10:00:{i - 1:02d}" if i < 60 else "2026-10-20T10:01:00",
            "meta_data": [],
            "images": [],
        }
        for i in range(1, 101)
    ]
    batch2 = [
        {
            "id": i,
            "name": f"P{i}",
            "price": "10.00",
            "tax_class": "",
            "date_modified": "2026-10-20T11:00:00",
            "meta_data": [],
            "images": [],
        }
        for i in range(101, 201)
    ]
    batch3 = [
        {
            "id": i,
            "name": f"P{i}",
            "price": "10.00",
            "tax_class": "",
            "date_modified": "2026-10-20T12:00:00",
            "meta_data": [],
            "images": [],
        }
        for i in range(201, 214)
    ]

    def mock_get(url, auth, params):
        assert params["per_page"] == 100
        assert params["orderby"] == "modified"
        assert params["order"] == "asc"
        modified_after = params.get("modified_after")
        if modified_after is None:
            return httpx.Response(200, json=batch1, request=httpx.Request("GET", url))
        if modified_after == "2026-10-20T10:01:00":
            return httpx.Response(200, json=batch2, request=httpx.Request("GET", url))
        if modified_after == "2026-10-20T11:00:00":
            return httpx.Response(200, json=batch3, request=httpx.Request("GET", url))
        raise AssertionError(f"Unexpected modified_after: {modified_after}")

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        r1 = client.post("/api/woocommerce/sync")
        assert r1.status_code == 200
        assert r1.json() == {
            "last_sync_date": "2026-10-20T10:01:00",
            "synced_count": 100,
            "has_more": True,
        }

        r2 = client.post("/api/woocommerce/sync")
        assert r2.status_code == 200
        assert r2.json() == {
            "last_sync_date": "2026-10-20T11:00:00",
            "synced_count": 100,
            "has_more": True,
        }

        r3 = client.post("/api/woocommerce/sync")
        assert r3.status_code == 200
        assert r3.json() == {
            "last_sync_date": "2026-10-20T12:00:00",
            "synced_count": 13,
            "has_more": False,
        }

        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            assert count == 213


def test_sync_lock_queueing():
    async def run_syncs():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res1, res2 = await asyncio.gather(
                ac.post("/api/woocommerce/sync"),
                ac.post("/api/woocommerce/sync"),
            )
            return res1, res2

    def mock_get(url, auth, params):
        return httpx.Response(200, json=[], request=httpx.Request("GET", url))

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        res1, res2 = asyncio.run(run_syncs())
        assert res1.status_code == 200
        assert res2.status_code == 200


def test_reset_sync():
    with get_db() as conn:
        conn.execute("INSERT INTO sync_state (key, value) VALUES ('last_sync_date', '2026-10-20T10:00:00')")

    res = client.post("/api/woocommerce/reset-sync")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    with get_db() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key = 'last_sync_date'").fetchone()
        assert row is None
