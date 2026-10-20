from datetime import date, timedelta
from unittest.mock import patch
import httpx
import pytest

import config
import fakturownia


def test_check_fakturownia_config():
    with patch.object(config, "FAKTUROWNIA_URL", "https://test.fakturownia.pl"), \
         patch.object(config, "FAKTUROWNIA_API_TOKEN", "token_123"):
        fakturownia.check_fakturownia_config()

    with patch.object(config, "FAKTUROWNIA_URL", None):
        with pytest.raises(ValueError, match="Fakturownia API is not configured"):
            fakturownia.check_fakturownia_config()

    with patch.object(config, "FAKTUROWNIA_URL", "https://test.fakturownia.pl"), \
         patch.object(config, "FAKTUROWNIA_API_TOKEN", None):
        with pytest.raises(ValueError, match="Fakturownia API is not configured"):
            fakturownia.check_fakturownia_config()


def test_build_fakturownia_payload_with_deadline_and_discount():
    company = {
        "nip": "5252674798",
        "name": "Example Sp. z o.o.",
        "address": "ul. Prosta 10",
        "zip_code": "00-001",
        "city": "Warszawa",
        "discount": 10.0,
        "deadline": 14,
    }
    shipping = {
        "nip": "5252674798",
        "name": "Example Sp. z o.o.",
        "address": "ul. Prosta 10",
        "zip_code": "00-001",
        "city": "Warszawa",
        "phone": "123456789",
        "email": "kontakt@example.com",
    }
    line_items = [
        {
            "product_id": 1,
            "name": "Kolorowanka",
            "quantity": 2,
            "price_cents": 5000,
            "tax_class": 23,
        },
        {
            "product_id": 2,
            "name": "Klocki",
            "quantity": 1,
            "price_cents": 10000,
            "tax_class": 5,
        },
    ]

    with patch.object(config, "FAKTUROWNIA_API_TOKEN", "secret_tok"):
        payload = fakturownia.build_fakturownia_payload(
            company=company,
            shipping=shipping,
            nip="5252674798",
            email_addr="jan@example.com",
            line_items=line_items,
            customer_note="Pilne zamówienie",
        )

    assert payload["api_token"] == "secret_tok"
    inv = payload["invoice"]
    assert inv["kind"] == "vat"
    assert inv["show_discount"] == 1
    assert inv["payment_to_kind"] == 14
    today = date.today().strftime("%Y-%m-%d")
    expected_payment_to = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    assert inv["issue_date"] == today
    assert inv["sell_date"] == today
    assert inv["payment_to"] == expected_payment_to
    assert inv["buyer_name"] == "Example Sp. z o.o."
    assert inv["buyer_tax_no"] == "5252674798"
    assert inv["buyer_street"] == "ul. Prosta 10"
    assert inv["buyer_post_code"] == "00-001"
    assert inv["buyer_city"] == "Warszawa"
    assert inv["buyer_email"] == "jan@example.com"
    assert inv["buyer_phone"] == "123456789"
    assert inv["buyer_person"] == ""
    assert inv["description"] == "Pilne zamówienie"

    # Same NIP -> no recipient fields
    assert "recipient_name" not in inv
    assert "recipients" not in inv

    # Positions
    positions = inv["positions"]
    assert len(positions) == 2
    # Item 1: gross 50.00, tax 23 -> net unit 50 / 1.23 = 40.65, total gross 100.00, disc 10%
    assert positions[0]["name"] == "Kolorowanka"
    assert positions[0]["quantity"] == 2
    assert positions[0]["tax"] == 23
    assert positions[0]["price_net"] == "40.65"
    assert positions[0]["total_price_gross"] == "100.00"
    assert positions[0]["discount_percent"] == 10.0

    # Item 2: gross 100.00, tax 5 -> net unit 100 / 1.05 = 95.24, total gross 100.00, disc 10%
    assert positions[1]["name"] == "Klocki"
    assert positions[1]["quantity"] == 1
    assert positions[1]["tax"] == 5
    assert positions[1]["price_net"] == "95.24"
    assert positions[1]["total_price_gross"] == "100.00"
    assert positions[1]["discount_percent"] == 10.0


def test_build_fakturownia_payload_nabywca_and_odbiorca():
    company = {
        "nip": "5252674798",
        "name": "Gmina Miasta Warszawa",
        "address": "pl. Bankowy 3/5",
        "zip_code": "00-950",
        "city": "Warszawa",
        "discount": 0.0,
        "deadline": 0,
    }
    shipping = {
        "nip": "",
        "name": "Szkoła Podstawowa nr 1",
        "address": "ul. Szkolna 12",
        "zip_code": "01-002",
        "city": "Warszawa",
        "phone": "987654321",
        "email": "sp1@szkola.pl",
    }
    line_items = [
        {
            "product_id": 1,
            "name": "Podręcznik",
            "quantity": 10,
            "price_cents": 2000,
            "tax_class": 5,
        }
    ]

    with patch.object(config, "FAKTUROWNIA_API_TOKEN", "tok"):
        payload = fakturownia.build_fakturownia_payload(
            company=company,
            shipping=shipping,
            nip="5252674798",
            email_addr="gmina@um.warszawa.pl",
            line_items=line_items,
        )

    inv = payload["invoice"]
    # Buyer is company
    assert inv["buyer_name"] == "Gmina Miasta Warszawa"
    assert inv["buyer_tax_no"] == "5252674798"
    assert inv["payment_to_kind"] == 0
    assert "payment_to" not in inv

    # Odbiorca is shipping
    assert inv["recipient_name"] == "Szkoła Podstawowa nr 1"
    assert inv["recipient_street"] == "ul. Szkolna 12"
    assert inv["recipient_post_code"] == "01-002"
    assert inv["recipient_city"] == "Warszawa"
    assert inv["recipient_email"] == "sp1@szkola.pl"
    assert inv["recipient_phone"] == "987654321"
    assert inv["recipients"] == [
        {
            "name": "Szkoła Podstawowa nr 1",
            "tax_no": "",
            "street": "ul. Szkolna 12",
            "post_code": "01-002",
            "city": "Warszawa",
            "country": "PL",
            "role": "Odbiorca",
        }
    ]


def test_build_fakturownia_payload_seller_person():
    company = {"name": "Test Co", "address": "Ul. 1", "zip_code": "00-000", "city": "Miasto"}
    with patch.object(config, "FAKTUROWNIA_API_TOKEN", "tok"), \
         patch.object(config, "FAKTUROWNIA_SELLER_PERSON", "Jan Nowak"):
        payload = fakturownia.build_fakturownia_payload(
            company=company,
            shipping=None,
            nip="1234567890",
            email_addr="test@example.com",
            line_items=[],
        )
    assert payload["invoice"]["seller_person"] == "Jan Nowak"
    assert payload["invoice"]["buyer_person"] == ""

    with patch.object(config, "FAKTUROWNIA_API_TOKEN", "tok"), \
         patch.object(config, "FAKTUROWNIA_SELLER_PERSON", ""):
        payload_empty = fakturownia.build_fakturownia_payload(
            company=company,
            shipping=None,
            nip="1234567890",
            email_addr="test@example.com",
            line_items=[],
        )
    assert "seller_person" not in payload_empty["invoice"]
    assert payload_empty["invoice"]["buyer_person"] == ""


@pytest.mark.anyio
async def test_create_fakturownia_invoice():
    captured_requests = []

    async def mock_post(url, json):
        captured_requests.append({"url": url, "json": json})
        return httpx.Response(
            201,
            json={
                "id": 123456789,
                "number": "1/10/2026",
                "token": "test_invoice_token_123",
            },
            request=httpx.Request("POST", url),
        )

    with patch.object(config, "FAKTUROWNIA_URL", "https://demo.fakturownia.pl"), \
         patch.object(config, "FAKTUROWNIA_API_TOKEN", "test_api_token"), \
         patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        res = await fakturownia.create_fakturownia_invoice(
            company={"nip": "123", "name": "Co", "address": "A", "zip_code": "00", "city": "C"},
            shipping=None,
            nip="123",
            email_addr="a@b.com",
            line_items=[{"product_id": 1, "name": "P1", "quantity": 1, "price_cents": 1000, "tax_class": 23}],
        )

    assert res["id"] == 123456789
    assert res["number"] == "1/10/2026"
    assert res["token"] == "test_invoice_token_123"
    assert res["url"] == "https://demo.fakturownia.pl/invoices/123456789"
    assert len(captured_requests) == 1
    assert captured_requests[0]["url"] == "https://demo.fakturownia.pl/invoices.json"
