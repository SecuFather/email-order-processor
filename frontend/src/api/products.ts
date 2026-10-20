import type { Product, ProductsResponse, SyncWooCommerceResponse } from "../types/product";

export async function fetchProducts(): Promise<ProductsResponse> {
  const res = await fetch("/api/products");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch products");
  }
  return res.json();
}

export async function updateProduct(
  id: number,
  data: {
    name: string;
    price_cents: number;
    prod_cost_cents: number | null;
    active: boolean;
  }
): Promise<Product> {
  const res = await fetch(`/api/products/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Failed to update product #${id}`);
  }
  return res.json();
}

export async function syncWooCommerce(): Promise<SyncWooCommerceResponse> {
  const res = await fetch("/api/woocommerce/sync", { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to sync with WooCommerce");
  }
  return res.json();
}

export async function resetWooCommerceSync(): Promise<void> {
  const res = await fetch("/api/woocommerce/reset-sync", { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to reset sync");
  }
}

export async function deleteAllProducts(): Promise<void> {
  const res = await fetch("/api/products", { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete products");
  }
}
