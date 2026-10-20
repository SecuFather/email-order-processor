import type { Shipping, ShippingsResponse } from "../types/shipping";

export async function fetchShippings(nip?: string): Promise<ShippingsResponse> {
  const url = nip ? `/api/shippings?nip=${encodeURIComponent(nip)}` : "/api/shippings";
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch shipping addresses");
  }
  return res.json();
}

export async function createShipping(
  data: Omit<Shipping, "id" | "created_at" | "updated_at" | "company_name">
): Promise<Shipping> {
  const res = await fetch("/api/shippings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create shipping address");
  }
  return res.json();
}

export async function updateShipping(
  id: number,
  data: Omit<Shipping, "id" | "created_at" | "updated_at" | "company_name">
): Promise<Shipping> {
  const res = await fetch(`/api/shippings/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update shipping address");
  }
  return res.json();
}

export async function deleteShipping(id: number): Promise<void> {
  const res = await fetch(`/api/shippings/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete shipping address");
  }
}

export async function extractShippingFromText(
  text: string
): Promise<Omit<Shipping, "id" | "created_at" | "updated_at" | "company_name">> {
  const res = await fetch("/api/shippings/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to extract shipping information");
  }
  const data = await res.json();
  return data.shipping;
}

