export type Product = {
  id: number;
  name: string;
  price_cents: number;
  tax_class: number;
  prod_cost_cents: number | null;
  image_src: string | null;
  active: boolean;
  permalink: string | null;
  stock_quantity: number | null;
  product_name?: string;
};

export type ProductDraft = {
  name: string;
  price: string;
  prod_cost: string;
  active: boolean;
};

export type ProductsResponse = {
  products: Product[];
};

export type SyncWooCommerceResponse = {
  last_sync_date: string | null;
  synced_count: number;
  has_more: boolean;
};

export type ProductActiveFilter = "all" | "active" | "inactive";

export function createDraftFromProduct(p: Product): ProductDraft {
  return {
    name: p.name || "",
    price: p.price_cents ? (p.price_cents / 100).toFixed(2) : "0.00",
    prod_cost: p.prod_cost_cents != null ? (p.prod_cost_cents / 100).toFixed(2) : "",
    active: Boolean(p.active),
  };
}

export function isProductModified(p: Product, d?: ProductDraft): boolean {
  if (!d) return false;
  const origPrice = p.price_cents ? (p.price_cents / 100).toFixed(2) : "0.00";
  const origCost = p.prod_cost_cents != null ? (p.prod_cost_cents / 100).toFixed(2) : "";
  return (
    d.name !== (p.name || "") ||
    d.price !== origPrice ||
    d.prod_cost !== origCost ||
    d.active !== Boolean(p.active)
  );
}
