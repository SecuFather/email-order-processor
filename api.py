import asyncio
from datetime import datetime, timezone
import email
from email import policy
import json
import os
import re
import tempfile
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx
from markitdown import StreamInfo

import config
import db
import fakturownia
import gus
import llm
import main
from main import (
    extract_email_address,
    extract_nip_from_eml,
    is_valid_nip,
    normalize_text,
    parse_attachment,
    process_order_tool_call,
    resolve_email_nip,
    search_products,
)
from schemas import (
    DEFAULT_ORDER_SYSTEM_PROMPT,
    DEFAULT_SHIPPING_SYSTEM_PROMPT,
    ConnectEmailRequest,
    ConnectOrderShippingRequest,
    CreateAmbiguityPairRequest,
    CreateClientRequest,
    CreateCompanyRequest,
    CreateEmailRequest,
    CreateOrderMakerOrderRequest,
    CreateShippingRequest,
    CreateThreadRequest,
    DisconnectEmailRequest,
    ExtractShippingRequest,
    FetchCompanyRequest,
    FetchShippingRequest,
    NormalizeRequest,
    OrderMakerConfig,
    OrderMakerRunRequest,
    ShippingConfig,
    ShippingExtractionResult,
    SubmitWooCommerceOrderRequest,
    UpdateClientRequest,
    UpdateCompanyRequest,
    UpdateEmailRequest,
    UpdateOrderMakerOrderRequest,
    UpdateProductRequest,
    UpdateShippingRequest,
    UpdateThreadRequest,
    UpdateVariantRequest,
)

app = FastAPI()
sync_lock = asyncio.Lock()

GOOGLE_DOCS_RE = re.compile(
    r"https://docs\.google\.com/(document|spreadsheets|presentation)/d/([a-zA-Z0-9_-]+)"
)
GOOGLE_EXPORT_FORMATS = {
    "document": "docx",
    "spreadsheets": "xlsx",
    "presentation": "pptx",
}


def convert_eml_bytes(raw_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".eml") as tmp:
        tmp.write(raw_bytes)
        tmp.flush()
        markdown = main.md.convert(tmp.name, email_attachment_mode="inline").text_content
    for doc_type, doc_id in dict.fromkeys(GOOGLE_DOCS_RE.findall(markdown)):
        ext = GOOGLE_EXPORT_FORMATS[doc_type]
        url = f"https://docs.google.com/{doc_type}/d/{doc_id}/export?format={ext}"
        doc_md = main.md.convert(
            url, stream_info=StreamInfo(extension=f".{ext}")
        ).text_content
        markdown += f"\n\n## Google {doc_type.capitalize()} ({doc_id})\n\n{doc_md}"
    return markdown


@app.post("/api/convert-eml")
async def convert_eml(file: UploadFile):
    return {"markdown": convert_eml_bytes(await file.read())}


def parse_eml_message(msg: email.message.EmailMessage) -> dict[str, Any]:
    body_part = msg.get_body(preferencelist=("html", "plain"))
    html = body_part.get_content() if body_part else ""
    google_docs = [
        {
            "filename": f"Google {doc_type.capitalize()} ({doc_id[:8]})",
            "url": f"https://docs.google.com/{doc_type}/d/{doc_id}/preview",
        }
        for doc_type, doc_id in dict.fromkeys(GOOGLE_DOCS_RE.findall(html))
    ]
    return {
        "subject": msg["Subject"],
        "from": msg["From"],
        "to": msg["To"],
        "date": msg["Date"],
        "html": html,
        "attachments": [
            *[parse_attachment(part) for part in msg.iter_attachments()],
            *google_docs,
        ],
    }


@app.post("/api/parse-eml")
async def parse_eml(file: UploadFile):
    msg = email.message_from_bytes(await file.read(), policy=policy.default)
    return parse_eml_message(msg)


@app.post("/api/normalize")
async def normalize(req: NormalizeRequest):
    return {"normalized": normalize_text(req.text)}


@app.get("/api/threads")
async def list_threads():
    return {"threads": db.list_threads()}


@app.post("/api/threads")
async def create_thread(req: CreateThreadRequest):
    return db.create_thread(
        req.name, req.model, req.system_message, req.tools, req.user_message
    )


@app.put("/api/threads/{thread_id}")
async def update_thread(thread_id: int, req: UpdateThreadRequest):
    messages = await llm.run_ollama(
        req.model, req.system_message, req.tools, req.messages
    )
    return db.update_thread(
        thread_id, req.name, req.model, req.system_message, req.tools, messages
    )


@app.post("/api/threads/{thread_id}/fork")
async def fork_thread(thread_id: int):
    return db.fork_thread(thread_id)


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: int):
    db.delete_thread(thread_id)
    return {"ok": True}


@app.get("/api/products")
async def list_products():
    return {"products": db.list_products()}


@app.get("/api/products/search")
async def search_products_endpoint(phrase: str, limit: int, page: int):
    return search_products(phrase, limit, page)


@app.put("/api/products/{product_id}")
async def update_product(product_id: int, req: UpdateProductRequest):
    row = db.update_product(
        product_id, req.name, req.price_cents, req.prod_cost_cents, req.active
    )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


@app.delete("/api/products")
async def delete_all_products():
    db.delete_all_products()
    return {"ok": True}


@app.get("/api/variants")
async def list_variants():
    return {"variants": db.list_variants()}


@app.put("/api/variants/{variant_id}")
async def update_variant(variant_id: int, req: UpdateVariantRequest):
    row = db.update_variant(
        variant_id,
        req.name,
        req.price_cents,
        req.prod_cost_cents,
        req.stock,
        req.product_name,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Variant not found")
    return row


@app.delete("/api/variants")
async def delete_all_variants():
    db.delete_all_variants()
    return {"ok": True}


@app.post("/api/woocommerce/sync")
async def sync_woocommerce():
    async with sync_lock:
        last_sync_date = db.get_sync_date()
        url = f"{config.WOOCOMMERCE_URL.rstrip('/')}/wp-json/wc/v3/products"
        auth = (
            config.WOOCOMMERCE_CONSUMER_KEY,
            config.WOOCOMMERCE_CONSUMER_SECRET,
        )
        params: dict[str, Any] = {
            "per_page": 100,
            "orderby": "modified",
            "order": "asc",
        }
        if last_sync_date:
            params["modified_after"] = last_sync_date

        variants_to_sync: list[dict[str, Any]] = []
        async with httpx.AsyncClient() as client:
            res = await client.get(url, auth=auth, params=params)
            res.raise_for_status()
            items = res.json()

            for item in items:
                if item.get("type") == "variable" or (item.get("variations") and isinstance(item["variations"], list)):
                    parent_name = item["name"]
                    parent_img = item["images"][0]["src"] if item.get("images") else None
                    parent_url = item.get("permalink")
                    cost_val = next(
                        (m["value"] for m in item.get("meta_data", []) if m["key"] == "_prod_cost" and m["value"]),
                        None,
                    )
                    parent_cost = (
                        round(float(str(cost_val).replace(",", ".").replace(" ", "")) * 100)
                        if cost_val
                        else None
                    )
                    if parent_cost is None:
                        db_prod = db.get_product(item["id"])
                        if db_prod:
                            parent_cost = db_prod.get("prod_cost_cents")
                    raw_vars = []
                    if item.get("variations") and isinstance(item["variations"][0], dict):
                        raw_vars = item["variations"]
                    else:
                        var_url = f"{config.WOOCOMMERCE_URL.rstrip('/')}/wp-json/wc/v3/products/{item['id']}/variations"
                        var_res = await client.get(var_url, auth=auth, params={"per_page": 100})
                        if var_res.is_success:
                            raw_vars = var_res.json()

                    for v in raw_vars:
                        name = (v.get("name") or "").strip()
                        if not name:
                            attr_parts = [
                                str(a.get("option", "")).strip()
                                for a in v.get("attributes", [])
                                if a.get("option")
                            ]
                            name = f"{parent_name} - {', '.join(attr_parts)}" if attr_parts else f"{parent_name} #{v['id']}"
                        variants_to_sync.append({
                            "id": v["id"],
                            "parent_id": item["id"],
                            "name": name,
                            "product_name": parent_name,
                            "price_cents": round(float(v.get("price") or v.get("regular_price") or item.get("price") or 0) * 100),
                            "tax_class": 23 if not v.get("tax_class") else 5,
                            "prod_cost_cents": parent_cost,
                            "image_src": parent_img,
                            "permalink": parent_url,
                            "stock": v.get("stock_quantity") if "stock_quantity" in v else v.get("stock"),
                        })

        total_synced = 0
        total_variants_synced = 0
        if items:
            last_sync_date = items[-1]["date_modified"]
            total_synced = db.sync_woocommerce_products(items, last_sync_date)
        if variants_to_sync:
            total_variants_synced = db.sync_woocommerce_variants(variants_to_sync)

        res_data: dict[str, Any] = {
            "last_sync_date": last_sync_date,
            "synced_count": total_synced,
            "has_more": len(items) == 100,
        }
        if total_variants_synced > 0:
            res_data["synced_variants_count"] = total_variants_synced
        return res_data


@app.post("/api/woocommerce/reset-sync")
async def reset_woocommerce_sync():
    db.reset_sync_date()
    return {"ok": True}


@app.get("/api/order-maker/config")
async def get_order_maker_config():
    row = db.get_order_maker_config()
    return (
        {k: row[k] for k in OrderMakerConfig.model_fields}
        if row
        else OrderMakerConfig()
    )


@app.put("/api/order-maker/config")
async def save_order_maker_config(req: OrderMakerConfig):
    db.save_order_maker_config(req.model_dump())
    return req


@app.get("/api/shipping/config")
async def get_shipping_config():
    row = db.get_shipping_config()
    return (
        {k: row[k] for k in ShippingConfig.model_fields}
        if row
        else ShippingConfig()
    )


@app.put("/api/shipping/config")
async def save_shipping_config(req: ShippingConfig):
    db.save_shipping_config(req.model_dump())
    return req



async def run_order_stream(
    cfg: OrderMakerConfig,
    initial_messages: list[dict[str, Any]],
    initial_cart: dict[str, Any],
    on_done: Any,
    emit_start: bool = False,
):
    tools = llm.get_order_maker_tools(
        cfg.search_tool,
        cfg.set_request_tool,
        cfg.set_product_tool,
        cfg.resolve_ambiguity_tool,
    )
    chat_messages: list[dict[str, Any]] = [
        {"role": "system", "content": cfg.system_prompt},
        *initial_messages,
    ]
    cart = dict(initial_cart)
    prompt_tokens = 0
    eval_tokens = 0

    if emit_start:
        yield f"data: {json.dumps({'type': 'start', 'messages': initial_messages, 'cart': cart})}\n\n"

    for _ in range(15):
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": "",
            "thinking": "",
            "tool_calls": [],
        }
        chat_messages.append(msg)
        yield f"data: {json.dumps({'type': 'turn', 'message': msg})}\n\n"

        stream = await llm.chat_stream(
            model=cfg.model,
            messages=chat_messages[:-1],
            tools=tools,
        )
        async for chunk in stream:
            m = chunk.message.model_dump()
            if m.get("thinking"):
                msg["thinking"] += m["thinking"]
            if m.get("content"):
                msg["content"] += m["content"]
            if m.get("tool_calls"):
                msg["tool_calls"].extend(m["tool_calls"])
            if chunk.done:
                p_tok = chunk.prompt_eval_count or 0
                e_tok = chunk.eval_count or 0
                prompt_tokens += p_tok
                eval_tokens += e_tok
                msg["stats"] = {
                    "prompt_tokens": p_tok,
                    "eval_tokens": e_tok,
                }
            yield f"data: {json.dumps({'type': 'assistant', 'message': msg})}\n\n"

        if not msg["tool_calls"]:
            msg["tool_calls"] = None
            break

        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            content = await process_order_tool_call(cfg, name, args, cart)
            tool_msg = {"role": "tool", "tool_name": name, "content": content}
            chat_messages.append(tool_msg)
            yield f"data: {json.dumps({'type': 'tool', 'message': tool_msg, 'cart': cart})}\n\n"

    final_messages = chat_messages[1:]
    extra = on_done(cart, final_messages)
    yield f"data: {json.dumps({'type': 'done', **extra, 'cart': cart, 'messages': final_messages, 'stats': {'prompt_tokens': prompt_tokens, 'eval_tokens': eval_tokens}})}\n\n"


@app.post("/api/order-maker/run")
async def run_order_maker(req: OrderMakerRunRequest):
    def on_done(cart: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        saved_id = db.save_order(
            req.order_id, req.name, req.filename, cart, messages, now
        )
        return {"order_id": saved_id}

    return StreamingResponse(
        run_order_stream(req, req.messages, req.cart, on_done),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/order-maker/orders")
async def create_order_maker_order(req: CreateOrderMakerOrderRequest):
    now = datetime.now(timezone.utc).isoformat()
    msg = email.message_from_string(req.file_content, policy=policy.default)
    sender_email = extract_email_address(msg.get("From", ""))
    nip = db.get_nip_by_email(sender_email) if sender_email else None
    if not nip:
        nip = extract_nip_from_eml(req.file_content)
    return db.create_order_maker_order(
        f"Order: {req.filename}",
        req.filename,
        req.file_content,
        nip,
        sender_email,
        now,
    )


@app.get("/api/order-maker/orders")
async def list_order_maker_orders():
    return {"orders": db.list_order_maker_orders()}


@app.get("/api/order-maker/orders/{order_id}")
async def get_order_maker_order(order_id: int):
    order = db.get_order_maker_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order["from_email"] and order["file_content"]:
        msg = email.message_from_string(order["file_content"], policy=policy.default)
        fallback_email = extract_email_address(msg.get("From", ""))
        if fallback_email:
            order = db.get_order_maker_order(order_id, fallback_sender_email=fallback_email)
    return order


@app.put("/api/order-maker/orders/{order_id}")
async def update_order_maker_order(order_id: int, req: UpdateOrderMakerOrderRequest):
    now = datetime.now(timezone.utc).isoformat()
    sender_email = None
    nip = None
    if req.file_content is not None:
        msg = email.message_from_string(req.file_content, policy=policy.default)
        sender_email = extract_email_address(msg.get("From", ""))
        nip = db.get_nip_by_email(sender_email) if sender_email else None
        if not nip:
            nip = extract_nip_from_eml(req.file_content)

    return db.update_order_maker_order(
        order_id, req.cart, req.filename, req.file_content, sender_email, nip, now
    )


@app.post("/api/companies/connect-email")
async def connect_company_email(req: ConnectEmailRequest):
    clean_email = extract_email_address(req.email)
    if not clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    clean_nip = re.sub(r"\D", "", req.nip)
    now = datetime.now(timezone.utc).isoformat()
    return db.connect_company_email(clean_email, clean_nip, req.order_id, now)


@app.post("/api/companies/disconnect-email")
async def disconnect_company_email(req: DisconnectEmailRequest):
    clean_email = extract_email_address(req.email)
    if not clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    now = datetime.now(timezone.utc).isoformat()
    db.disconnect_company_email(clean_email, req.order_id, now)
    return {"ok": True, "email": clean_email, "is_connected": False}


@app.get("/api/clients")
async def list_clients(nip: str | None = None):
    clean_nip = re.sub(r"\D", "", nip) if nip else None
    return {"clients": db.list_clients(clean_nip)}


@app.post("/api/clients")
async def create_client(req: CreateClientRequest):
    clean_email = extract_email_address(req.email)
    if not clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    clean_nip = re.sub(r"\D", "", req.nip)
    if not is_valid_nip(clean_nip):
        raise HTTPException(status_code=400, detail="Invalid NIP")
    now = datetime.now(timezone.utc).isoformat()
    try:
        return db.create_client(clean_email, clean_nip, now)
    except db.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Client mapping for email {clean_email} already exists",
        )


@app.put("/api/clients/{email:path}")
async def update_client(email: str, req: UpdateClientRequest):
    clean_old_email = extract_email_address(email)
    if not clean_old_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    clean_email = extract_email_address(req.email)
    if not clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    clean_nip = re.sub(r"\D", "", req.nip)
    if not is_valid_nip(clean_nip):
        raise HTTPException(status_code=400, detail="Invalid NIP")
    try:
        client = db.update_client(clean_old_email, clean_email, clean_nip)
    except db.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Client mapping for email {clean_email} already exists",
        )
    if not client:
        raise HTTPException(status_code=404, detail="Client mapping not found")
    return client


@app.delete("/api/clients/{email:path}")
async def delete_client(email: str):
    clean_email = extract_email_address(email)
    if not clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    db.delete_client(clean_email)
    return {"ok": True}


@app.get("/api/companies")
async def list_companies():
    clean_my_nip = re.sub(r"\D", "", config.MY_NIP or "") if config.MY_NIP else None
    return {"companies": db.list_companies(), "my_nip": clean_my_nip}


@app.post("/api/companies")
async def create_company(req: CreateCompanyRequest):
    clean_nip = re.sub(r"\D", "", req.nip)
    if not is_valid_nip(clean_nip):
        raise HTTPException(status_code=400, detail="Invalid NIP")
    now = datetime.now(timezone.utc).isoformat()
    name = req.name.strip() or f"Firma {clean_nip}"
    try:
        return db.create_company(
            clean_nip,
            name,
            req.address.strip(),
            req.zip_code.strip(),
            req.city.strip(),
            req.discount,
            req.deadline,
            now,
        )
    except db.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Company with NIP {clean_nip} already exists")


@app.get("/api/companies/lookup/{nip}")
async def lookup_company(nip: str):
    clean_nip = re.sub(r"\D", "", nip)
    if not is_valid_nip(clean_nip):
        raise HTTPException(status_code=400, detail="Invalid NIP")
    try:
        return await gus.fetch_gus_company(clean_nip)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/companies/{nip}")
async def get_company(nip: str):
    clean_nip = re.sub(r"\D", "", nip)
    company = db.get_company(clean_nip)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.put("/api/companies/{nip}")
async def update_company(nip: str, req: UpdateCompanyRequest):
    clean_nip = re.sub(r"\D", "", nip)
    now = datetime.now(timezone.utc).isoformat()
    company = db.update_company(
        clean_nip,
        req.name.strip(),
        req.address.strip(),
        req.zip_code.strip(),
        req.city.strip(),
        req.discount,
        req.deadline,
        now,
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.delete("/api/companies/{nip}")
async def delete_company(nip: str):
    clean_nip = re.sub(r"\D", "", nip)
    db.delete_company(clean_nip)
    return {"ok": True}


@app.post("/api/order-maker/fetch-company")
async def fetch_company(req: FetchCompanyRequest):
    cfg_row = db.get_order_maker_config()
    model = req.model or (cfg_row["model"] if cfg_row and cfg_row["model"] else "")
    system_prompt = req.system_prompt or (cfg_row["system_prompt"] if cfg_row else DEFAULT_ORDER_SYSTEM_PROMPT)
    tool_name = req.set_company_tool or "set_company_info"

    tools = llm.get_company_tools(tool_name)
    res = await llm.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.content},
        ],
        tools=tools,
    )
    msg = res.message.model_dump()
    tool_calls = msg.get("tool_calls") or []
    company = None
    for tc in tool_calls:
        if tc["function"]["name"] == tool_name:
            args = tc["function"]["arguments"]
            clean_nip = re.sub(r"\D", "", str(args.get("nip", "")))
            name = str(args.get("name", "")).strip()
            address = str(args.get("adress") or args.get("address") or "").strip()
            zip_code = str(args.get("zip_code", "")).strip()
            city = str(args.get("city", "")).strip()
            db.save_company_info(clean_nip, name, address, zip_code, city, req.order_id)
            company = db.get_company(clean_nip)
            break
    if not company:
        raise HTTPException(status_code=400, detail="Could not extract company info")
    return {"ok": True, "company": company, "nip": company["nip"]}


@app.delete("/api/order-maker/orders/{order_id}")
async def delete_order_maker_order(order_id: int):
    db.delete_order_maker_order(order_id)
    return {"ok": True}


@app.get("/api/order-maker/ambiguity-pairs")
async def list_ambiguity_pairs():
    return {"pairs": db.list_ambiguity_pairs()}


@app.post("/api/order-maker/ambiguity-pairs")
async def create_ambiguity_pair(req: CreateAmbiguityPairRequest):
    db.create_ambiguity_pair(req.product_id_a, req.product_id_b, req.chosen_product_id)
    return {"ok": True}


@app.delete("/api/order-maker/ambiguity-pairs/{pair_id}")
async def delete_ambiguity_pair(pair_id: int):
    db.delete_ambiguity_pair(pair_id)
    return {"ok": True}


@app.get("/api/shippings")
async def list_shippings(nip: str | None = None):
    clean_nip = re.sub(r"\D", "", nip) if nip else None
    return {"shippings": db.list_shippings(clean_nip)}


@app.post("/api/shippings")
async def create_shipping(req: CreateShippingRequest):
    clean_nip = re.sub(r"\D", "", req.nip)
    now = datetime.now(timezone.utc).isoformat()
    return db.create_shipping(
        clean_nip,
        req.name.strip(),
        req.address.strip(),
        req.zip_code.strip(),
        req.city.strip(),
        req.phone.strip(),
        req.email.strip(),
        now,
    )


@app.get("/api/shippings/{shipping_id}")
async def get_shipping(shipping_id: int):
    shipping = db.get_shipping(shipping_id)
    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping not found")
    return shipping


@app.put("/api/shippings/{shipping_id}")
async def update_shipping(shipping_id: int, req: UpdateShippingRequest):
    clean_nip = re.sub(r"\D", "", req.nip)
    now = datetime.now(timezone.utc).isoformat()
    shipping = db.update_shipping(
        shipping_id,
        clean_nip,
        req.name.strip(),
        req.address.strip(),
        req.zip_code.strip(),
        req.city.strip(),
        req.phone.strip(),
        req.email.strip(),
        now,
    )
    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping not found")
    return shipping


@app.delete("/api/shippings/{shipping_id}")
async def delete_shipping(shipping_id: int):
    db.delete_shipping(shipping_id)
    return {"ok": True}


@app.post("/api/order-maker/orders/{order_id}/connect-shipping")
async def connect_order_shipping(order_id: int, req: ConnectOrderShippingRequest):
    now = datetime.now(timezone.utc).isoformat()
    return db.connect_order_shipping(order_id, req.shipping_id, now)


@app.post("/api/order-maker/orders/{order_id}/disconnect-shipping")
async def disconnect_order_shipping(order_id: int):
    now = datetime.now(timezone.utc).isoformat()
    db.disconnect_order_shipping(order_id, now)
    return {"ok": True}


def check_woocommerce_config():
    if not config.WOOCOMMERCE_URL or not config.WOOCOMMERCE_CONSUMER_KEY or not config.WOOCOMMERCE_CONSUMER_SECRET:
        raise HTTPException(status_code=500, detail="WooCommerce API is not configured")


async def post_woocommerce_order(
    cart: dict[str, Any],
    company: dict[str, Any] | None,
    shipping: dict[str, Any] | None,
    nip: str | None,
    email_addr: str,
    customer_note: str | None = None,
) -> dict[str, Any]:
    check_woocommerce_config()

    aggregated: dict[int, dict[str, Any]] = {}
    for seg in cart.values():
        for p in seg.get("products", {}).values():
            pid = p["product_id"]
            qty = p.get("amount", 1)
            prod = p.get("product") or {}
            price_cents = prod.get("price_cents")
            tax_class = prod.get("tax_class")
            name = prod.get("name")
            if price_cents is None or tax_class is None or not name:
                db_prod = db.get_product(pid) or db.get_variant(pid)
                if db_prod:
                    price_cents = price_cents if price_cents is not None else db_prod["price_cents"]
                    tax_class = tax_class if tax_class is not None else db_prod["tax_class"]
                    name = name or db_prod.get("name") or db_prod.get("product_name")
            if pid not in aggregated:
                aggregated[pid] = {
                    "product_id": pid,
                    "name": name or f"Product #{pid}",
                    "quantity": qty,
                    "price_cents": price_cents or 0,
                    "tax_class": tax_class if tax_class is not None else 23,
                }
            else:
                aggregated[pid]["quantity"] += qty

    if not aggregated:
        raise HTTPException(status_code=400, detail="Cart has no products")

    discount = company["discount"] if company else 0.0
    line_items = []
    for item in aggregated.values():
        entry: dict[str, Any] = {"product_id": item["product_id"], "quantity": item["quantity"]}
        if item["price_cents"]:
            net_unit_cents = item["price_cents"] * 100 / (100 + item["tax_class"])
            entry["subtotal"] = f"{(net_unit_cents * item['quantity']) / 100:.2f}"
            entry["total"] = f"{(net_unit_cents * (1 - discount / 100) * item['quantity']) / 100:.2f}"
        line_items.append(entry)

    billing = {
        "first_name": "",
        "last_name": "",
        "company": company["name"] if company else (shipping["name"] if shipping else ""),
        "address_1": company["address"] if company else (shipping["address"] if shipping else ""),
        "city": company["city"] if company else (shipping["city"] if shipping else ""),
        "postcode": company["zip_code"] if company else (shipping["zip_code"] if shipping else ""),
        "country": "PL",
        "email": shipping["email"] if shipping and shipping.get("email") else email_addr,
        "phone": shipping["phone"] if shipping and shipping.get("phone") else "",
    }

    shipping_data = {
        "first_name": shipping["name"] if shipping else (company["name"] if company else ""),
        "last_name": "",
        "company": company["name"] if company else "",
        "address_1": shipping["address"] if shipping else (company["address"] if company else ""),
        "city": shipping["city"] if shipping else (company["city"] if shipping else ""),
        "postcode": shipping["zip_code"] if shipping else (company["zip_code"] if company else ""),
        "country": "PL",
        "phone": shipping["phone"] if shipping and shipping.get("phone") else "",
    }

    wc_payload: dict[str, Any] = {
        "customer_id": 1,
        "status": "on-hold",
        "billing": billing,
        "shipping": shipping_data,
        "line_items": line_items,
    }
    if customer_note:
        wc_payload["customer_note"] = customer_note

    fakturownia_inv = None
    if nip:
        resolved_company = company or db.get_company(nip) or {
            "nip": nip,
            "name": shipping["name"] if shipping else "",
            "address": shipping["address"] if shipping else "",
            "zip_code": shipping["zip_code"] if shipping else "",
            "city": shipping["city"] if shipping else "",
            "discount": 0.0,
            "deadline": 0,
        }
        fakturownia_inv = await fakturownia.create_fakturownia_invoice(
            company=resolved_company,
            shipping=shipping,
            nip=nip,
            email_addr=email_addr,
            line_items=list(aggregated.values()),
            customer_note=customer_note,
        )

        meta_data: list[dict[str, Any]] = [
            {"key": "_billing_nip", "value": nip},
            {
                "key": config.FAKTUROWNIA_WOOCOMMERCE_META_KEY,
                "value": {
                    "id": fakturownia_inv["id"],
                    "numer": fakturownia_inv["number"],
                },
            },
        ]
        if fakturownia_inv.get("token"):
            meta_data.append({
                "key": config.FAKTUROWNIA_WOOCOMMERCE_HASH_META_KEY,
                "value": fakturownia_inv["token"],
            })
        wc_payload["meta_data"] = meta_data

    url = f"{config.WOOCOMMERCE_URL.rstrip('/')}/wp-json/wc/v3/orders"
    auth = (config.WOOCOMMERCE_CONSUMER_KEY, config.WOOCOMMERCE_CONSUMER_SECRET)

    async with httpx.AsyncClient() as client:
        res = await client.post(url, auth=auth, json=wc_payload)
        res.raise_for_status()
        wc_order = res.json()

    wc_order_id = wc_order["id"]
    return {
        "woocommerce_order_id": wc_order_id,
        "order_url": f"{config.WOOCOMMERCE_URL.rstrip('/')}/wp-admin/post.php?post={wc_order_id}&action=edit",
        "fakturownia_id": fakturownia_inv["id"] if fakturownia_inv else None,
        "fakturownia_number": fakturownia_inv["number"] if fakturownia_inv else None,
        "fakturownia_url": fakturownia_inv["url"] if fakturownia_inv else None,
    }


@app.post("/api/order-maker/orders/{order_id}/submit-woocommerce")
async def submit_woocommerce_order(
    order_id: int, req: SubmitWooCommerceOrderRequest = SubmitWooCommerceOrderRequest()
):
    check_woocommerce_config()
    order = db.get_order_maker_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    nip = order.get("nip")
    if not nip:
        raise HTTPException(status_code=400, detail="NIP is required to submit order and issue invoice")
    if not req.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required to issue invoice and submit WooCommerce order",
        )

    result = await post_woocommerce_order(
        cart=order.get("cart", {}),
        company=order.get("company"),
        shipping=order.get("shipping"),
        nip=nip,
        email_addr=order.get("from_email") or "",
        customer_note=req.customer_note,
    )

    wc_order_id = result["woocommerce_order_id"]
    now = datetime.now(timezone.utc).isoformat()
    db.set_order_woocommerce_id(order_id, wc_order_id, now)
    if result.get("fakturownia_id"):
        db.set_order_fakturownia_invoice(
            order_id,
            result["fakturownia_id"],
            result["fakturownia_number"],
            result["fakturownia_url"],
            now,
        )

    return {
        "ok": True,
        "woocommerce_id": wc_order_id,
        "woocommerce_order_id": wc_order_id,
        "order_url": result["order_url"],
        "fakturownia_id": result.get("fakturownia_id"),
        "fakturownia_number": result.get("fakturownia_number"),
        "fakturownia_url": result.get("fakturownia_url"),
    }


@app.post("/api/order-maker/fetch-shipping")
async def fetch_shipping(req: FetchShippingRequest):
    cfg_row = db.get_order_maker_config()
    model = req.model or (cfg_row["model"] if cfg_row and cfg_row["model"] else "")
    system_prompt = req.system_prompt or (cfg_row["system_prompt"] if cfg_row else DEFAULT_ORDER_SYSTEM_PROMPT)
    tool_name = req.set_shipping_tool or "set_shipping_info"

    tools = llm.get_shipping_tools(tool_name)
    res = await llm.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.content},
        ],
        tools=tools,
    )
    msg = res.message.model_dump()
    tool_calls = msg.get("tool_calls") or []
    shipping = None
    order_nip = ""
    if req.order_id:
        existing_order = db.get_order_maker_order(req.order_id)
        if existing_order and existing_order.get("nip"):
            order_nip = existing_order["nip"]

    for tc in tool_calls:
        if tc["function"]["name"] == tool_name:
            args = tc["function"]["arguments"]
            clean_nip = re.sub(r"\D", "", str(args.get("nip", ""))) or order_nip
            name = str(args.get("name", "")).strip()
            address = str(args.get("address") or args.get("adress") or "").strip()
            zip_code = str(args.get("zip_code", "")).strip()
            city = str(args.get("city", "")).strip()
            phone = str(args.get("phone", "")).strip()
            email_addr = str(args.get("email", "")).strip()
            shipping = db.save_shipping_info(
                clean_nip, name, address, zip_code, city, phone, email_addr, req.order_id
            )
            break
    if not shipping:
        raise HTTPException(status_code=400, detail="Could not extract shipping info")
    return {"ok": True, "shipping": shipping}


@app.post("/api/shippings/fetch-from-eml")
async def fetch_shipping_from_eml(file: UploadFile):
    with tempfile.NamedTemporaryFile(suffix=".eml") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        markdown = main.md.convert(tmp.name, email_attachment_mode="inline").text_content

    cfg_row = db.get_order_maker_config()
    model = cfg_row["model"] if cfg_row and cfg_row["model"] else ""
    system_prompt = cfg_row["system_prompt"] if cfg_row else DEFAULT_ORDER_SYSTEM_PROMPT
    tool_name = "set_shipping_info"

    tools = llm.get_shipping_tools(tool_name)
    res = await llm.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown},
        ],
        tools=tools,
    )
    msg = res.message.model_dump()
    tool_calls = msg.get("tool_calls") or []
    shipping = None
    for tc in tool_calls:
        if tc["function"]["name"] == tool_name:
            args = tc["function"]["arguments"]
            clean_nip = re.sub(r"\D", "", str(args.get("nip", "")))
            name = str(args.get("name", "")).strip()
            address = str(args.get("address") or args.get("adress") or "").strip()
            zip_code = str(args.get("zip_code", "")).strip()
            city = str(args.get("city", "")).strip()
            phone = str(args.get("phone", "")).strip()
            email_addr = str(args.get("email", "")).strip()
            shipping = db.save_shipping_info(
                clean_nip, name, address, zip_code, city, phone, email_addr
            )
            break
    if not shipping:
        raise HTTPException(status_code=400, detail="Could not extract shipping info")
    return {"ok": True, "shipping": shipping}


@app.post("/api/shippings/extract")
async def extract_shipping(req: ExtractShippingRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    cfg_row = db.get_shipping_config()
    model = cfg_row["model"] if cfg_row and cfg_row["model"] else ""
    if not model:
        order_cfg = db.get_order_maker_config()
        if order_cfg and order_cfg["model"]:
            model = order_cfg["model"]
    system_prompt = (
        cfg_row["system_prompt"]
        if cfg_row and cfg_row["system_prompt"]
        else DEFAULT_SHIPPING_SYSTEM_PROMPT
    )

    res = await llm.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.text},
        ],
        format=ShippingExtractionResult.model_json_schema(),
    )
    result = ShippingExtractionResult.model_validate_json(res.message.content)
    clean_nip = re.sub(r"\D", "", result.nip)
    return {
        "ok": True,
        "shipping": {
            "nip": clean_nip,
            "name": result.name.strip(),
            "address": result.address.strip(),
            "zip_code": result.zip_code.strip(),
            "city": result.city.strip(),
            "phone": result.phone.strip(),
            "email": result.email.strip(),
        },
    }




def attach_woocommerce_url(email_data: dict[str, Any]) -> dict[str, Any]:
    wc_id = email_data.get("woocommerce_id")
    email_data["woocommerce_url"] = (
        f"{config.WOOCOMMERCE_URL.rstrip('/')}/wp-admin/post.php?post={wc_id}&action=edit"
        if wc_id and config.WOOCOMMERCE_URL
        else None
    )
    return email_data


@app.get("/api/emails")
async def list_emails():
    return {"emails": [attach_woocommerce_url(e) for e in db.list_emails()]}


@app.post("/api/emails")
async def create_email(req: CreateEmailRequest):
    now = datetime.now(timezone.utc).isoformat()
    msg = email.message_from_string(req.eml_text, policy=policy.default)
    date = str(msg.get("Date", "")).strip()
    sender = str(msg.get("From", "")).strip()
    recipient = str(msg.get("To", "")).strip()
    title = str(msg.get("Subject", "")).strip()
    nip = resolve_email_nip(req.eml_text, sender, recipient)
    return attach_woocommerce_url(
        db.create_email(req.eml_text, nip, date, sender, recipient, title, now)
    )


@app.get("/api/emails/{email_id}")
async def get_email(email_id: int):
    record = db.get_email(email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email not found")
    msg = email.message_from_string(record["eml_text"], policy=policy.default)
    return attach_woocommerce_url(
        {
            **record,
            **parse_eml_message(msg),
        }
    )


@app.put("/api/emails/{email_id}")
async def update_email(email_id: int, req: UpdateEmailRequest):
    update_nip = "nip" in req.model_fields_set
    update_shipping = "shipping_id" in req.model_fields_set
    update_notes = "notes" in req.model_fields_set
    update_woocommerce_id = "woocommerce_id" in req.model_fields_set
    clean_nip = re.sub(r"\D", "", req.nip) if req.nip else None
    if update_nip and clean_nip and not is_valid_nip(clean_nip):
        raise HTTPException(status_code=400, detail="Invalid NIP")
    updated = db.update_email(
        email_id,
        nip=clean_nip or None,
        shipping_id=req.shipping_id,
        notes=req.notes or "",
        woocommerce_id=req.woocommerce_id,
        update_nip=update_nip,
        update_shipping=update_shipping,
        update_notes=update_notes,
        update_woocommerce_id=update_woocommerce_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Email not found")
    return attach_woocommerce_url(updated)


@app.post("/api/emails/{email_id}/submit-woocommerce")
async def submit_email_woocommerce_order(
    email_id: int, req: SubmitWooCommerceOrderRequest = SubmitWooCommerceOrderRequest()
):
    check_woocommerce_config()
    record = db.get_email(email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email not found")
    if record.get("woocommerce_id"):
        raise HTTPException(status_code=400, detail="Order already submitted to WooCommerce")

    nip = record.get("nip")
    if not nip:
        raise HTTPException(status_code=400, detail="NIP is required to submit order and issue invoice")
    if not req.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required to issue invoice and submit WooCommerce order",
        )

    company = db.get_company(nip)
    shipping = db.get_shipping(record["shipping_id"]) if record.get("shipping_id") else None
    sender = record.get("sender") or ""
    clean_sender_email = extract_email_address(sender) or sender

    result = await post_woocommerce_order(
        cart=record.get("cart", {}),
        company=company,
        shipping=shipping,
        nip=nip,
        email_addr=clean_sender_email,
        customer_note=req.customer_note or record.get("notes") or "",
    )

    wc_order_id = result["woocommerce_order_id"]
    db.set_email_woocommerce_id(email_id, wc_order_id)
    if result.get("fakturownia_id"):
        db.set_email_fakturownia_invoice(
            email_id,
            result["fakturownia_id"],
            result["fakturownia_number"],
            result["fakturownia_url"],
        )

    return {
        "ok": True,
        "woocommerce_id": wc_order_id,
        "woocommerce_order_id": wc_order_id,
        "order_url": result["order_url"],
        "fakturownia_id": result.get("fakturownia_id"),
        "fakturownia_number": result.get("fakturownia_number"),
        "fakturownia_url": result.get("fakturownia_url"),
    }


@app.post("/api/emails/{email_id}/order")
async def run_email_order(email_id: int):
    record = db.get_email(email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email not found")

    markdown = convert_eml_bytes(record["eml_text"].encode("utf-8"))
    notes = record["notes"].strip()
    user_content = f"{markdown}\n\nNotes:\n{notes}" if notes else markdown
    initial_messages = [{"role": "user", "content": user_content}]

    row = db.get_order_maker_config()
    cfg = OrderMakerConfig(**row) if row else OrderMakerConfig()

    def on_done(cart: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
        db.save_email_order(email_id, cart, messages)
        return {}

    return StreamingResponse(
        run_order_stream(cfg, initial_messages, {}, on_done, emit_start=True),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
