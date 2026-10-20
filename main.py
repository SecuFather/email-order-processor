import base64
import email
from email import policy
import io
import re
from typing import Any

from markitdown import MarkItDown, StreamInfo
from unidecode import unidecode
import uvicorn

import config
import db
from schemas import OrderMakerConfig

md = MarkItDown(enable_plugins=True)


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", unidecode(text).lower())
    words = [w for w in cleaned.split() if len(w) >= 4 or any(c.isdigit() for c in w)]
    return " ".join(words)


NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
NIP_PATTERN = re.compile(r"(?<!\d)(?:\d[- ._]?){9}\d(?!\d)")


def is_valid_nip(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    return sum(int(d) * w for d, w in zip(digits, NIP_WEIGHTS)) % 11 == int(digits[9])


def extract_nip_from_eml(eml_content: str) -> str | None:
    my_nip = re.sub(r"\D", "", config.MY_NIP or "")
    msg = email.message_from_string(eml_content, policy=policy.default)
    body = msg.get_body(preferencelist=("plain", "html")).get_content()
    for m in NIP_PATTERN.finditer(body):
        digits = re.sub(r"\D", "", m.group(0))
        if digits != my_nip and is_valid_nip(digits):
            return digits
    return None


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_email_address(from_header: str) -> str | None:
    match = EMAIL_PATTERN.search(from_header)
    return match.group(0).lower() if match else None


def resolve_email_nip(eml_text: str, sender_header: str, to_header: str = "") -> str | None:
    my_nip = re.sub(r"\D", "", config.MY_NIP or "")
    my_email = extract_email_address(config.MY_EMAIL or "")
    for m in EMAIL_PATTERN.finditer(f"{sender_header} {to_header}"):
        addr = m.group(0).lower()
        if addr != my_email:
            nip = db.get_nip_by_email(addr)
            if nip and nip != my_nip:
                return nip
    return extract_nip_from_eml(eml_text)



def parse_attachment(part):
    filename = part.get_filename()
    content_type = part.get_content_type()
    payload = part.get_payload(decode=True)
    if content_type == "application/pdf" or content_type.startswith("image/"):
        return {
            "filename": filename,
            "content_type": content_type,
            "data": base64.b64encode(payload).decode(),
        }
    return {
        "filename": filename,
        "markdown": md.convert_stream(
            io.BytesIO(payload), stream_info=StreamInfo(filename=filename)
        ).text_content,
    }


def search_products(phrase: str, limit: int, page: int) -> dict[str, Any]:
    words = normalize_text(phrase).split()
    if not words:
        return {"products": []}

    products = db.get_active_products()
    normalized = [(prod, normalize_text(prod["name"])) for prod in products]
    results = []
    seen_ids = set()
    offset = (page - 1) * limit

    for k in range(len(words), 0, -1):
        for prod, norm_name in normalized:
            if prod["id"] not in seen_ids and all(w in norm_name for w in words[:k]):
                seen_ids.add(prod["id"])
                if len(seen_ids) > offset:
                    results.append(
                        {**prod, "not_matching_words": len(words) - k}
                    )
                    if len(results) == limit:
                        return {"products": results}

    return {"products": results}


async def process_order_tool_call(
    req: OrderMakerConfig,
    name: str,
    args: dict[str, Any],
    cart: dict[str, Any],
) -> str:
    if name == req.search_tool:
        search_res = search_products(
            str(args["phrase"]),
            int(args.get("limit", 5)),
            int(args.get("page", 1)),
        )
        prods = search_res["products"]
        if not prods:
            return req.search_empty_template
        return "\n".join(
            req.search_row_template.format(
                rank=i + 1,
                name=p["name"],
                id=p["id"],
                price=f"{p['price_cents'] / 100:.2f}",
                stock=p["stock_quantity"] or 0,
            )
            for i, p in enumerate(prods)
        )

    if name == req.set_request_tool:
        at = str(args["at"])
        text = str(args["text"])
        cart.setdefault(at, {"at": int(at), "products": {}})["text"] = text
        return req.set_text_template.format(at=at, text=text)

    if name == req.set_product_tool:
        at = str(args["at"])
        product_id = int(args["product_id"])
        segment = cart.get(at)
        if not segment or not segment.get("text"):
            return req.set_product_no_text_template.format(
                at=at,
                product_id=product_id,
                set_request_tool=req.set_request_tool,
            )
        amount_raw = float(args["amount"])
        amount = int(amount_raw) if amount_raw.is_integer() else amount_raw
        p_dict = db.get_product(product_id)
        if not p_dict:
            return req.set_product_not_found_template.format(
                product_id=product_id, at=at
            )
        segment["products"][str(product_id)] = {
            "product_id": product_id,
            "amount": amount,
            "product": p_dict,
        }
        return req.set_product_template.format(
            at=at,
            product_id=product_id,
            amount=amount,
            name=p_dict["name"],
            price=f"{p_dict['price_cents'] / 100:.2f}",
            stock=p_dict["stock_quantity"] or 0,
        )

    if name == req.resolve_ambiguity_tool:
        ids = [int(x) for x in args["ids"]]
        row = db.find_ambiguity_choice(ids)
        if row:
            return req.resolve_ambiguity_template.format(
                ids=ids,
                id=row["id"],
                name=row["name"],
                price=f"{row['price_cents'] / 100:.2f}",
                stock=row["stock_quantity"] or 0,
            )
        return req.resolve_ambiguity_none_template.format(ids=ids)

    return ""


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=config.HOST,
        port=config.PORT,
        ssl_certfile=config.SSL_CERTFILE,
        ssl_keyfile=config.SSL_KEYFILE,
    )
