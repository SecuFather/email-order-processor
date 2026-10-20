import base64
from email.message import EmailMessage
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import openpyxl

import config
import db
from api import app
from db import get_db
from llm import parse_tools
from main import md

client = TestClient(app)


def test_parse_eml():
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Invoice and Report Attached"
    msg["Date"] = "Tue, 20 Oct 2026 14:00:00 +0200"
    msg.set_content(
        '<p>Please find the files attached and see <a href="https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOp/edit?usp=sharing">Sheet</a>.</p>',
        subtype="html",
    )
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    msg.add_attachment(
        pdf_bytes, maintype="application", subtype="pdf", filename="invoice.pdf"
    )
    png_bytes = b"\x89PNG\r\n\x1a\nfake png content"
    msg.add_attachment(
        png_bytes, maintype="image", subtype="png", filename="diagram.png"
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Product", "Revenue"])
    ws.append(["Widget", 1200])
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    msg.add_attachment(
        xlsx_buf.getvalue(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="report.xlsx",
    )

    res = client.post(
        "/api/parse-eml",
        files={"file": ("invoice.eml", msg.as_bytes(), "message/rfc822")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["subject"] == "Invoice and Report Attached"
    assert data["from"] == "sender@example.com"
    assert data["to"] == "recipient@example.com"
    assert "Please find the files attached" in data["html"]
    assert len(data["attachments"]) == 4
    assert data["attachments"][0]["filename"] == "invoice.pdf"
    assert data["attachments"][0]["content_type"] == "application/pdf"
    assert base64.b64decode(data["attachments"][0]["data"]) == pdf_bytes
    assert data["attachments"][1]["filename"] == "diagram.png"
    assert data["attachments"][1]["content_type"] == "image/png"
    assert base64.b64decode(data["attachments"][1]["data"]) == png_bytes
    assert data["attachments"][2]["filename"] == "report.xlsx"
    assert "Widget" in data["attachments"][2]["markdown"]
    assert "1200" in data["attachments"][2]["markdown"]
    assert data["attachments"][3]["filename"] == "Google Spreadsheets (1AbCdEfG)"
    assert (
        data["attachments"][3]["url"]
        == "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOp/preview"
    )


def test_convert_eml():
    eml_bytes = (
        b"From: sender@example.com\r\n"
        b"To: recipient@example.com\r\n"
        b"Subject: Meeting Notes\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Hello team, here are the notes."
    )
    res = client.post(
        "/api/convert-eml",
        files={"file": ("sample.eml", eml_bytes, "message/rfc822")},
    )
    assert res.status_code == 200
    md_text = res.json()["markdown"]
    assert "Meeting Notes" in md_text
    assert "Hello team, here are the notes." in md_text


def test_convert_eml_with_eml_attachment():
    inner = EmailMessage()
    inner["From"] = "inner@example.com"
    inner["Subject"] = "Inner Subject"
    inner.set_content("Inner attachment body content.")

    outer = EmailMessage()
    outer["From"] = "outer@example.com"
    outer["Subject"] = "Outer Subject"
    outer.set_content("Outer body text.")
    outer.add_attachment(inner, filename="attached_message.eml")

    res = client.post(
        "/api/convert-eml",
        files={"file": ("outer.eml", outer.as_bytes(), "message/rfc822")},
    )
    assert res.status_code == 200
    md_text = res.json()["markdown"]
    assert "Outer Subject" in md_text
    assert "Outer body text." in md_text
    assert "Inner Subject" in md_text
    assert "Inner attachment body content." in md_text


def test_convert_eml_deduplicates_google_docs():
    doc_url = "https://docs.google.com/document/d/1DocIdXyz/edit"
    eml_bytes = (
        b"From: sender@example.com\r\n"
        b"To: recipient@example.com\r\n"
        b"Subject: Thread\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        + f"First message: {doc_url}\nReply quoting: {doc_url}".encode()
    )

    orig_convert = md.convert

    def side_effect(source, **kwargs):
        if str(source).startswith("https://docs.google.com/"):
            return MagicMock(text_content="Fetched Google Doc Content")
        return orig_convert(source, **kwargs)

    with patch.object(md, "convert", side_effect=side_effect) as mock_convert:
        res = client.post(
            "/api/convert-eml",
            files={"file": ("thread.eml", eml_bytes, "message/rfc822")},
        )
        assert res.status_code == 200
        md_text = res.json()["markdown"]
        assert md_text.count("## Google Document (1DocIdXyz)") == 1
        assert md_text.count("Fetched Google Doc Content") == 1
        assert mock_convert.call_count == 2


def test_normalize():
    res = client.post(
        "/api/normalize",
        json={"text": "Zażółć gęślą jaźń! Cat on a1 #42 and 3d dog."},
    )
    assert res.status_code == 200
    assert res.json()["normalized"] == "zazolc gesla jazn a1 42 3d"


def test_parse_tools():
    sys_msg = """
You are an assistant.

def get_weather(city: str, days: int, tags: list):
    pass

def internal_helper(x: int):
    return x
"""
    tools = parse_tools(sys_msg, "get_weather")
    assert tools == [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "days": {"type": "integer"},
                        "tags": {"type": "array"},
                    },
                    "required": ["city", "days", "tags"],
                },
            },
        }
    ]
    assert "description" not in tools[0]["function"]


def test_threads_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test_threads.db"))

    fake_msg_1 = MagicMock()
    fake_msg_1.model_dump.return_value = {
        "role": "assistant",
        "thinking": "Need to call get_weather",
        "content": "",
        "tool_calls": [
            {"function": {"name": "get_weather", "arguments": {"city": "Warsaw"}}}
        ],
    }
    fake_res_1 = MagicMock(
        message=fake_msg_1, prompt_eval_count=40, eval_count=15
    )

    fake_msg_2 = MagicMock()
    fake_msg_2.model_dump.return_value = {
        "role": "assistant",
        "thinking": "Got weather result",
        "content": "It is 21C in Warsaw.",
        "tool_calls": None,
    }
    fake_res_2 = MagicMock(
        message=fake_msg_2, prompt_eval_count=60, eval_count=12
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(side_effect=[fake_res_1, fake_res_2])

        # 1. Create thread (returns immediately with initial user message)
        res = client.post(
            "/api/threads",
            json={
                "name": "Weather Test",
                "model": "llama3.2",
                "system_message": "def get_weather(city: str):\n    pass",
                "tools": "get_weather",
                "user_message": "Weather in Warsaw?",
            },
        )
        assert res.status_code == 200
        created = res.json()
        assert created["name"] == "Weather Test"
        assert created["messages"] == [
            {"role": "user", "content": "Weather in Warsaw?"}
        ]

        # 2. First Run (calls Ollama and appends assistant + tool slot)
        res_run1 = client.put(
            f"/api/threads/{created['id']}",
            json={
                "name": created["name"],
                "model": created["model"],
                "system_message": created["system_message"],
                "tools": created["tools"],
                "messages": created["messages"],
            },
        )
        assert res_run1.status_code == 200
        thread = res_run1.json()
        assert len(thread["messages"]) == 3
        assert thread["messages"][1]["thinking"] == "Need to call get_weather"
        assert thread["messages"][1]["stats"] == {
            "prompt_tokens": 40,
            "eval_tokens": 15,
        }
        assert thread["messages"][2] == {
            "role": "tool",
            "tool_name": "get_weather",
            "content": "",
        }

        # 3. Fill tool output and Run again
        thread["messages"][2]["content"] = '{"temp": "21C"}'
        res_upd = client.put(
            f"/api/threads/{thread['id']}",
            json={
                "name": "Weather Updated",
                "model": thread["model"],
                "system_message": thread["system_message"],
                "tools": thread["tools"],
                "messages": thread["messages"],
            },
        )
        assert res_upd.status_code == 200
        updated = res_upd.json()
        assert updated["name"] == "Weather Updated"
        assert len(updated["messages"]) == 4
        assert updated["messages"][3]["content"] == "It is 21C in Warsaw."

        # 4. Fork thread
        res_fork = client.post(f"/api/threads/{thread['id']}/fork")
        assert res_fork.status_code == 200
        forked = res_fork.json()
        assert forked["id"] != thread["id"]
        assert forked["name"] == "Weather Updated (Fork)"
        assert forked["messages"] == updated["messages"]

        # 5. List & delete
        res_list = client.get("/api/threads")
        assert len(res_list.json()["threads"]) == 2
        client.delete(f"/api/threads/{forked['id']}")
        assert len(client.get("/api/threads").json()["threads"]) == 1


def test_fastapi_only_imported_in_api_py():
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    violations = []
    for py_file in root.glob("*.py"):
        if py_file.name == "api.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\b(import\s+fastapi|from\s+fastapi\b)", content):
            violations.append(py_file.name)
    assert not violations, f"FastAPI must only be imported in api.py, found in: {violations}"


def test_sqlite3_only_imported_in_db_py():
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    violations = []
    for py_file in root.glob("*.py"):
        if py_file.name == "db.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\b(import\s+sqlite3|from\s+sqlite3\b)", content):
            violations.append(py_file.name)
    assert not violations, f"sqlite3 must only be imported in db.py, found in: {violations}"


def test_dotenv_only_imported_in_config_py():
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    violations = []
    for py_file in root.glob("*.py"):
        if py_file.name == "config.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\b(import\s+dotenv|from\s+dotenv\b|load_dotenv)", content):
            violations.append(py_file.name)
    assert not violations, f"dotenv must only be imported in config.py, found in: {violations}"


def test_env_vars_only_accessed_in_config_py():
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    violations = []
    for py_file in root.glob("*.py"):
        if py_file.name == "config.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\b(os\.environ|os\.getenv)\b", content):
            violations.append(py_file.name)
    assert not violations, f"os.environ / os.getenv must only be accessed in config.py, found in: {violations}"


def test_ollama_only_imported_in_llm_py():
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    violations = []
    for py_file in root.glob("*.py"):
        if py_file.name == "llm.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\b(import\s+ollama|from\s+ollama\b)", content):
            violations.append(py_file.name)
    assert not violations, f"ollama must only be imported in llm.py, found in: {violations}"


def test_companies_api_validation_and_my_nip(monkeypatch):
    monkeypatch.setattr(config, "MY_NIP", "525-26-74-798")

    # 1. GET /api/companies returns my_nip
    res = client.get("/api/companies")
    assert res.status_code == 200
    assert res.json()["my_nip"] == "5252674798"

    # 2. POST /api/companies with invalid NIP returns 400
    res_bad = client.post("/api/companies", json={"nip": "12345"})
    assert res_bad.status_code == 400
    assert "Invalid NIP" in res_bad.json()["detail"]

    # Invalid checksum
    res_bad_checksum = client.post("/api/companies", json={"nip": "1234567890"})
    assert res_bad_checksum.status_code == 400

    # 3. POST /api/companies with only NIP uses default data
    valid_nip = "1234563218"
    client.delete(f"/api/companies/{valid_nip}")

    res_create = client.post("/api/companies", json={"nip": valid_nip})
    assert res_create.status_code == 200
    data = res_create.json()
    assert data["nip"] == valid_nip
    assert data["name"] == f"Firma {valid_nip}"
    assert data["discount"] == 0.0
    assert data["deadline"] == 0

    # 4. Duplicate NIP returns 409
    res_dup = client.post("/api/companies", json={"nip": valid_nip})
    assert res_dup.status_code == 409
    assert f"Company with NIP {valid_nip} already exists" in res_dup.json()["detail"]

    # Cleanup
    client.delete(f"/api/companies/{valid_nip}")


def test_clients_api():
    valid_nip = "1234563218"
    valid_nip_2 = "5260250274"
    test_email = "testclient@example.com"
    updated_email = "updatedclient@example.com"

    # Cleanup any leftovers
    client.delete(f"/api/clients/{test_email}")
    client.delete(f"/api/clients/{updated_email}")
    client.delete(f"/api/companies/{valid_nip}")

    # 1. Validation errors
    res_bad_email = client.post("/api/clients", json={"email": "not-an-email", "nip": valid_nip})
    assert res_bad_email.status_code == 400

    res_bad_nip = client.post("/api/clients", json={"email": test_email, "nip": "12345"})
    assert res_bad_nip.status_code == 400

    # 2. Create client mapping
    res_create = client.post("/api/clients", json={"email": test_email, "nip": valid_nip})
    assert res_create.status_code == 200
    created = res_create.json()
    assert created["email"] == test_email
    assert created["nip"] == valid_nip
    assert created["company_name"] is None

    # 3. Create company and verify company_name is joined
    client.post("/api/companies", json={"nip": valid_nip, "name": "Test Client Sp. z o.o."})
    res_list = client.get("/api/clients")
    assert res_list.status_code == 200
    matched = next((c for c in res_list.json()["clients"] if c["email"] == test_email), None)
    assert matched is not None
    assert matched["company_name"] == "Test Client Sp. z o.o."

    # 4. Duplicate email returns 409
    res_dup = client.post("/api/clients", json={"email": test_email, "nip": valid_nip})
    assert res_dup.status_code == 409

    # 5. Filter by NIP
    res_filter = client.get(f"/api/clients?nip={valid_nip}")
    assert res_filter.status_code == 200
    assert any(c["email"] == test_email for c in res_filter.json()["clients"])

    res_filter_other = client.get(f"/api/clients?nip={valid_nip_2}")
    assert res_filter_other.status_code == 200
    assert not any(c["email"] == test_email for c in res_filter_other.json()["clients"])

    # 6. Update client mapping
    res_upd = client.put(f"/api/clients/{test_email}", json={"email": updated_email, "nip": valid_nip})
    assert res_upd.status_code == 200
    assert res_upd.json()["email"] == updated_email

    # 7. Delete client mapping
    res_del = client.delete(f"/api/clients/{updated_email}")
    assert res_del.status_code == 200

    res_list_after = client.get("/api/clients")
    assert not any(c["email"] == updated_email for c in res_list_after.json()["clients"])

    # Cleanup company
    client.delete(f"/api/companies/{valid_nip}")


def test_emails_api(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test_emails.db"))
    monkeypatch.setattr(config, "MY_NIP", "525-26-74-798")
    monkeypatch.setattr(config, "MY_EMAIL", "sales@mycompany.pl")

    client_nip = "5260250274"
    other_nip = "1234563218"

    client.post("/api/companies", json={"nip": client_nip, "name": "Klient Sp. z o.o."})
    client.post("/api/clients", json={"email": "known@klient.pl", "nip": client_nip})
    client.post("/api/clients", json={"email": "sales@mycompany.pl", "nip": other_nip})
    client.post("/api/clients", json={"email": "me@mycompany.pl", "nip": "5252674798"})

    ship_res = client.post(
        "/api/shippings",
        json={
            "nip": client_nip,
            "name": "Magazyn Centralny",
            "address": "ul. Magazynowa 5",
            "zip_code": "00-100",
            "city": "Warszawa",
        },
    )
    shipping_id = ship_res.json()["id"]

    # 1. Create email from known client email -> auto-resolves NIP from company_emails, shipping_id is None
    eml_known = (
        "From: Jan Kowalski <known@klient.pl>\r\n"
        "To: sales@mycompany.pl\r\n"
        "Subject: Zamowienie 100\r\n"
        "Date: Mon, 26 Oct 2026 14:00:00 +0100\r\n"
        "Content-Type: text/html; charset=utf-8\r\n\r\n"
        "<p>Poprosze 10 sztuk.</p>"
    )
    res1 = client.post("/api/emails", json={"eml_text": eml_known})
    assert res1.status_code == 200
    e1 = res1.json()
    assert e1["nip"] == client_nip
    assert e1["company_name"] == "Klient Sp. z o.o."
    assert e1["shipping_id"] is None
    assert e1["sender"] == "Jan Kowalski <known@klient.pl>"
    assert e1["recipient"] == "sales@mycompany.pl"
    assert e1["title"] == "Zamowienie 100"
    assert e1["date"] == "Mon, 26 Oct 2026 14:00:00 +0100"
    assert e1["notes"] == ""
    assert e1["woocommerce_id"] is None
    assert e1["woocommerce_url"] is None

    # 2. Outgoing email From MY_EMAIL To known@klient.pl -> ignores MY_EMAIL, resolves NIP from To
    eml_to_client = (
        "From: sales@mycompany.pl\r\n"
        "To: Jan Kowalski <known@klient.pl>\r\n"
        "Cc: other@example.com\r\n"
        "Subject: Re: Zamowienie 100\r\n"
        "Date: Mon, 26 Oct 2026 16:00:00 +0100\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "Potwierdzamy przyjecie zamowienia."
    )
    res_to = client.post("/api/emails", json={"eml_text": eml_to_client})
    assert res_to.status_code == 200
    e_to = res_to.json()
    assert e_to["nip"] == client_nip
    assert e_to["shipping_id"] is None
    assert e_to["recipient"] == "Jan Kowalski <known@klient.pl>"

    # 3. Create email with MY_NIP in body and another valid NIP (older date) -> ignores MY_NIP and MY_EMAIL, picks other_nip from body
    eml_body_nip = (
        "From: newbuyer@firma.pl\r\n"
        "To: sales@mycompany.pl\r\n"
        "Subject: Faktura\r\n"
        "Date: Sun, 25 Oct 2026 09:00:00 +0100\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "Nasza firma NIP: 525-26-74-798, Nabywca NIP: 123-456-32-18"
    )
    res2 = client.post("/api/emails", json={"eml_text": eml_body_nip})
    assert res2.status_code == 200
    e2 = res2.json()
    assert e2["nip"] == other_nip

    # 4. Create email where sender is mapped to MY_NIP and To is MY_EMAIL -> nip is None
    eml_only_my_nip = (
        "From: me@mycompany.pl\r\n"
        "To: sales@mycompany.pl\r\n"
        "Subject: Wewnetrzny\r\n"
        "Date: Mon, 26 Oct 2026 12:00:00 +0100\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "NIP: 525-26-74-798"
    )
    res3 = client.post("/api/emails", json={"eml_text": eml_only_my_nip})
    assert res3.status_code == 200
    e3 = res3.json()
    assert e3["nip"] is None

    # 5. List emails -> sorted by EML Date descending (latest first: 16:00, 14:00, 12:00, Oct 25 09:00)
    res_list = client.get("/api/emails")
    assert res_list.status_code == 200
    emails = res_list.json()["emails"]
    assert len(emails) == 4
    assert [x["id"] for x in emails] == [e_to["id"], e1["id"], e3["id"], e2["id"]]

    # 6. Get email detail (includes EML viewer parsed fields)
    res_detail = client.get(f"/api/emails/{e1['id']}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["eml_text"] == eml_known
    assert detail["subject"] == "Zamowienie 100"
    assert detail["to"] == "sales@mycompany.pl"
    assert "<p>Poprosze 10 sztuk.</p>" in detail["html"]

    # 7. Update email NIP and shipping_id independently via badge mechanism
    res_upd_nip = client.put(f"/api/emails/{e3['id']}", json={"nip": client_nip})
    assert res_upd_nip.status_code == 200
    assert res_upd_nip.json()["nip"] == client_nip
    assert res_upd_nip.json()["company_name"] == "Klient Sp. z o.o."
    assert res_upd_nip.json()["shipping_id"] is None

    res_upd_ship = client.put(f"/api/emails/{e3['id']}", json={"shipping_id": shipping_id})
    assert res_upd_ship.status_code == 200
    assert res_upd_ship.json()["nip"] == client_nip
    assert res_upd_ship.json()["shipping_id"] == shipping_id
    assert res_upd_ship.json()["shipping_name"] == "Magazyn Centralny"

    res_upd_notes = client.put(f"/api/emails/{e3['id']}", json={"notes": "Important delivery note"})
    assert res_upd_notes.status_code == 200
    assert res_upd_notes.json()["notes"] == "Important delivery note"
    assert res_upd_notes.json()["nip"] == client_nip
    assert res_upd_notes.json()["shipping_id"] == shipping_id

    res_detail_e3 = client.get(f"/api/emails/{e3['id']}")
    assert res_detail_e3.status_code == 200
    assert res_detail_e3.json()["notes"] == "Important delivery note"

    res_clear_ship = client.put(f"/api/emails/{e3['id']}", json={"shipping_id": None})
    assert res_clear_ship.status_code == 200
    assert res_clear_ship.json()["nip"] == client_nip
    assert res_clear_ship.json()["shipping_id"] is None
    assert res_clear_ship.json()["shipping_name"] is None
    assert res_clear_ship.json()["notes"] == "Important delivery note"

    res_clear_nip = client.put(f"/api/emails/{e3['id']}", json={"nip": None})
    assert res_clear_nip.status_code == 200
    assert res_clear_nip.json()["nip"] is None
    assert res_clear_nip.json()["company_name"] is None
    assert detail["cart"] == {}
    assert detail["messages"] == []


def test_email_order_generation_and_streaming(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test_email_order.db"))
    monkeypatch.setattr(config, "OLLAMA_HOST", "http://127.0.0.1:11434")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, image_src, active, permalink, stock_quantity)
            VALUES (501, 'Puzzle 100 el. Kosmos', 3200, 23, 1500, 'http://img/501.jpg', 1, 'http://shop/501', 12),
                   (502, 'Puzzle 100 el. Dinozaury', 3400, 23, 1600, NULL, 1, NULL, 7)
            """
        )

    client.put(
        "/api/order-maker/config",
        json={
            "model": "qwen2.5:14b",
            "system_prompt": "Custom email order prompt",
            "search_tool": "search_product",
            "set_request_tool": "set_order_text",
            "set_product_tool": "set_order_product",
            "search_row_template": "{rank}. {name} (ID: {id})",
            "search_empty_template": "No products found.",
            "set_text_template": "Saved order text at {at}: {text}",
            "set_product_template": "Set product at {at}: {name} (ID: {product_id}), amount: {amount}",
            "set_product_not_found_template": "Product {product_id} not found.",
            "set_product_no_text_template": "Error: call {set_request_tool} at {at} before adding {product_id}.",
            "resolve_ambiguity_tool": "resolve_ambiguity",
            "resolve_ambiguity_template": "Resolved ambiguity: chosen product is {name} (ID: {id})",
            "resolve_ambiguity_none_template": "No ambiguity rule found for IDs: {ids}.",
        },
    )

    eml_text = (
        "From: buyer@sklep.pl\r\n"
        "To: sales@mycompany.pl\r\n"
        "Subject: Zamowienie puzzle\r\n"
        "Date: Tue, 27 Oct 2026 08:00:00 +0100\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "Poprosze 3x Puzzle 100 el. Kosmos oraz 2x Dinozaury."
    )
    created = client.post("/api/emails", json={"eml_text": eml_text}).json()
    email_id = created["id"]
    client.put(f"/api/emails/{email_id}", json={"notes": "Dodac gratis naklejki i zmienic Kosmos na 4 szt."})

    def make_chunk(thinking="", content="", tool_calls=None, done=False, prompt_eval_count=None, eval_count=None):
        m = MagicMock()
        m.model_dump.return_value = {
            "role": "assistant",
            "content": content,
            "thinking": thinking,
            "tool_calls": tool_calls,
        }
        return MagicMock(
            message=m,
            done=done,
            prompt_eval_count=prompt_eval_count,
            eval_count=eval_count,
        )

    def make_stream(*chunks):
        async def _gen():
            for c in chunks:
                yield c

        return _gen()

    stream_1 = make_stream(
        make_chunk(
            thinking="Trying to set product before text...",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 0, "product_id": 501, "amount": 4},
                    }
                }
            ],
            done=True,
            prompt_eval_count=10,
            eval_count=5,
        )
    )

    stream_2 = make_stream(
        make_chunk(thinking="Reading email and notes... "),
        make_chunk(
            thinking="Creating segment 0 and searching products.",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_text",
                        "arguments": {"at": 0, "text": "Puzzle 100 el. Kosmos (4 szt.) i Dinozaury (2 szt.)"},
                    }
                },
                {
                    "function": {
                        "name": "search_product",
                        "arguments": {"phrase": "Puzzle 100", "limit": 5, "page": 1},
                    }
                },
            ],
            done=True,
            prompt_eval_count=30,
            eval_count=14,
        ),
    )

    stream_3 = make_stream(
        make_chunk(
            thinking="Adding both products into segment 0.",
            tool_calls=[
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 0, "product_id": 501, "amount": 4},
                    }
                },
                {
                    "function": {
                        "name": "set_order_product",
                        "arguments": {"at": 0, "product_id": 502, "amount": 2},
                    }
                },
            ],
            done=True,
            prompt_eval_count=45,
            eval_count=18,
        )
    )

    stream_4 = make_stream(
        make_chunk(
            thinking="Order complete.",
            content="Order created with 2 products in segment 0.",
            done=True,
            prompt_eval_count=50,
            eval_count=10,
        )
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(side_effect=[stream_1, stream_2, stream_3, stream_4])

        res_order = client.post(f"/api/emails/{email_id}/order")
        assert res_order.status_code == 200
        assert "text/event-stream" in res_order.headers["content-type"]

        first_call_kwargs = mock_instance.chat.call_args_list[0].kwargs
        assert first_call_kwargs["model"] == "qwen2.5:14b"
        assert first_call_kwargs["messages"][0] == {
            "role": "system",
            "content": "Custom email order prompt",
        }
        user_msg_content = first_call_kwargs["messages"][1]["content"]
        assert "Poprosze 3x Puzzle 100 el. Kosmos" in user_msg_content
        assert "Notes:\nDodac gratis naklejki i zmienic Kosmos na 4 szt." in user_msg_content
        tool_names = [t["function"]["name"] for t in first_call_kwargs["tools"]]
        assert tool_names == [
            "search_product",
            "set_order_text",
            "set_order_product",
            "resolve_ambiguity",
        ]

    events = [
        json.loads(block[6:])
        for block in res_order.text.strip().split("\n\n")
        if block.startswith("data: ")
    ]
    assert events[0]["type"] == "start"
    assert events[0]["cart"] == {}
    assert len(events[0]["messages"]) == 1
    assert events[0]["messages"][0]["role"] == "user"

    tool_events = [e for e in events if e["type"] == "tool"]
    assert (
        tool_events[0]["message"]["content"]
        == "Error: call set_order_text at 0 before adding 501."
    )
    assert tool_events[0]["cart"] == {}

    assistant_events = [e for e in events if e["type"] == "assistant"]
    assert assistant_events[1]["message"]["thinking"] == "Reading email and notes... "
    assert (
        assistant_events[2]["message"]["thinking"]
        == "Reading email and notes... Creating segment 0 and searching products."
    )

    done_event = events[-1]
    assert done_event["type"] == "done"
    assert "0" in done_event["cart"]
    seg = done_event["cart"]["0"]
    assert seg["at"] == 0
    assert seg["text"] == "Puzzle 100 el. Kosmos (4 szt.) i Dinozaury (2 szt.)"
    assert seg["products"]["501"]["amount"] == 4
    assert seg["products"]["501"]["product"]["name"] == "Puzzle 100 el. Kosmos"
    assert seg["products"]["502"]["amount"] == 2
    assert seg["products"]["502"]["product"]["name"] == "Puzzle 100 el. Dinozaury"
    assert done_event["stats"] == {"prompt_tokens": 135, "eval_tokens": 47}

    detail_after = client.get(f"/api/emails/{email_id}").json()
    assert detail_after["cart"] == done_event["cart"]
    assert detail_after["messages"] == done_event["messages"]

    res_404 = client.post("/api/emails/999999/order")
    assert res_404.status_code == 404


def test_email_submit_woocommerce_order(monkeypatch, tmp_path):
    import httpx
    from unittest.mock import patch

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test_email_wc.db"))

    # 1. Unconfigured WooCommerce -> 500
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", None)
    res_unconf = client.post("/api/emails/1/submit-woocommerce")
    assert res_unconf.status_code == 500

    # Configure WooCommerce
    monkeypatch.setattr(config, "WOOCOMMERCE_URL", "https://example.com")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_KEY", "ck_test")
    monkeypatch.setattr(config, "WOOCOMMERCE_CONSUMER_SECRET", "cs_test")

    # 2. Non-existent email -> 404
    res_404 = client.post("/api/emails/99999/submit-woocommerce")
    assert res_404.status_code == 404

    # Setup company, shipping, product, and email with cart
    client_nip = "5260250274"
    client.post("/api/companies", json={"nip": client_nip, "name": "Firma Testowa", "discount": 10.0})
    ship_res = client.post(
        "/api/shippings",
        json={
            "nip": client_nip,
            "name": "Magazyn Odbiorczy",
            "address": "ul. Dostawcza 10",
            "zip_code": "02-200",
            "city": "Krakow",
            "phone": "987654321",
            "email": "magazyn@testowa.pl",
        },
    )
    shipping_id = ship_res.json()["id"]

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO products (id, name, price_cents, tax_class, prod_cost_cents, active)
            VALUES (201, 'Produkt A', 5000, 23, 2000, 1),
                   (202, 'Produkt B', 10000, 5, 4000, 1)
            """
        )

    eml_text = (
        "From: Jan Kowalski <jan@firma.pl>\r\n"
        "To: sales@mycompany.pl\r\n"
        "Subject: Zamowienie hurtowe\r\n"
        "Date: Tue, 27 Oct 2026 10:00:00 +0100\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "Tresc maila"
    )
    created = client.post("/api/emails", json={"eml_text": eml_text}).json()
    email_id = created["id"]

    # 3a. Missing NIP -> 400
    res_no_nip = client.post(f"/api/emails/{email_id}/submit-woocommerce", json={"confirmed": True})
    assert res_no_nip.status_code == 400
    assert "NIP is required" in res_no_nip.json()["detail"]

    client.put(f"/api/emails/{email_id}", json={"nip": client_nip, "shipping_id": shipping_id, "notes": "Uwaga: szklo"})

    # 3b. Missing confirmation -> 400
    res_unconfirmed = client.post(f"/api/emails/{email_id}/submit-woocommerce", json={"confirmed": False})
    assert res_unconfirmed.status_code == 400
    assert "Confirmation required" in res_unconfirmed.json()["detail"]

    # 3c. Empty cart -> 400
    res_empty = client.post(f"/api/emails/{email_id}/submit-woocommerce", json={"confirmed": True})
    assert res_empty.status_code == 400
    assert "Cart has no products" in res_empty.json()["detail"]

    # Save cart to email
    cart = {
        "0": {
            "at": 0,
            "products": {
                "201": {
                    "product_id": 201,
                    "amount": 2,
                    "product": {"id": 201, "name": "Produkt A", "price_cents": 5000, "tax_class": 23},
                },
                "202": {
                    "product_id": 202,
                    "amount": 1,
                    "product": {"id": 202, "name": "Produkt B", "price_cents": 10000, "tax_class": 5},
                },
            },
        }
    }
    db.save_email_order(email_id, cart, [])

    # Configure Fakturownia
    monkeypatch.setattr(config, "FAKTUROWNIA_URL", "https://demo.fakturownia.pl")
    monkeypatch.setattr(config, "FAKTUROWNIA_API_TOKEN", "tok_123")

    captured_requests = []

    async def mock_post(url, *args, **kwargs):
        json_body = kwargs.get("json")
        auth = kwargs.get("auth") or (args[0] if len(args) > 0 else None)
        captured_requests.append({"url": str(url), "auth": auth, "json": json_body})
        if "fakturownia.pl" in str(url):
            return httpx.Response(
                201,
                json={"id": 55443, "number": "FV 12/2026", "token": "hash123"},
                request=httpx.Request("POST", str(url)),
            )
        return httpx.Response(201, json={"id": 99112, "status": "on-hold"}, request=httpx.Request("POST", str(url)))

    # 4. Successful submission
    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        res_submit = client.post(
            f"/api/emails/{email_id}/submit-woocommerce",
            json={"customer_note": "Odprawa boczna", "confirmed": True},
        )
        assert res_submit.status_code == 200
        data = res_submit.json()
        assert data["ok"] is True
        assert data["woocommerce_id"] == 99112
        assert data["fakturownia_id"] == 55443
        assert data["fakturownia_number"] == "FV 12/2026"
        assert data["fakturownia_url"] == "https://demo.fakturownia.pl/invoices/55443"
        assert data["order_url"] == "https://example.com/wp-admin/post.php?post=99112&action=edit"

    assert len(captured_requests) == 2
    # First request was to Fakturownia
    req_fak = captured_requests[0]
    assert req_fak["url"] == "https://demo.fakturownia.pl/invoices.json"
    assert req_fak["json"]["api_token"] == "tok_123"

    # Second request was to WooCommerce
    req = captured_requests[1]
    assert req["url"] == "https://example.com/wp-json/wc/v3/orders"
    assert req["auth"] == ("ck_test", "cs_test")
    payload = req["json"]
    assert payload["customer_id"] == 1
    assert payload["status"] == "on-hold"
    assert payload["customer_note"] == "Odprawa boczna"
    assert payload["meta_data"] == [
        {"key": "_billing_nip", "value": client_nip},
        {"key": "_woo_fakturownia_faktura", "value": {"id": 55443, "numer": "FV 12/2026"}},
        {"key": "_woo_fakturownia_faktura_hash", "value": "hash123"},
    ]
    assert payload["billing"]["company"] == "Firma Testowa"
    assert payload["billing"]["email"] == "magazyn@testowa.pl"
    assert payload["shipping"]["company"] == "Firma Testowa"
    assert payload["shipping"]["first_name"] == "Magazyn Odbiorczy"
    assert payload["shipping"]["city"] == "Krakow"

    # Line items check:
    # 201: gross 50.00 -> net unit 5000*100/123 = 4065.04 cents. Qty 2: subtotal 81.30, 10% disc total 73.17
    # 202: gross 100.00 -> net unit 10000*100/105 = 9523.81 cents. Qty 1: subtotal 95.24, 10% disc total 85.71
    items_by_id = {item["product_id"]: item for item in payload["line_items"]}
    assert items_by_id[201]["quantity"] == 2
    assert items_by_id[201]["subtotal"] == "81.30"
    assert items_by_id[201]["total"] == "73.17"
    assert items_by_id[202]["quantity"] == 1
    assert items_by_id[202]["subtotal"] == "95.24"
    assert items_by_id[202]["total"] == "85.71"

    # 5. Verify persisted in DB and returned in GET detail and GET list
    get_res = client.get(f"/api/emails/{email_id}")
    assert get_res.status_code == 200
    assert get_res.json()["woocommerce_id"] == 99112
    assert get_res.json()["woocommerce_url"] == "https://example.com/wp-admin/post.php?post=99112&action=edit"

    list_res = client.get("/api/emails")
    summary = next(e for e in list_res.json()["emails"] if e["id"] == email_id)
    assert summary["woocommerce_id"] == 99112
    assert summary["woocommerce_url"] == "https://example.com/wp-admin/post.php?post=99112&action=edit"

    # 6. Re-submission returns 400 (already submitted)
    res_dup = client.post(f"/api/emails/{email_id}/submit-woocommerce")
    assert res_dup.status_code == 400
    assert "already submitted" in res_dup.json()["detail"].lower()

    # 7. Updating woocommerce_id via PUT works
    res_upd = client.put(f"/api/emails/{email_id}", json={"woocommerce_id": 99999})
    assert res_upd.status_code == 200
    assert res_upd.json()["woocommerce_id"] == 99999
    assert res_upd.json()["woocommerce_url"] == "https://example.com/wp-admin/post.php?post=99999&action=edit"




