# Edu1 System Philosophy & Architectural Vision

## 1. Executive Purpose & Vision

**Edu1 ("Order Manager")** is a lean, highly focused e-commerce order automation and catalog management platform. Its primary mission is to automate the ingestion, resolution, and submission of B2B/B2C purchase orders arriving via email and document attachments into WooCommerce, powered by local LLMs (Ollama) and a streamlined single-page React frontend.

The system bridges unstructured customer communication (emails, PDFs, spreadsheets, scans, Google Docs) with structured store catalog data, customer master data (NIP tax IDs, discounts, payment deadlines), and automated WooCommerce administrative order creation.

---

## 2. Core Business Domains & Author Goals

1. **Email & Document Ingestion**:
   - Ingest `.eml` and `.msg` files.
   - Transform attachments and Google Doc/Sheet links into clean Markdown using `markitdown`.
   - Automatically extract Polish NIP identifiers (with mathematical checksum validation) and sender email addresses.

2. **Entity Resolution & Data Federation**:
   - Map client emails to corporate tax identifiers (NIP) through `company_emails`.
   - Maintain company profiles with payment terms (`deadline`) and negotiated percentage discounts (`discount`).
   - Associate multiple shipping destinations per company/order.
   - Disambiguate catalog matches through human-configured pairwise preference rules (`ambiguity_pairs`).

3. **Store Catalog Synchronization**:
   - Bi-directionally align catalog state with WooCommerce REST API (`wp-json/wc/v3`).
   - Track incremental changes via timestamp bookmarks (`last_sync_date`).
   - Manage top-level products and variant hierarchies with cost tracking (`_prod_cost`) and inventory levels.

4. **Agentic LLM Order Processing**:
   - Empower local Ollama models to process orders through deterministic tool calling (`search_product`, `set_order_text`, `set_order_product`, `resolve_ambiguity`).
   - Stream the LLM reasoning, thoughts, and cart state in real-time to the operator via Server-Sent Events (SSE).
   - Submit finished orders directly into WooCommerce as admin-level on-hold orders with calculated net pricing and customer discount percentages.

5. **Single-Page Administrative Cockpit**:
   - Responsive, dark-themed React 19 interface without heavyweight UI component libraries.
   - Instant inline editing with clean discard/save flows.
   - Centralized error tracking and alerting via an event log tab.

---

## 3. Guiding Architectural Principles

### Boundary Isolation (Non-Negotiable)
- **`api.py`** is the sole owner of `fastapi` and transport concerns.
- **`db.py`** is the sole owner of `sqlite3`, SQL queries, table schemas, and row serialization.
- **`config.py`** is the sole owner of `dotenv`, `os.environ`, and environment variables.
- **`llm.py`** is the sole owner of `ollama` SDK calls and tool schema definitions.
- **`main.py`** encapsulates domain logic, text processing, and server bootstrapper.
- **`schemas.py`** is purely Pydantic models with zero framework or database entanglements.

### Code Quality Tenets (From AGENTS.md)
1. **No Defensive Programming**:
   - Reject speculative fallbacks, unnecessary `try/except` blocks, defensive `None`/null checks where invariants guarantee values, or wrapper shims.
   - Errors should fail cleanly and noticeably rather than being silently swallowed or masked.
2. **No Redundant Code**:
   - Eliminate duplicate operations, repeated transformations (e.g., redundant `.lower()`, `.strip()`, regex recompilation), and dead/unreachable branches.
   - Keep implementations minimal, direct, and readable.
3. **Radical Simplicity**:
   - Prefer standard language constructs and lightweight dependencies over complex abstractions.
   - Keep data flows unidirectional and transparent.

---

## 4. Evaluation Rubric for Every Expression & Code Block

When auditing each expression and block in the codebase:
1. **Necessity & Simplification**: Does this expression/block directly serve the author's vision or domain invariants? Can it be expressed in fewer operations or simpler primitives?
2. **Elimination & Refactoring Action**: What exact steps would remove or simplify it without losing required business capabilities?
3. **Consequences & Blast Radius**: Does removing or simplifying it break contracts, tests, UI reactivity, or architectural boundaries?
4. **Final Decision**: Keep as-is, Simplify, or Remove.
