import type { ShippingConfigData } from "../types/shippingConfig";

export async function fetchShippingConfig(): Promise<ShippingConfigData> {
  const res = await fetch("/api/shipping/config");
  if (!res.ok) throw new Error("Failed to fetch shipping configuration");
  return res.json();
}

export async function saveShippingConfig(
  config: ShippingConfigData
): Promise<ShippingConfigData> {
  const res = await fetch("/api/shipping/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to save shipping configuration");
  return res.json();
}
