import { useEffect, useMemo, useState } from "react";
import type { LogEntry } from "../../types/log";
import {
  createDraftFromProduct,
  isProductModified,
  type Product,
  type ProductActiveFilter,
  type ProductDraft,
} from "../../types/product";
import {
  deleteAllProducts,
  fetchProducts,
  resetWooCommerceSync,
  syncWooCommerce,
  updateProduct,
} from "../../api/products";
import { ProductToolbar } from "./ProductToolbar";
import { ProductTable } from "./ProductTable";

type ProductsTabProps = {
  activeFilter?: ProductActiveFilter;
  onFilterChange?: (filter: ProductActiveFilter) => void;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function ProductsTab({
  activeFilter,
  onFilterChange,
  onAddLog,
}: ProductsTabProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [drafts, setDrafts] = useState<Record<number, ProductDraft>>({});
  const [isSavingAll, setIsSavingAll] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [internalFilter, setInternalFilter] =
    useState<ProductActiveFilter>("active");
  const productActiveFilter = activeFilter ?? internalFilter;
  const setProductActiveFilter = onFilterChange ?? setInternalFilter;

  useEffect(() => {
    loadProducts();
  }, []);

  function initDrafts(prods: Product[]) {
    const d: Record<number, ProductDraft> = {};
    for (const p of prods) {
      d[p.id] = createDraftFromProduct(p);
    }
    setDrafts(d);
  }

  function handleUpdateDraft(id: number, partial: Partial<ProductDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), ...partial },
    }));
  }

  async function loadProducts() {
    setIsLoading(true);
    try {
      const data = await fetchProducts();
      setProducts(data.products);
      initDrafts(data.products);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load products";
      onAddLog({
        level: "error",
        title: "Failed to load products",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  const modifiedProductIds = useMemo(() => {
    return products
      .filter((p) => isProductModified(p, drafts[p.id]))
      .map((p) => p.id);
  }, [products, drafts]);

  const searchLower = productSearch.toLowerCase();
  const activeCount = useMemo(() => {
    return products.filter((p) => (drafts[p.id]?.active ?? p.active)).length;
  }, [products, drafts]);

  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      const d = drafts[p.id];
      const active = d !== undefined ? d.active : p.active;
      if (productActiveFilter === "active" && !active) return false;
      if (productActiveFilter === "inactive" && active) return false;
      if (searchLower) {
        const name = d !== undefined ? d.name : p.name;
        return (
          name.toLowerCase().includes(searchLower) ||
          String(p.id).includes(searchLower)
        );
      }
      return true;
    });
  }, [products, drafts, productActiveFilter, searchLower]);

  async function handleSaveAllChanges() {
    if (modifiedProductIds.length === 0 || isSavingAll) return;
    setIsSavingAll(true);
    try {
      const updates = modifiedProductIds.map(async (id) => {
        const d = drafts[id];
        const priceCents = Math.round(parseFloat(d.price || "0") * 100);
        const costCents =
          d.prod_cost.trim() === ""
            ? null
            : Math.round(parseFloat(d.prod_cost) * 100);
        return updateProduct(id, {
          name: d.name,
          price_cents: priceCents,
          prod_cost_cents: costCents,
          active: d.active,
        });
      });
      const updatedProducts = await Promise.all(updates);
      setProducts((prev) => {
        const map = new Map(updatedProducts.map((p) => [p.id, p]));
        const next = prev.map((p) => map.get(p.id) || p);
        initDrafts(next);
        return next;
      });
      setSyncMsg(`Saved ${updatedProducts.length} product(s)!`);
      onAddLog({
        level: "info",
        title: "Products saved",
        message: `Successfully saved ${updatedProducts.length} product(s)`,
      });
      setTimeout(() => setSyncMsg(""), 4000);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save products";
      onAddLog({
        level: "error",
        title: "Failed to save products",
        message,
      });
    } finally {
      setIsSavingAll(false);
    }
  }

  function handleDiscardAllChanges() {
    initDrafts(products);
  }

  async function handleSyncProducts() {
    setIsSyncing(true);
    setSyncMsg("");
    try {
      const data = await syncWooCommerce();
      await loadProducts();
      const msg = data.has_more
        ? `Synced 100 products (+${data.synced_count} new). More available — sync again.`
        : `Sync complete (+${data.synced_count} new)`;
      setSyncMsg(msg);
      onAddLog({
        level: "info",
        title: "WooCommerce synced",
        message: msg,
      });
      setTimeout(() => setSyncMsg(""), 4000);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to sync WooCommerce products";
      onAddLog({
        level: "error",
        title: "WooCommerce sync failed",
        message,
      });
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleResetSync() {
    try {
      await resetWooCommerceSync();
      setSyncMsg("Sync date reset — click 'Sync WooCommerce' to resync");
      onAddLog({
        level: "info",
        title: "Sync date reset",
        message:
          "WooCommerce sync date was reset. Next sync will check all products from the beginning.",
      });
      setTimeout(() => setSyncMsg(""), 5000);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to reset sync date";
      onAddLog({
        level: "error",
        title: "Reset sync failed",
        message,
      });
    }
  }

  async function handleDeleteAllProducts() {
    if (
      !window.confirm(
        "Are you sure you want to remove all products? This will also reset the sync date."
      )
    ) {
      return;
    }
    try {
      await deleteAllProducts();
      setProducts([]);
      setDrafts({});
      setSyncMsg("All products removed");
      onAddLog({
        level: "info",
        title: "All products removed",
        message: "Database products cleared and sync date reset",
      });
      setTimeout(() => setSyncMsg(""), 4000);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete all products";
      onAddLog({
        level: "error",
        title: "Failed to delete products",
        message,
      });
    }
  }

  return (
    <div className="w-full space-y-6">
      <ProductToolbar
        search={productSearch}
        onSearchChange={setProductSearch}
        activeFilter={productActiveFilter}
        onFilterChange={setProductActiveFilter}
        syncMsg={syncMsg}
        isSavingAll={isSavingAll}
        modifiedCount={modifiedProductIds.length}
        onSaveAll={handleSaveAllChanges}
        onDiscardAll={handleDiscardAllChanges}
        isSyncing={isSyncing}
        onSync={handleSyncProducts}
        onResetSync={handleResetSync}
        totalProductsCount={products.length}
        filteredCount={filteredProducts.length}
        activeCount={activeCount}
        onDeleteAll={handleDeleteAllProducts}
      />

      <ProductTable
        products={filteredProducts}
        drafts={drafts}
        modifiedProductIds={modifiedProductIds}
        isLoading={isLoading}
        totalProductsCount={products.length}
        onUpdateDraft={handleUpdateDraft}
      />
    </div>
  );
}
