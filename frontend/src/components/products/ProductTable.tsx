import { createDraftFromProduct, type Product, type ProductDraft } from "../../types/product";
import { ProductRow } from "./ProductRow";

type ProductTableProps = {
  products: Product[];
  drafts: Record<number, ProductDraft>;
  modifiedProductIds?: number[];
  isLoading: boolean;
  totalProductsCount: number;
  onUpdateDraft: (id: number, partial: Partial<ProductDraft>) => void;
  showProductNameInsteadOfActive?: boolean;
  onBlurSave?: (id: number) => void;
  emptyMessage?: string;
  loadingMessage?: string;
};

export function ProductTable({
  products,
  drafts,
  modifiedProductIds = [],
  isLoading,
  totalProductsCount,
  onUpdateDraft,
  showProductNameInsteadOfActive,
  onBlurSave,
  emptyMessage,
  loadingMessage,
}: ProductTableProps) {
  if (isLoading && totalProductsCount === 0) {
    return (
      <div className="py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-2xl">
        {loadingMessage || "Loading products..."}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-2xl">
        {emptyMessage ||
          (totalProductsCount === 0
            ? "No products found. Click 'Sync WooCommerce' to import products."
            : "No products match the filter.")}
      </div>
    );
  }

  const modifiedSet = new Set(modifiedProductIds);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950/70 text-xs uppercase text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-3 w-16">Image</th>
              <th className="py-3 px-3 w-20">ID</th>
              <th className="py-3 px-3 min-w-[260px]">
                {showProductNameInsteadOfActive ? "Variant Name" : "Product Name"}
              </th>
              <th className="py-3 px-3 w-28">Price</th>
              <th className="py-3 px-3 w-28">Cost</th>
              <th className="py-3 px-3 w-24">Stock</th>
              <th className="py-3 px-3 min-w-[140px]">
                {showProductNameInsteadOfActive ? "Product Name" : "Active"}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {products.map((p) => {
              const draft = drafts[p.id] || createDraftFromProduct(p);
              const isModified = modifiedSet.has(p.id);

              return (
                <ProductRow
                  key={p.id}
                  product={p}
                  draft={draft}
                  isModified={isModified}
                  onUpdateDraft={onUpdateDraft}
                  showProductNameInsteadOfActive={showProductNameInsteadOfActive}
                  onBlurSave={onBlurSave}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
