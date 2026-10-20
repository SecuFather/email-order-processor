from datetime import date, timedelta
from typing import Any
import httpx
import config


def check_fakturownia_config() -> None:
    if not config.FAKTUROWNIA_URL or not config.FAKTUROWNIA_API_TOKEN:
        raise ValueError("Fakturownia API is not configured")


def build_fakturownia_payload(
    company: dict[str, Any],
    shipping: dict[str, Any] | None,
    nip: str,
    email_addr: str,
    line_items: list[dict[str, Any]],
    customer_note: str | None = None,
) -> dict[str, Any]:
    today = date.today().strftime("%Y-%m-%d")
    deadline = int(company.get("deadline") or 0)
    discount = float(company.get("discount") or 0.0)

    invoice: dict[str, Any] = {
        "kind": "vat",
        "show_discount": 1,
        "issue_date": today,
        "sell_date": today,
        "payment_to_kind": deadline,
        "buyer_name": company["name"],
        "buyer_tax_no": nip,
        "buyer_street": company["address"],
        "buyer_post_code": company["zip_code"],
        "buyer_city": company["city"],
        "buyer_email": email_addr,
        "buyer_phone": shipping["phone"] if shipping and shipping.get("phone") else "",
        "buyer_person": "",
    }
    if config.FAKTUROWNIA_SELLER_PERSON:
        invoice["seller_person"] = config.FAKTUROWNIA_SELLER_PERSON
    if deadline > 0:
        invoice["payment_to"] = (date.today() + timedelta(days=deadline)).strftime("%Y-%m-%d")
    if customer_note:
        invoice["description"] = customer_note

    shipping_nip = (shipping.get("nip") or "").strip() if shipping else ""
    company_nip = (company.get("nip") or "").strip()
    if shipping and shipping_nip != company_nip:
        invoice["recipient_name"] = shipping["name"]
        invoice["recipient_street"] = shipping["address"]
        invoice["recipient_post_code"] = shipping["zip_code"]
        invoice["recipient_city"] = shipping["city"]
        invoice["recipient_country"] = "PL"
        if shipping.get("email"):
            invoice["recipient_email"] = shipping["email"]
        if shipping.get("phone"):
            invoice["recipient_phone"] = shipping["phone"]
        if shipping_nip:
            invoice["recipient_tax_no"] = shipping_nip
            invoice["recipient_note"] = f"NIP: {shipping_nip}"
        invoice["recipients"] = [
            {
                "name": shipping["name"],
                "tax_no": shipping_nip,
                "street": shipping["address"],
                "post_code": shipping["zip_code"],
                "city": shipping["city"],
                "country": "PL",
                "role": "Odbiorca",
            }
        ]

    positions = []
    for item in line_items:
        qty = item["quantity"]
        gross_unit = item["price_cents"] / 100
        tax = item["tax_class"]
        net_unit = (item["price_cents"] * 100 / (100 + tax)) / 100

        pos: dict[str, Any] = {
            "name": item["name"],
            "quantity": qty,
            "tax": tax,
            "price_net": f"{net_unit:.2f}",
            "total_price_gross": f"{gross_unit * qty:.2f}",
        }
        if discount > 0:
            pos["discount_percent"] = discount
        positions.append(pos)

    invoice["positions"] = positions
    return {"api_token": config.FAKTUROWNIA_API_TOKEN, "invoice": invoice}


async def create_fakturownia_invoice(
    company: dict[str, Any],
    shipping: dict[str, Any] | None,
    nip: str,
    email_addr: str,
    line_items: list[dict[str, Any]],
    customer_note: str | None = None,
) -> dict[str, Any]:
    check_fakturownia_config()
    payload = build_fakturownia_payload(company, shipping, nip, email_addr, line_items, customer_note)
    base_url = config.FAKTUROWNIA_URL.rstrip("/")
    url = f"{base_url}/invoices.json"

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload)
        res.raise_for_status()
        data = res.json()

    inv_id = data["id"]
    return {
        "id": inv_id,
        "number": data.get("number", ""),
        "token": data.get("token", ""),
        "url": f"{base_url}/invoices/{inv_id}",
    }
