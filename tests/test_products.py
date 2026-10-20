import pytest
from fastapi.testclient import TestClient

import config
from api import app
from db import get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))


def test_products_list_and_update():
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (101, 'Book A', 4999, 5, 1200, 'https://example.com/a.jpg', 1, 'https://store.com/p/book-a', 15)
            """
        )
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src)
            VALUES (102, 'Book B', 2500, 23, NULL, NULL)
            """
        )

    # 1. Test GET /api/products
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()["products"]
    assert len(products) == 2

    p1 = products[0]
    assert p1["id"] == 101
    assert p1["name"] == "Book A"
    assert p1["price_cents"] == 4999
    assert p1["tax_class"] == 5
    assert p1["prod_cost_cents"] == 1200
    assert p1["image_src"] == "https://example.com/a.jpg"
    assert p1["active"] is True
    assert p1["permalink"] == "https://store.com/p/book-a"
    assert p1["stock_quantity"] == 15

    p2 = products[1]
    assert p2["id"] == 102
    assert p2["name"] == "Book B"
    assert p2["price_cents"] == 2500
    assert p2["tax_class"] == 23
    assert p2["prod_cost_cents"] is None
    assert p2["image_src"] is None
    assert p2["active"] is True  # defaulted to True
    assert p2["permalink"] is None
    assert p2["stock_quantity"] is None

    # 2. Test PUT /api/products/{id} to update name, price, cost, active
    res_upd = client.put(
        "/api/products/101",
        json={
            "name": "Book A - Updated Edition",
            "price_cents": 5999,
            "prod_cost_cents": 1500,
            "active": False,
        },
    )
    assert res_upd.status_code == 200
    updated = res_upd.json()
    assert updated["id"] == 101
    assert updated["name"] == "Book A - Updated Edition"
    assert updated["price_cents"] == 5999
    assert updated["prod_cost_cents"] == 1500
    assert updated["active"] is False
    # Ensure unchangeable params were NOT changed
    assert updated["stock_quantity"] == 15
    assert updated["tax_class"] == 5
    assert updated["image_src"] == "https://example.com/a.jpg"
    assert updated["permalink"] == "https://store.com/p/book-a"


def test_delete_all_products():
    with get_db() as conn:
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class) VALUES (1, 'Test', 100, 23)")
        conn.execute("INSERT INTO sync_state (key, value) VALUES ('last_sync_date', '2026-01-01')")

    res = client.delete("/api/products")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        assert count == 0
        sync_row = conn.execute("SELECT value FROM sync_state WHERE key = 'last_sync_date'").fetchone()
        assert sync_row is None


def test_search_products_algorithm_and_active_filter():
    with get_db() as conn:
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class, active) VALUES (1, 'Wielka księga różnic', 1000, 23, 1)")
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class, active) VALUES (2, 'Wielka księga bajek', 1000, 23, 1)")
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class, active) VALUES (3, 'Wielka encyklopedia', 1000, 23, 1)")
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class, active) VALUES (4, 'Wielka księga różnic - Inactive', 1000, 23, 0)")
        conn.execute("INSERT INTO products (id, name, price_cents, tax_class, active) VALUES (5, 'Zupełnie inny produkt', 1000, 23, 1)")

    # All 3 words match product 1; 2 words match product 2; 1 word matches product 3. Product 4 is inactive.
    res = client.get("/api/products/search", params={"phrase": "Wielka księga różnic", "limit": 3, "page": 1})
    assert res.status_code == 200
    products = res.json()["products"]
    assert [(p["id"], p["not_matching_words"]) for p in products] == [(1, 0), (2, 1), (3, 2)]

    # Pagination works without seeing duplicate items
    res_page1 = client.get("/api/products/search", params={"phrase": "Wielka księga różnic", "limit": 2, "page": 1})
    assert res_page1.status_code == 200
    assert [p["id"] for p in res_page1.json()["products"]] == [1, 2]

    res_page2 = client.get("/api/products/search", params={"phrase": "Wielka księga różnic", "limit": 2, "page": 2})
    assert res_page2.status_code == 200
    assert [p["id"] for p in res_page2.json()["products"]] == [3]

    res_page3 = client.get("/api/products/search", params={"phrase": "Wielka księga różnic", "limit": 2, "page": 3})
    assert res_page3.status_code == 200
    assert res_page3.json()["products"] == []

    # Substring matching works
    res_sub = client.get("/api/products/search", params={"phrase": "encyklo", "limit": 5, "page": 1})
    assert res_sub.status_code == 200
    assert [p["id"] for p in res_sub.json()["products"]] == [3]

    # Empty phrase or words shorter than 4 chars without digits produce empty result
    res_empty = client.get("/api/products/search", params={"phrase": "a b c", "limit": 5, "page": 1})
    assert res_empty.status_code == 200
    assert res_empty.json()["products"] == []

    # Limit and page are mandatory from API perspective
    assert client.get("/api/products/search", params={"phrase": "Wielka", "page": 1}).status_code == 422
    assert client.get("/api/products/search", params={"phrase": "Wielka", "limit": 10}).status_code == 422
