import type { Product, ProductDraft } from "../../types/product";

type ProductRowProps = {
  product: Product;
  draft: ProductDraft;
  isModified: boolean;
  onUpdateDraft: (id: number, partial: Partial<ProductDraft>) => void;
  showProductNameInsteadOfActive?: boolean;
  onBlurSave?: (id: number) => void;
};

export function ProductRow({
  product,
  draft,
  isModified,
  onUpdateDraft,
  showProductNameInsteadOfActive,
  onBlurSave,
}: ProductRowProps) {
  return (
    <tr
      className={`transition-colors ${
        isModified
          ? "bg-indigo-950/20 hover:bg-indigo-950/30"
          : "hover:bg-slate-800/40"
      }`}
    >
      {/* Image - Click on image redirects to shop */}
      <td className="py-2.5 px-3">
        <a
          href={product.permalink || undefined}
          target={product.permalink ? "_blank" : undefined}
          rel={product.permalink ? "noopener noreferrer" : undefined}
          className={`relative block w-14 h-14 rounded-lg overflow-hidden bg-slate-950 border group shrink-0 ${
            isModified ? "border-indigo-500/80" : "border-slate-800"
          } ${
            product.permalink
              ? "cursor-pointer hover:border-indigo-400"
              : "cursor-default"
          }`}
          title={
            product.permalink
              ? "Click on image to open product page in shop ↗"
              : "No shop link available"
          }
        >
          {product.image_src ? (
            <img
              src={product.image_src}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-200"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-600 text-[10px] font-mono">
              no img
            </div>
          )}
          {product.permalink && (
            <div className="absolute inset-0 bg-black/45 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </div>
          )}
        </a>
      </td>

      {/* ID (Read-only) */}
      <td className="py-2.5 px-3 font-mono text-xs text-slate-400 whitespace-nowrap">
        #{product.id}
      </td>

      {/* Inline Editable Name */}
      <td className="py-2.5 px-3">
        <input
          type="text"
          value={draft.name}
          onChange={(e) => onUpdateDraft(product.id, { name: e.target.value })}
          onBlur={() => onBlurSave?.(product.id)}
          className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-medium focus:outline-none"
        />
      </td>

      {/* Inline Editable Price */}
      <td className="py-2.5 px-3 whitespace-nowrap">
        <input
          type="number"
          step="0.01"
          value={draft.price}
          onChange={(e) => onUpdateDraft(product.id, { price: e.target.value })}
          onBlur={() => onBlurSave?.(product.id)}
          className={`w-24 border focus:border-indigo-500 rounded-lg px-2 py-1.5 text-xs font-mono text-slate-200 focus:outline-none text-right ${
            product.tax_class === 5
              ? "bg-emerald-950/60 border-emerald-800/80"
              : "bg-slate-950 border-slate-800"
          }`}
        />
      </td>

      {/* Inline Editable Cost */}
      <td className="py-2.5 px-3 whitespace-nowrap">
        <input
          type="number"
          step="0.01"
          placeholder="—"
          value={draft.prod_cost}
          onChange={(e) =>
            onUpdateDraft(product.id, { prod_cost: e.target.value })
          }
          onBlur={() => onBlurSave?.(product.id)}
          className="w-24 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-2 py-1.5 text-xs font-mono text-slate-200 focus:outline-none text-right"
        />
      </td>

      {/* Stock (Read-only, updated after fetch) */}
      <td className="py-2.5 px-3 whitespace-nowrap font-mono text-xs">
        {product.stock_quantity !== null ? (
          <span
            className={
              product.stock_quantity > 0
                ? "text-emerald-400 font-semibold"
                : "text-slate-500"
            }
          >
            {product.stock_quantity}
          </span>
        ) : (
          <span className="text-slate-600">—</span>
        )}
      </td>

      {/* Inline Editable Active Checkbox or Product Name */}
      <td className="py-2.5 px-3 whitespace-nowrap">
        {showProductNameInsteadOfActive ? (
          <span className="text-xs text-slate-300 font-medium truncate block max-w-[200px]" title={product.product_name || ""}>
            {product.product_name || "—"}
          </span>
        ) : (
          <input
            type="checkbox"
            checked={draft.active}
            onChange={(e) =>
              onUpdateDraft(product.id, { active: e.target.checked })
            }
            className="w-4 h-4 rounded text-indigo-600 bg-slate-950 border-slate-700 focus:ring-indigo-500 cursor-pointer"
          />
        )}
      </td>
    </tr>
  );
}
