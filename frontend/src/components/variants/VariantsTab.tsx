import { useEffect, useMemo, useState } from "react";
import type { LogEntry } from "../../types/log";
import {
  createDraftFromProduct,
  isProductModified,
  type Product,
  type ProductActiveFilter,
  type ProductDraft,
} from "../../types/product";
import { fetchVariants, updateVariant } from "../../api/variants";
import { ProductTable } from "../products/ProductTable";

type VariantsTabProps = {
  activeFilter?: ProductActiveFilter;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function VariantsTab({
  activeFilter = "active",
  onAddLog,
}: VariantsTabProps) {
  const [variants, setVariants] = useState<Product[]>([]);
  const [drafts, setDrafts] = useState<Record<number, ProductDraft>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadVariants();
  }, []);

  function initDrafts(vars: Product[]) {
    const d: Record<number, ProductDraft> = {};
    for (const v of vars) {
      d[v.id] = createDraftFromProduct(v);
    }
    setDrafts(d);
  }

  function handleUpdateDraft(id: number, partial: Partial<ProductDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), ...partial },
    }));
  }

  async function loadVariants() {
    setIsLoading(true);
    try {
      const data = await fetchVariants();
      setVariants(data.variants);
      initDrafts(data.variants);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load variants";
      onAddLog({
        level: "error",
        title: "Failed to load variants",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  const filteredVariants = useMemo(() => {
    return variants.filter((v) => {
      const d = drafts[v.id];
      const active = d !== undefined ? d.active : v.active;
      if (activeFilter === "active" && !active) return false;
      if (activeFilter === "inactive" && active) return false;
      return true;
    });
  }, [variants, drafts, activeFilter]);

  async function handleBlurSave(id: number) {
    const orig = variants.find((v) => v.id === id);
    const draft = drafts[id];
    if (!orig || !draft || !isProductModified(orig, draft)) return;

    try {
      const priceCents = Math.round(parseFloat(draft.price || "0") * 100);
      const costCents =
        draft.prod_cost.trim() === ""
          ? null
          : Math.round(parseFloat(draft.prod_cost) * 100);

      const updated = await updateVariant(id, {
        name: draft.name,
        price_cents: priceCents,
        prod_cost_cents: costCents,
        stock: orig.stock_quantity,
        product_name: orig.product_name,
      });

      setVariants((prev) => prev.map((v) => (v.id === id ? updated : v)));
      setDrafts((prev) => ({ ...prev, [id]: createDraftFromProduct(updated) }));
      onAddLog({
        level: "info",
        title: "Variant updated",
        message: `Updated variant #${id} (${draft.name})`,
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to update variant #${id}`;
      onAddLog({
        level: "error",
        title: "Failed to update variant",
        message,
      });
    }
  }

  return (
    <div className="w-full">
      <ProductTable
        products={filteredVariants}
        drafts={drafts}
        isLoading={isLoading}
        totalProductsCount={filteredVariants.length}
        onUpdateDraft={handleUpdateDraft}
        showProductNameInsteadOfActive={true}
        onBlurSave={handleBlurSave}
        emptyMessage={
          variants.length === 0
            ? "No variants found. Sync WooCommerce in the Products tab to import variants."
            : "No variants match the active filter."
        }
        loadingMessage="Loading variants..."
      />
    </div>
  );
}
