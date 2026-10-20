# Edu1

Single-server FastAPI + React 19 application over HTTPS with Tailscale TLS certificates.

## Endpoints
- `POST /api/convert-eml` — Converts `.eml` / `.msg` files to Markdown using `markitdown` + `markitdown-email-plugin`.
- `POST /api/parse-eml` — Parses `.eml` files into headers, HTML body, and base64-encoded attachments for native frontend viewing.
- `POST /api/normalize` — Applies `unidecode`, lowercases, strips special characters, and removes words shorter than 4 characters unless they contain digits.
- `GET /api/threads` — Lists saved playground threads from SQLite.
- `POST /api/threads` — Creates a new thread, parses Python tool signatures from the system message, and runs Ollama.
- `PUT /api/threads/{thread_id}` — Updates thread steps/settings in SQLite and runs Ollama.
- `POST /api/threads/{thread_id}/fork` — Duplicates a thread in SQLite.
- `DELETE /api/threads/{thread_id}` — Deletes a thread.
- `POST /api/woocommerce/sync` — Synchronizes up to 100 oldest-modified products since last sync date from WooCommerce and inserts new products into SQLite.
- `GET /api/products` — Lists all products with active status from SQLite.
- `GET /api/products/search` — Searches active products by normalized name matching words with fallback across pages (`phrase`, `limit`, `page`).
- `PUT /api/products/{product_id}` — Updates editable parameters of a product (`name`, `price_cents`, `prod_cost_cents`, `active`).
- `DELETE /api/products` — Removes all products and resets last sync date.
- `GET /api/variants` — Lists all variants (id, name, stock) from SQLite.
- `PUT /api/variants/{variant_id}` — Updates editable parameters of a variant (name, stock).
- `DELETE /api/variants` — Removes all variants from SQLite.
- `POST /api/woocommerce/reset-sync` — Resets last WooCommerce sync date to allow resyncing all items and stock from beginning.
- `POST /api/order-maker/orders/{order_id}/submit-woocommerce` — Submits order to WooCommerce as admin with on-hold status and net prices.

## Deploy & Run from Target Directory

1. Create `.env` in your target directory (see `.env.example`):
   ```dotenv
   TAILSCALE_DOMAIN=your-device.your-tailnet.ts.net
   SSL_CERTFILE=tailscale.crt
   SSL_KEYFILE=tailscale.key
   HOST=0.0.0.0
   PORT=8443
   OLLAMA_HOST=http://127.0.0.1:11434
   ```

2. Deploy:
   ```bash
   ./deploy.sh /path/to/target-dir
   ```

3. Run from target directory:
   ```bash
   cd /path/to/target-dir
   uv run python main.py
   ```
