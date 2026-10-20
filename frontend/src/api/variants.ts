import type { Product } from "../types/product";

export async function fetchVariants(): Promise<{ variants: Product[] }> {
  const res = await fetch("/api/variants");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch variants");
  }
  return res.json();
}

export async function updateVariant(
  id: number,
  data: {
    name: string;
    price_cents?: number;
    prod_cost_cents?: number | null;
    stock?: number | null;
    product_name?: string;
  }
): Promise<Product> {
  const res = await fetch(`/api/variants/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Failed to update variant #${id}`);
  }
  return res.json();
}

export async function deleteAllVariants(): Promise<void> {
  const res = await fetch("/api/variants", { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete variants");
  }
}
