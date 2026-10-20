# Architecture

## Overview

This project is a single-server application providing an API backend alongside a React 19 frontend served over HTTPS.

The backend is split into six distinct layers:
1. **API / Transport Layer (`api.py`)**
2. **Domain & Core Logic Layer (`main.py`)**
3. **LLM & Tool Definition Layer (`llm.py`)**
4. **Data Validation & Schemas Layer (`schemas.py`)**
5. **Persistence & Database Layer (`db.py`)**
6. **Configuration Layer (`config.py`)**

---

## Architectural Principles & Boundaries

### 1. Web Framework Isolation (FastAPI)

> [!IMPORTANT]
> **`api.py` is the only application module permitted to reference or import `fastapi`.**
> No other application source file (such as `main.py` or `db.py`) may import or depend on `fastapi`.

- **`api.py`**:
  - Owns the `FastAPI` instance (`app = FastAPI()`).
  - Defines all HTTP route handlers (`GET`, `POST`, `PUT`, `DELETE`).
  - Handles transport-level primitives: `UploadFile`, `StreamingResponse`, `HTTPException`, and `StaticFiles` mounting.
  - Translates incoming HTTP requests into domain and database operations and formats HTTP responses.

### 2. Database Isolation (SQLite)

> [!IMPORTANT]
> **`db.py` is the only application module permitted to reference or import `sqlite3`.**
> No other application source file (such as `main.py` or `api.py`) may import or depend on `sqlite3`.

- **`db.py`**:
  - Encapsulates database connection creation (`get_db()`), schemas, and migrations.
  - Houses all SQL queries and operations across threads, products, WooCommerce sync, Order Maker config, orders, ambiguity pairs, companies, and company emails.
  - Serializes database rows into domain dictionaries (`serialize_company`, `serialize_product`, `serialize_thread`).

### 3. Domain & Core Logic (`main.py`)

- Fully decoupled from both `fastapi` and `sqlite3`, as well as `ollama`.
- Implements text processing (`normalize_text`), Polish NIP validation/extraction (`is_valid_nip`, `extract_nip_from_eml`), email address extraction, document conversions, product search, and order tool call execution (`process_order_tool_call`).
- Acts as the application entry point (`python main.py`), invoking `uvicorn.run("api:app", ...)`.

### 4. LLM & Tool Definition Layer (`llm.py`)

> [!IMPORTANT]
> **`llm.py` is the only application module permitted to reference or import `ollama`.**
> No other application source file (such as `main.py` or `api.py`) may import or depend on `ollama`.

- **`llm.py`**:
  - Encapsulates Ollama `AsyncClient` communication (`list_models`, `chat`, `chat_stream`, `run_ollama`).
  - Defines all function/tool schemas (`get_order_maker_tools`, `get_company_tools`, `parse_tools`).
  - Strict schema policy: tool definitions contain no `"description"` fields at function or parameter levels.

### 5. Data Validation & Schemas (`schemas.py`)

- Hosts Pydantic models for request payloads, configurations, and data validation schemas.
- Self-contained and isolated from database operations, web framework dependencies, and environment configuration.

### 6. Configuration & Environment Variable Isolation (dotenv / os.environ)

> [!IMPORTANT]
> **`config.py` is the only application module permitted to reference `dotenv` / `load_dotenv` or fetch environment variables (`os.environ` / `os.getenv`).**
> No other application source file (such as `main.py`, `api.py`, or `db.py`) may load dotenv or read environment variables directly.

- **`config.py`**:
  - Executes `load_dotenv()` on load.
  - Exposes configuration variables (`HOST`, `PORT`, `SSL_CERTFILE`, `SSL_KEYFILE`, `OLLAMA_HOST`, `WOOCOMMERCE_URL`, `WOOCOMMERCE_CONSUMER_KEY`, `WOOCOMMERCE_CONSUMER_SECRET`, `MY_NIP`, `DB_PATH`).
  - Sets standard defaults where applicable (e.g. `DB_PATH="threads.db"`).

### 7. Testing Boundary

- Test suites (located in `tests/`) test API functionality by importing the ASGI application (`from api import app`) and using `fastapi.testclient.TestClient`.
- Domain unit tests import directly from `main.py`.
- LLM and tool tests import directly from `llm.py`.
- Tests requiring database state inspection import `get_db` directly from `db.py`.
- Automated architectural test checks enforce:
  - `fastapi` is not imported anywhere outside `api.py`.
  - `sqlite3` is not imported anywhere outside `db.py`.
  - `dotenv` is not imported anywhere outside `config.py`.
  - `os.environ` and `os.getenv` are not accessed anywhere outside `config.py`.
  - `ollama` is not imported anywhere outside `llm.py`.

---

## Component Layout

```
.
├── api.py           # FastAPI application, route declarations, HTTP handlers
├── main.py          # Domain logic, server launcher
├── llm.py           # Ollama client communication, tool schemas (no descriptions)
├── schemas.py       # Pydantic request models, config schemas
├── db.py            # SQLite connection, schema, queries, serializers
├── config.py        # Centralized configuration and environment variable access
├── gus.py           # GUS BIR API client
├── fakturownia.py   # Fakturownia API invoicing client
├── deploy.sh        # Deployment script (bundles api.py, main.py, llm.py, schemas.py, db.py, config.py, gus.py, fakturownia.py, frontend/dist)
├── frontend/        # React 19 client application
└── tests/           # Integration, unit, and architectural boundary tests
```

---

## Deployment & Execution

- **Development / Direct Run**:
  ```bash
  uv run python main.py
  ```
  `main.py` reads configuration parameters from `config.py` and runs Uvicorn targeting `"api:app"`.

- **Deployment (`deploy.sh`)**:
  Copies `main.py`, `api.py`, `schemas.py`, `db.py`, `config.py`, `llm.py`, `gus.py`, `fakturownia.py`, `pyproject.toml`, `uv.lock`, `.python-version`, and `frontend/dist` to the target server environment.
