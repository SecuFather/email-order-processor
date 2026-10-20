from typing import Any

from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    text: str


class CreateThreadRequest(BaseModel):
    name: str
    model: str
    system_message: str
    tools: str
    user_message: str


class UpdateThreadRequest(BaseModel):
    name: str
    model: str
    system_message: str
    tools: str
    messages: list[dict[str, Any]]


class UpdateProductRequest(BaseModel):
    name: str
    price_cents: int
    prod_cost_cents: int | None = None
    active: bool = True


class UpdateVariantRequest(BaseModel):
    name: str
    price_cents: int = 0
    prod_cost_cents: int | None = None
    stock: int | None = None
    product_name: str | None = None


DEFAULT_ORDER_SYSTEM_PROMPT = """You are an order processing assistant. Your task is to extract requested products from the customer order document and match them to products in the store catalog.

Instructions:
1. Identify each ordered item in the document.
2. For each item at index 0, 1, 2...:
   - Call set_order_text(at, text) with the original requested item description and quantity from the source document.
   - Call search_product(phrase, limit, page) to find matching products in the catalog.
   - If multiple plausible candidates are returned and you need to choose between them, call resolve_ambiguity(ids=[...]) to check stored preference rules.
   - From the search results or resolved ambiguity, pick the best matching product and call set_order_product(at, product_id, amount). If the request corresponds to multiple products (e.g. all puzzles with 60 elements), call set_order_product(at, product_id, amount) for each matching product under the same position index at.
3. If no matching product is found, do not call set_order_product for that index.
"""


class OrderMakerConfig(BaseModel):
    model: str = ""
    system_prompt: str = DEFAULT_ORDER_SYSTEM_PROMPT
    search_tool: str = "search_product"
    set_request_tool: str = "set_order_text"
    set_product_tool: str = "set_order_product"
    search_row_template: str = "{rank}. {name} (ID: {id})"
    search_empty_template: str = "No products found."
    set_text_template: str = "Saved order text at {at}: {text}"
    set_product_template: str = (
        "Set product at {at}: {name} (ID: {product_id}), amount: {amount}"
    )
    set_product_not_found_template: str = "Product {product_id} not found."
    set_product_no_text_template: str = (
        "No order text at {at}. Set order text first."
    )
    resolve_ambiguity_tool: str = "resolve_ambiguity"
    resolve_ambiguity_template: str = (
        "Resolved ambiguity: chosen product is {name} (ID: {id})"
    )
    resolve_ambiguity_none_template: str = (
        "No ambiguity rule found for IDs: {ids}."
    )


class OrderMakerRunRequest(OrderMakerConfig):
    messages: list[dict[str, Any]]
    cart: dict[str, dict[str, Any]] = {}
    order_id: int | None = None
    name: str | None = None
    filename: str | None = None


class CreateAmbiguityPairRequest(BaseModel):
    product_id_a: int
    product_id_b: int
    chosen_product_id: int


class CreateOrderMakerOrderRequest(BaseModel):
    filename: str
    file_content: str


class UpdateOrderMakerOrderRequest(BaseModel):
    cart: dict[str, Any] | None = None
    filename: str | None = None
    file_content: str | None = None


class CreateCompanyRequest(BaseModel):
    nip: str
    name: str = ""
    address: str = ""
    zip_code: str = ""
    city: str = ""
    discount: float = 0.0
    deadline: int = 0


class UpdateCompanyRequest(BaseModel):
    name: str
    address: str
    zip_code: str
    city: str
    discount: float = 0.0
    deadline: int = 0


class ConnectEmailRequest(BaseModel):
    email: str
    nip: str
    order_id: int | None = None


class DisconnectEmailRequest(BaseModel):
    email: str
    order_id: int | None = None


class CreateClientRequest(BaseModel):
    email: str
    nip: str


class UpdateClientRequest(BaseModel):
    email: str
    nip: str


class FetchCompanyRequest(BaseModel):
    order_id: int | None = None
    content: str
    model: str = ""
    system_prompt: str = ""
    set_company_tool: str = "set_company_info"


class CreateShippingRequest(BaseModel):
    nip: str = ""
    name: str
    address: str
    zip_code: str
    city: str
    phone: str = ""
    email: str = ""


class UpdateShippingRequest(BaseModel):
    nip: str = ""
    name: str
    address: str
    zip_code: str
    city: str
    phone: str = ""
    email: str = ""


class ConnectOrderShippingRequest(BaseModel):
    shipping_id: int


class FetchShippingRequest(BaseModel):
    order_id: int | None = None
    content: str
    model: str = ""
    system_prompt: str = ""
    set_shipping_tool: str = "set_shipping_info"


class SubmitWooCommerceOrderRequest(BaseModel):
    customer_note: str | None = None
    confirmed: bool = False


class CreateEmailRequest(BaseModel):
    eml_text: str


class UpdateEmailRequest(BaseModel):
    nip: str | None = None
    shipping_id: int | None = None
    notes: str | None = None
    woocommerce_id: int | None = None


DEFAULT_SHIPPING_SYSTEM_PROMPT = """You are a shipping address extraction assistant. Your task is to extract delivery address and contact details from the provided text into structured JSON.

Extract the following fields:
- nip: Polish tax identification number (NIP) if present, digits only. Empty string if not present.
- name: Recipient name, person name, or company/facility name.
- address: Street address including street name, building number, and apartment/suite number if present.
- zip_code: Postal/ZIP code (e.g. 00-000).
- city: City or locality name.
- phone: Contact phone number if present. Empty string if not present.
- email: Contact email address if present. Empty string if not present.
"""


class ShippingConfig(BaseModel):
    model: str = ""
    system_prompt: str = DEFAULT_SHIPPING_SYSTEM_PROMPT


class ExtractShippingRequest(BaseModel):
    text: str


class ShippingExtractionResult(BaseModel):
    nip: str = ""
    name: str = ""
    address: str = ""
    zip_code: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""



