import type { OrderMakerConfigData } from "../types/orderConfig";

export async function fetchOrderConfig(): Promise<OrderMakerConfigData> {
  const res = await fetch("/api/order-maker/config");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch order configuration");
  }
  return res.json();
}

export async function saveOrderConfig(
  config: OrderMakerConfigData
): Promise<OrderMakerConfigData> {
  const res = await fetch("/api/order-maker/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to save order configuration");
  }
  return res.json();
}
