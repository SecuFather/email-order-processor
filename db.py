from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import sqlite3
from typing import Any

IntegrityError = sqlite3.IntegrityError

import config


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            system_message TEXT NOT NULL,
            tools TEXT NOT NULL,
            messages TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            tax_class INTEGER NOT NULL,
            prod_cost_cents INTEGER,
            image_src TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            permalink TEXT,
            stock_quantity INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id INTEGER,
            product_name TEXT NOT NULL DEFAULT '',
            price_cents INTEGER NOT NULL DEFAULT 0,
            tax_class INTEGER NOT NULL DEFAULT 23,
            prod_cost_cents INTEGER,
            image_src TEXT,
            permalink TEXT,
            stock INTEGER
        )
        """
    )
    var_cols = [r[1] for r in conn.execute("PRAGMA table_info(variants)").fetchall()]
    if var_cols and "parent_id" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN parent_id INTEGER")
    if var_cols and "product_name" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
    if var_cols and "price_cents" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 0")
    if var_cols and "tax_class" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN tax_class INTEGER NOT NULL DEFAULT 23")
    if var_cols and "prod_cost_cents" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN prod_cost_cents INTEGER")
    if var_cols and "image_src" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN image_src TEXT")
    if var_cols and "permalink" not in var_cols:
        conn.execute("ALTER TABLE variants ADD COLUMN permalink TEXT")
    conn.execute(
        """
        UPDATE variants
        SET parent_id = (SELECT p.id FROM products p WHERE p.name = variants.product_name LIMIT 1)
        WHERE parent_id IS NULL AND product_name != ''
        """
    )
    conn.execute(
        """
        UPDATE variants
        SET prod_cost_cents = (SELECT p.prod_cost_cents FROM products p WHERE p.id = variants.parent_id)
        WHERE prod_cost_cents IS NULL AND parent_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_maker_config (
            id INTEGER PRIMARY KEY,
            model TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            search_tool TEXT NOT NULL,
            set_request_tool TEXT NOT NULL,
            set_product_tool TEXT NOT NULL,
            search_row_template TEXT NOT NULL,
            search_empty_template TEXT NOT NULL,
            set_text_template TEXT NOT NULL,
            set_product_template TEXT NOT NULL,
            set_product_not_found_template TEXT NOT NULL,
            set_product_no_text_template TEXT NOT NULL DEFAULT 'No order text at {at}. Set order text first.',
            resolve_ambiguity_tool TEXT NOT NULL DEFAULT 'resolve_ambiguity',
            resolve_ambiguity_template TEXT NOT NULL DEFAULT 'Resolved ambiguity: chosen product is {name} (ID: {id})',
            resolve_ambiguity_none_template TEXT NOT NULL DEFAULT 'No ambiguity rule found for IDs: {ids}.'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipping_config (
            id INTEGER PRIMARY KEY,
            model TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT ''
        )
        """
    )
    cfg_cols = [r[1] for r in conn.execute("PRAGMA table_info(order_maker_config)").fetchall()]
    if cfg_cols and "set_product_no_text_template" not in cfg_cols:
        conn.execute(
            "ALTER TABLE order_maker_config ADD COLUMN set_product_no_text_template TEXT NOT NULL DEFAULT 'No order text at {at}. Set order text first.'"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ambiguity_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id_a INTEGER NOT NULL,
            product_id_b INTEGER NOT NULL,
            chosen_product_id INTEGER NOT NULL,
            UNIQUE(product_id_a, product_id_b)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_maker_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            filename TEXT,
            file_content TEXT,
            nip TEXT,
            cart TEXT NOT NULL,
            messages TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            nip TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            zip_code TEXT NOT NULL,
            city TEXT NOT NULL,
            discount REAL NOT NULL DEFAULT 0.0,
            deadline INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS company_emails (
            email TEXT PRIMARY KEY,
            nip TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shippings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nip TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            zip_code TEXT NOT NULL,
            city TEXT NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shippings_nip ON shippings(nip)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eml_text TEXT NOT NULL,
            nip TEXT,
            shipping_id INTEGER,
            date TEXT NOT NULL DEFAULT '',
            sender TEXT NOT NULL DEFAULT '',
            recipient TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            cart TEXT NOT NULL DEFAULT '{}',
            messages TEXT NOT NULL DEFAULT '[]',
            woocommerce_id INTEGER,
            fakturownia_id INTEGER,
            fakturownia_number TEXT,
            fakturownia_url TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    email_cols = [r[1] for r in conn.execute("PRAGMA table_info(emails)").fetchall()]
    if email_cols and "shipping_id" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN shipping_id INTEGER")
    if email_cols and "recipient" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN recipient TEXT NOT NULL DEFAULT ''")
    if email_cols and "notes" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
    if email_cols and "cart" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN cart TEXT NOT NULL DEFAULT '{}'")
    if email_cols and "messages" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN messages TEXT NOT NULL DEFAULT '[]'")
    if email_cols and "woocommerce_id" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN woocommerce_id INTEGER")
    if email_cols and "fakturownia_id" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN fakturownia_id INTEGER")
    if email_cols and "fakturownia_number" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN fakturownia_number TEXT")
    if email_cols and "fakturownia_url" not in email_cols:
        conn.execute("ALTER TABLE emails ADD COLUMN fakturownia_url TEXT")
    company_cols = [r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()]
    if company_cols and "discount" not in company_cols:
        conn.execute("ALTER TABLE companies ADD COLUMN discount REAL NOT NULL DEFAULT 0.0")
    if company_cols and "deadline" not in company_cols:
        conn.execute("ALTER TABLE companies ADD COLUMN deadline INTEGER NOT NULL DEFAULT 0")
    order_cols = [r[1] for r in conn.execute("PRAGMA table_info(order_maker_orders)").fetchall()]
    if order_cols and "from_email" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN from_email TEXT")
    if order_cols and "shipping_id" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN shipping_id INTEGER")
    if order_cols and "woocommerce_order_id" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN woocommerce_order_id INTEGER")
    if order_cols and "fakturownia_id" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN fakturownia_id INTEGER")
    if order_cols and "fakturownia_number" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN fakturownia_number TEXT")
    if order_cols and "fakturownia_url" not in order_cols:
        conn.execute("ALTER TABLE order_maker_orders ADD COLUMN fakturownia_url TEXT")
    return conn


def serialize_company(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "nip": row["nip"],
        "name": row["name"],
        "address": row["address"],
        "zip_code": row["zip_code"],
        "city": row["city"],
        "discount": float(row["discount"] or 0.0),
        "deadline": int(row["deadline"] or 0),
    }


def serialize_client(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "email": row["email"],
        "nip": row["nip"],
        "created_at": row["created_at"],
        "company_name": row["company_name"],
    }


def serialize_shipping(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "nip": row["nip"],
        "name": row["name"],
        "address": row["address"],
        "zip_code": row["zip_code"],
        "city": row["city"],
        "phone": row["phone"],
        "email": row["email"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "company_name": row["company_name"] if "company_name" in row.keys() else None,
    }


def serialize_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "price_cents": row["price_cents"],
        "tax_class": row["tax_class"],
        "prod_cost_cents": row["prod_cost_cents"],
        "image_src": row["image_src"],
        "active": bool(row["active"]),
        "permalink": row["permalink"],
        "stock_quantity": row["stock_quantity"],
    }


def serialize_variant(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "parent_id": row["parent_id"],
        "product_name": row["product_name"] or "",
        "price_cents": row["price_cents"] or 0,
        "tax_class": row["tax_class"] if row["tax_class"] is not None else 23,
        "prod_cost_cents": row["prod_cost_cents"],
        "image_src": row["image_src"],
        "active": bool(row["active"]) if row["active"] is not None else True,
        "permalink": row["permalink"],
        "stock": row["stock"],
        "stock_quantity": row["stock"],
    }


def serialize_thread(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "model": row["model"],
        "system_message": row["system_message"],
        "tools": row["tools"],
        "messages": json.loads(row["messages"]),
    }


# Threads
def list_threads() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM threads ORDER BY id ASC").fetchall()
    return [serialize_thread(r) for r in rows]


def create_thread(
    name: str,
    model: str,
    system_message: str,
    tools: str,
    user_message: str,
) -> dict[str, Any]:
    messages = [{"role": "user", "content": user_message}]
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO threads (name, model, system_message, tools, messages) VALUES (?, ?, ?, ?, ?)",
            (name, model, system_message, tools, json.dumps(messages)),
        )
        row = conn.execute("SELECT * FROM threads WHERE id = ?", (cur.lastrowid,)).fetchone()
    return serialize_thread(row)


def update_thread(
    thread_id: int,
    name: str,
    model: str,
    system_message: str,
    tools: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            "UPDATE threads SET name = ?, model = ?, system_message = ?, tools = ?, messages = ? WHERE id = ?",
            (name, model, system_message, tools, json.dumps(messages), thread_id),
        )
        row = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
    return serialize_thread(row)


def fork_thread(thread_id: int) -> dict[str, Any]:
    with get_db() as conn:
        orig = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
        cur = conn.execute(
            "INSERT INTO threads (name, model, system_message, tools, messages) VALUES (?, ?, ?, ?, ?)",
            (
                f"{orig['name']} (Fork)",
                orig["model"],
                orig["system_message"],
                orig["tools"],
                orig["messages"],
            ),
        )
        row = conn.execute("SELECT * FROM threads WHERE id = ?", (cur.lastrowid,)).fetchone()
    return serialize_thread(row)


def delete_thread(thread_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))


# Products
def list_products() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    return [serialize_product(r) for r in rows]


def get_active_products() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products WHERE active = 1 ORDER BY id ASC").fetchall()
    return [serialize_product(r) for r in rows]


def get_product(product_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return serialize_product(row) if row else None


def update_product(
    product_id: int,
    name: str,
    price_cents: int,
    prod_cost_cents: int | None,
    active: bool,
) -> dict[str, Any] | None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE products
            SET name = ?, price_cents = ?, prod_cost_cents = ?, active = ?
            WHERE id = ?
            """,
            (name, price_cents, prod_cost_cents, 1 if active else 0, product_id),
        )
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return serialize_product(row) if row else None


def delete_all_products() -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM variants")
        conn.execute("DELETE FROM sync_state")


# Variants
def list_variants() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                v.id,
                v.name,
                v.parent_id,
                COALESCE(NULLIF(v.product_name, ''), p.name, '') AS product_name,
                COALESCE(NULLIF(v.price_cents, 0), p.price_cents, 0) AS price_cents,
                COALESCE(v.tax_class, p.tax_class, 23) AS tax_class,
                COALESCE(v.prod_cost_cents, p.prod_cost_cents) AS prod_cost_cents,
                COALESCE(v.image_src, p.image_src) AS image_src,
                COALESCE(v.permalink, p.permalink) AS permalink,
                v.stock,
                COALESCE(p.active, 1) AS active
            FROM variants v
            LEFT JOIN products p ON p.id = v.parent_id
            ORDER BY v.id ASC
            """
        ).fetchall()
    return [serialize_variant(r) for r in rows]


def get_variant(variant_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                v.id,
                v.name,
                v.parent_id,
                COALESCE(NULLIF(v.product_name, ''), p.name, '') AS product_name,
                COALESCE(NULLIF(v.price_cents, 0), p.price_cents, 0) AS price_cents,
                COALESCE(v.tax_class, p.tax_class, 23) AS tax_class,
                COALESCE(v.prod_cost_cents, p.prod_cost_cents) AS prod_cost_cents,
                COALESCE(v.image_src, p.image_src) AS image_src,
                COALESCE(v.permalink, p.permalink) AS permalink,
                v.stock,
                COALESCE(p.active, 1) AS active
            FROM variants v
            LEFT JOIN products p ON p.id = v.parent_id
            WHERE v.id = ?
            """,
            (variant_id,),
        ).fetchone()
    return serialize_variant(row) if row else None


def update_variant(
    variant_id: int,
    name: str,
    price_cents: int = 0,
    prod_cost_cents: int | None = None,
    stock: int | None = None,
    product_name: str | None = None,
) -> dict[str, Any] | None:
    with get_db() as conn:
        if product_name is not None:
            conn.execute(
                """
                UPDATE variants
                SET name = ?, price_cents = ?, prod_cost_cents = ?, stock = ?, product_name = ?
                WHERE id = ?
                """,
                (name, price_cents, prod_cost_cents, stock, product_name, variant_id),
            )
        else:
            conn.execute(
                """
                UPDATE variants
                SET name = ?, price_cents = ?, prod_cost_cents = ?, stock = ?
                WHERE id = ?
                """,
                (name, price_cents, prod_cost_cents, stock, variant_id),
            )
    return get_variant(variant_id)


def delete_all_variants() -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM variants")


# WooCommerce Sync
def get_sync_date() -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key = 'last_sync_date'").fetchone()
    return row["value"] if row else None


def reset_sync_date() -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM sync_state WHERE key = 'last_sync_date'")


def sync_woocommerce_products(items: list[dict[str, Any]], last_sync_date: str) -> int:
    total_synced = 0
    with get_db() as conn:
        for item in items:
            prod_cost = next(
                (
                    round(float(m["value"]) * 100)
                    for m in item["meta_data"]
                    if m["key"] == "_prod_cost" and m["value"]
                ),
                None,
            )
            img = item["images"][0]["src"] if item["images"] else None
            stock = item.get("stock_quantity")
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["name"],
                    round(float(item["price"] or 0) * 100),
                    23 if not item["tax_class"] else 5,
                    prod_cost,
                    img,
                    1 if (stock or 0) > 0 else 0,
                    item.get("permalink"),
                    stock,
                ),
            )
            if cur.rowcount == 0:
                conn.execute(
                    "UPDATE products SET stock_quantity = ? WHERE id = ?",
                    (stock, item["id"]),
                )
            else:
                total_synced += cur.rowcount

        conn.execute(
            """
            INSERT INTO sync_state (key, value) VALUES ('last_sync_date', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (last_sync_date,),
        )
    return total_synced


def sync_woocommerce_variants(items: list[dict[str, Any]]) -> int:
    total_synced = 0
    with get_db() as conn:
        for item in items:
            stock = item.get("stock")
            conn.execute(
                """
                INSERT INTO variants (id, name, parent_id, product_name, price_cents, tax_class, prod_cost_cents, image_src, permalink, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    stock = excluded.stock,
                    parent_id = excluded.parent_id,
                    product_name = excluded.product_name,
                    image_src = excluded.image_src,
                    permalink = excluded.permalink,
                    prod_cost_cents = excluded.prod_cost_cents,
                    tax_class = excluded.tax_class,
                    name = CASE WHEN variants.name = '' OR variants.name IS NULL THEN excluded.name ELSE variants.name END,
                    price_cents = CASE WHEN variants.price_cents = 0 OR variants.price_cents IS NULL THEN excluded.price_cents ELSE variants.price_cents END
                """,
                (
                    item["id"],
                    item["name"],
                    item.get("parent_id"),
                    item.get("product_name", ""),
                    item.get("price_cents", 0),
                    item.get("tax_class", 23),
                    item.get("prod_cost_cents"),
                    item.get("image_src"),
                    item.get("permalink"),
                    stock,
                ),
            )
            total_synced += 1
    return total_synced


# Order Maker Config
def get_order_maker_config() -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM order_maker_config WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_order_maker_config(config_dict: dict[str, Any]) -> None:
    cols = list(config_dict.keys())
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols)
    with get_db() as conn:
        conn.execute(
            f"INSERT INTO order_maker_config (id, {', '.join(cols)}) VALUES (1, {placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            tuple(config_dict[c] for c in cols),
        )


# Shipping Config
def get_shipping_config() -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM shipping_config WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_shipping_config(config_dict: dict[str, Any]) -> None:
    cols = list(config_dict.keys())
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols)
    with get_db() as conn:
        conn.execute(
            f"INSERT INTO shipping_config (id, {', '.join(cols)}) VALUES (1, {placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            tuple(config_dict[c] for c in cols),
        )



# Ambiguity Pairs
def list_ambiguity_pairs() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.product_id_a, p.product_id_b, p.chosen_product_id,
                   pa.name as name_a, pb.name as name_b, pc.name as chosen_name
            FROM ambiguity_pairs p
            LEFT JOIN products pa ON pa.id = p.product_id_a
            LEFT JOIN products pb ON pb.id = p.product_id_b
            LEFT JOIN products pc ON pc.id = p.chosen_product_id
            ORDER BY p.id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def create_ambiguity_pair(
    product_id_a: int,
    product_id_b: int,
    chosen_product_id: int,
) -> None:
    a = min(product_id_a, product_id_b)
    b = max(product_id_a, product_id_b)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO ambiguity_pairs (product_id_a, product_id_b, chosen_product_id)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id_a, product_id_b) DO UPDATE SET
                chosen_product_id = excluded.chosen_product_id
            """,
            (a, b, chosen_product_id),
        )


def delete_ambiguity_pair(pair_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM ambiguity_pairs WHERE id = ?", (pair_id,))


def find_ambiguity_choice(ids: list[int]) -> dict[str, Any] | None:
    if len(ids) < 2:
        return None
    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        row = conn.execute(
            f"""
            SELECT p.*
            FROM ambiguity_pairs ap
            JOIN products p ON p.id = ap.chosen_product_id
            WHERE ap.product_id_a IN ({placeholders})
              AND ap.product_id_b IN ({placeholders})
            LIMIT 1
            """,
            (*ids, *ids),
        ).fetchone()
    return dict(row) if row else None


# Order Maker Orders
def save_order(
    order_id: int | None,
    name: str | None,
    filename: str | None,
    cart: dict[str, Any],
    messages: list[dict[str, Any]],
    now: str,
) -> int:
    with get_db() as conn:
        if order_id:
            conn.execute(
                """
                UPDATE order_maker_orders
                SET cart = ?, messages = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(cart), json.dumps(messages), now, order_id),
            )
            return order_id
        order_name = name or (f"Order: {filename}" if filename else f"Order {now[:16]}")
        cur = conn.execute(
            """
            INSERT INTO order_maker_orders (name, filename, cart, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (order_name, filename, json.dumps(cart), json.dumps(messages), now, now),
        )
        return cur.lastrowid


def list_order_maker_orders() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, filename, created_at, updated_at, woocommerce_order_id, fakturownia_id, fakturownia_number, fakturownia_url FROM order_maker_orders ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_order_maker_order(order_id: int, fallback_sender_email: str | None = None) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM order_maker_orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row:
            return None
        sender_email = row["from_email"] or fallback_sender_email
        linked_row = (
            conn.execute("SELECT nip FROM company_emails WHERE email = ?", (sender_email,)).fetchone()
            if sender_email
            else None
        )
        company_row = (
            conn.execute("SELECT * FROM companies WHERE nip = ?", (row["nip"],)).fetchone()
            if row["nip"]
            else None
        )
        shipping_id = row["shipping_id"]
        shipping_row = (
            conn.execute("SELECT * FROM shippings WHERE id = ?", (shipping_id,)).fetchone()
            if shipping_id
            else None
        )
    return {
        "id": row["id"],
        "name": row["name"],
        "filename": row["filename"],
        "file_content": row["file_content"],
        "nip": row["nip"],
        "from_email": sender_email,
        "is_connected": bool(linked_row and row["nip"] == linked_row["nip"]),
        "company": serialize_company(company_row) if company_row else None,
        "shipping_id": shipping_id,
        "shipping": serialize_shipping(shipping_row) if shipping_row else None,
        "woocommerce_order_id": row["woocommerce_order_id"],
        "fakturownia_id": row["fakturownia_id"],
        "fakturownia_number": row["fakturownia_number"],
        "fakturownia_url": row["fakturownia_url"],
        "cart": json.loads(row["cart"]),
        "messages": json.loads(row["messages"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_order_maker_order(
    name: str,
    filename: str,
    file_content: str,
    nip: str | None,
    from_email: str | None,
    now: str,
) -> dict[str, Any]:
    with get_db() as conn:
        linked_row = (
            conn.execute("SELECT nip FROM company_emails WHERE email = ?", (from_email,)).fetchone()
            if from_email
            else None
        )
        cur = conn.execute(
            """
            INSERT INTO order_maker_orders (name, filename, file_content, nip, from_email, cart, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, '{}', '[]', ?, ?)
            """,
            (name, filename, file_content, nip, from_email, now, now),
        )
        company_row = (
            conn.execute("SELECT * FROM companies WHERE nip = ?", (nip,)).fetchone()
            if nip
            else None
        )
    return {
        "id": cur.lastrowid,
        "nip": nip,
        "from_email": from_email,
        "is_connected": bool(linked_row and nip == linked_row["nip"]),
        "company": serialize_company(company_row) if company_row else None,
    }


def update_order_maker_order(
    order_id: int,
    cart: dict[str, Any] | None,
    filename: str | None,
    file_content: str | None,
    from_email: str | None,
    nip: str | None,
    updated_at: str,
) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE order_maker_orders
            SET cart = COALESCE(?, cart),
                filename = COALESCE(?, filename),
                file_content = COALESCE(?, file_content),
                from_email = CASE WHEN ? IS NOT NULL THEN ? ELSE from_email END,
                nip = CASE WHEN ? IS NOT NULL THEN ? ELSE nip END,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(cart) if cart is not None else None,
                filename,
                file_content,
                file_content,
                from_email,
                file_content,
                nip,
                updated_at,
                order_id,
            ),
        )
        updated = conn.execute(
            "SELECT nip, from_email FROM order_maker_orders WHERE id = ?", (order_id,)
        ).fetchone()
        effective_nip = updated["nip"] if updated else None
        effective_email = updated["from_email"] if updated else None
        company_row = (
            conn.execute("SELECT * FROM companies WHERE nip = ?", (effective_nip,)).fetchone()
            if effective_nip
            else None
        )
        linked_row = (
            conn.execute("SELECT nip FROM company_emails WHERE email = ?", (effective_email,)).fetchone()
            if effective_email
            else None
        )
    return {
        "ok": True,
        "nip": effective_nip,
        "from_email": effective_email,
        "is_connected": bool(linked_row and effective_nip == linked_row["nip"]),
        "company": serialize_company(company_row) if company_row else None,
    }


def delete_order_maker_order(order_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM order_maker_orders WHERE id = ?", (order_id,))


# Companies & Emails
def list_companies() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM companies ORDER BY name ASC, nip ASC").fetchall()
    return [serialize_company(r) for r in rows]


def get_company(nip: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM companies WHERE nip = ?", (nip,)).fetchone()
    return serialize_company(row) if row else None


def create_company(
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    discount: float,
    deadline: int,
    now: str,
) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO companies (nip, name, address, zip_code, city, discount, deadline, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nip, name, address, zip_code, city, discount, deadline, now, now),
        )
        row = conn.execute("SELECT * FROM companies WHERE nip = ?", (nip,)).fetchone()
    return serialize_company(row)


def update_company(
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    discount: float,
    deadline: int,
    now: str,
) -> dict[str, Any] | None:
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE companies
            SET name = ?, address = ?, zip_code = ?, city = ?, discount = ?, deadline = ?, updated_at = ?
            WHERE nip = ?
            """,
            (name, address, zip_code, city, discount, deadline, now, nip),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM companies WHERE nip = ?", (nip,)).fetchone()
    return serialize_company(row)


def delete_company(nip: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM companies WHERE nip = ?", (nip,))


def save_company_info(
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    order_id: int | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO companies (nip, name, address, zip_code, city, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nip) DO UPDATE SET
                name = excluded.name,
                address = excluded.address,
                zip_code = excluded.zip_code,
                city = excluded.city,
                updated_at = excluded.updated_at
            """,
            (nip, name, address, zip_code, city, now, now),
        )
        if order_id:
            conn.execute(
                "UPDATE order_maker_orders SET nip = ?, updated_at = ? WHERE id = ?",
                (nip, now, order_id),
            )


def get_nip_by_email(email: str) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT nip FROM company_emails WHERE email = ?", (email,)).fetchone()
    return row["nip"] if row else None


def connect_company_email(
    email: str,
    nip: str,
    order_id: int | None,
    now: str,
) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO company_emails (email, nip, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET nip = excluded.nip
            """,
            (email, nip, now),
        )
        if order_id:
            conn.execute(
                "UPDATE order_maker_orders SET nip = ?, from_email = ?, updated_at = ? WHERE id = ?",
                (nip, email, now, order_id),
            )
        company_row = conn.execute("SELECT * FROM companies WHERE nip = ?", (nip,)).fetchone()
    return {
        "ok": True,
        "email": email,
        "nip": nip,
        "is_connected": True,
        "company": serialize_company(company_row) if company_row else None,
    }


def disconnect_company_email(email: str, order_id: int | None, now: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM company_emails WHERE email = ?", (email,))
        if order_id:
            conn.execute(
                "UPDATE order_maker_orders SET nip = NULL, updated_at = ? WHERE id = ?",
                (now, order_id),
            )


def list_clients(nip: str | None = None) -> list[dict[str, Any]]:
    with get_db() as conn:
        if nip:
            rows = conn.execute(
                """
                SELECT ce.email, ce.nip, ce.created_at, c.name AS company_name
                FROM company_emails ce
                LEFT JOIN companies c ON ce.nip = c.nip
                WHERE ce.nip = ?
                ORDER BY ce.created_at DESC, ce.email ASC
                """,
                (nip,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT ce.email, ce.nip, ce.created_at, c.name AS company_name
                FROM company_emails ce
                LEFT JOIN companies c ON ce.nip = c.nip
                ORDER BY ce.created_at DESC, ce.email ASC
                """
            ).fetchall()
    return [serialize_client(r) for r in rows]


def create_client(email: str, nip: str, now: str) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO company_emails (email, nip, created_at) VALUES (?, ?, ?)",
            (email, nip, now),
        )
        row = conn.execute(
            """
            SELECT ce.email, ce.nip, ce.created_at, c.name AS company_name
            FROM company_emails ce
            LEFT JOIN companies c ON ce.nip = c.nip
            WHERE ce.email = ?
            """,
            (email,),
        ).fetchone()
    return serialize_client(row)


def update_client(old_email: str, new_email: str, nip: str) -> dict[str, Any] | None:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE company_emails SET email = ?, nip = ? WHERE email = ?",
            (new_email, nip, old_email),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            """
            SELECT ce.email, ce.nip, ce.created_at, c.name AS company_name
            FROM company_emails ce
            LEFT JOIN companies c ON ce.nip = c.nip
            WHERE ce.email = ?
            """,
            (new_email,),
        ).fetchone()
    return serialize_client(row)


def delete_client(email: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM company_emails WHERE email = ?", (email,))


# Shippings
def list_shippings(nip: str | None = None) -> list[dict[str, Any]]:
    with get_db() as conn:
        if nip:
            rows = conn.execute(
                """
                SELECT s.*, c.name AS company_name
                FROM shippings s
                LEFT JOIN companies c ON s.nip = c.nip
                WHERE s.nip = ?
                ORDER BY s.name ASC, s.id DESC
                """,
                (nip,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.*, c.name AS company_name
                FROM shippings s
                LEFT JOIN companies c ON s.nip = c.nip
                ORDER BY s.name ASC, s.id DESC
                """
            ).fetchall()
    return [serialize_shipping(r) for r in rows]


def get_shipping(shipping_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT s.*, c.name AS company_name
            FROM shippings s
            LEFT JOIN companies c ON s.nip = c.nip
            WHERE s.id = ?
            """,
            (shipping_id,),
        ).fetchone()
    return serialize_shipping(row) if row else None


def create_shipping(
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    phone: str,
    email: str,
    now: str,
) -> dict[str, Any]:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO shippings (nip, name, address, zip_code, city, phone, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nip, name, address, zip_code, city, phone, email, now, now),
        )
        row = conn.execute(
            """
            SELECT s.*, c.name AS company_name
            FROM shippings s
            LEFT JOIN companies c ON s.nip = c.nip
            WHERE s.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
    return serialize_shipping(row)


def update_shipping(
    shipping_id: int,
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    phone: str,
    email: str,
    now: str,
) -> dict[str, Any] | None:
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE shippings
            SET nip = ?, name = ?, address = ?, zip_code = ?, city = ?, phone = ?, email = ?, updated_at = ?
            WHERE id = ?
            """,
            (nip, name, address, zip_code, city, phone, email, now, shipping_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            """
            SELECT s.*, c.name AS company_name
            FROM shippings s
            LEFT JOIN companies c ON s.nip = c.nip
            WHERE s.id = ?
            """,
            (shipping_id,),
        ).fetchone()
    return serialize_shipping(row)


def delete_shipping(shipping_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE order_maker_orders SET shipping_id = NULL WHERE shipping_id = ?", (shipping_id,))
        conn.execute("UPDATE emails SET shipping_id = NULL WHERE shipping_id = ?", (shipping_id,))
        conn.execute("DELETE FROM shippings WHERE id = ?", (shipping_id,))


def save_shipping_info(
    nip: str,
    name: str,
    address: str,
    zip_code: str,
    city: str,
    phone: str,
    email: str,
    order_id: int | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO shippings (nip, name, address, zip_code, city, phone, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nip, name, address, zip_code, city, phone, email, now, now),
        )
        shipping_id = cur.lastrowid
        if order_id:
            conn.execute(
                "UPDATE order_maker_orders SET shipping_id = ?, updated_at = ? WHERE id = ?",
                (shipping_id, now, order_id),
            )
        row = conn.execute(
            """
            SELECT s.*, c.name AS company_name
            FROM shippings s
            LEFT JOIN companies c ON s.nip = c.nip
            WHERE s.id = ?
            """,
            (shipping_id,),
        ).fetchone()
    return serialize_shipping(row)


def connect_order_shipping(order_id: int, shipping_id: int, now: str) -> dict[str, Any]:
    with get_db() as conn:
        conn.execute(
            "UPDATE order_maker_orders SET shipping_id = ?, updated_at = ? WHERE id = ?",
            (shipping_id, now, order_id),
        )
        shipping_row = conn.execute("SELECT * FROM shippings WHERE id = ?", (shipping_id,)).fetchone()
    return {
        "ok": True,
        "shipping_id": shipping_id,
        "shipping": serialize_shipping(shipping_row) if shipping_row else None,
    }


def disconnect_order_shipping(order_id: int, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE order_maker_orders SET shipping_id = NULL, updated_at = ? WHERE id = ?",
            (now, order_id),
        )


def set_order_woocommerce_id(order_id: int, woocommerce_order_id: int, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE order_maker_orders SET woocommerce_order_id = ?, updated_at = ? WHERE id = ?",
            (woocommerce_order_id, now, order_id),
        )


def set_order_fakturownia_invoice(order_id: int, fakturownia_id: int, number: str, url: str, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE order_maker_orders SET fakturownia_id = ?, fakturownia_number = ?, fakturownia_url = ?, updated_at = ? WHERE id = ?",
            (fakturownia_id, number, url, now, order_id),
        )


# Emails
EMAIL_SELECT_SQL = """
    SELECT e.id, e.nip, e.shipping_id, e.date, e.sender, e.recipient, e.title, e.notes, e.woocommerce_id,
           e.fakturownia_id, e.fakturownia_number, e.fakturownia_url, e.created_at,
           c.name AS company_name, c.discount AS company_discount, s.name AS shipping_name
    FROM emails e
    LEFT JOIN companies c ON e.nip = c.nip
    LEFT JOIN shippings s ON e.shipping_id = s.id
"""


def serialize_email_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "nip": row["nip"],
        "company_name": row["company_name"],
        "company_discount": float(row["company_discount"] or 0.0),
        "shipping_id": row["shipping_id"],
        "shipping_name": row["shipping_name"],
        "woocommerce_id": row["woocommerce_id"],
        "fakturownia_id": row["fakturownia_id"],
        "fakturownia_number": row["fakturownia_number"],
        "fakturownia_url": row["fakturownia_url"],
        "date": row["date"],
        "sender": row["sender"],
        "recipient": row["recipient"],
        "title": row["title"],
        "notes": row["notes"],
        "created_at": row["created_at"],
    }


def list_emails() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(EMAIL_SELECT_SQL).fetchall()
    rows.sort(
        key=lambda r: (
            parsedate_to_datetime(r["date"]).timestamp() if r["date"] else 0.0,
            r["id"],
        ),
        reverse=True,
    )
    return [serialize_email_summary(r) for r in rows]


def get_email(email_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT e.*, c.name AS company_name, c.discount AS company_discount, s.name AS shipping_name
            FROM emails e
            LEFT JOIN companies c ON e.nip = c.nip
            LEFT JOIN shippings s ON e.shipping_id = s.id
            WHERE e.id = ?
            """,
            (email_id,),
        ).fetchone()
    if not row:
        return None
    return {
        **serialize_email_summary(row),
        "eml_text": row["eml_text"],
        "cart": json.loads(row["cart"]),
        "messages": json.loads(row["messages"]),
    }


def save_email_order(
    email_id: int,
    cart: dict[str, Any],
    messages: list[dict[str, Any]],
) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE emails SET cart = ?, messages = ? WHERE id = ?",
            (json.dumps(cart), json.dumps(messages), email_id),
        )


def create_email(
    eml_text: str,
    nip: str | None,
    date: str,
    sender: str,
    recipient: str,
    title: str,
    now: str,
) -> dict[str, Any]:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO emails (eml_text, nip, shipping_id, date, sender, recipient, title, created_at)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (eml_text, nip, date, sender, recipient, title, now),
        )
        row = conn.execute(
            f"{EMAIL_SELECT_SQL} WHERE e.id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return serialize_email_summary(row)


def set_email_woocommerce_id(email_id: int, woocommerce_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE emails SET woocommerce_id = ? WHERE id = ?",
            (woocommerce_id, email_id),
        )


def set_email_fakturownia_invoice(email_id: int, fakturownia_id: int, number: str, url: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE emails SET fakturownia_id = ?, fakturownia_number = ?, fakturownia_url = ? WHERE id = ?",
            (fakturownia_id, number, url, email_id),
        )


def update_email(
    email_id: int,
    nip: str | None = None,
    shipping_id: int | None = None,
    notes: str = "",
    woocommerce_id: int | None = None,
    update_nip: bool = False,
    update_shipping: bool = False,
    update_notes: bool = False,
    update_woocommerce_id: bool = False,
) -> dict[str, Any] | None:
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE emails
            SET nip = CASE WHEN ? THEN ? ELSE nip END,
                shipping_id = CASE WHEN ? THEN ? ELSE shipping_id END,
                notes = CASE WHEN ? THEN ? ELSE notes END,
                woocommerce_id = CASE WHEN ? THEN ? ELSE woocommerce_id END
            WHERE id = ?
            """,
            (
                1 if update_nip else 0,
                nip,
                1 if update_shipping else 0,
                shipping_id,
                1 if update_notes else 0,
                notes,
                1 if update_woocommerce_id else 0,
                woocommerce_id,
                email_id,
            ),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            f"{EMAIL_SELECT_SQL} WHERE e.id = ?",
            (email_id,),
        ).fetchone()
    return serialize_email_summary(row)


