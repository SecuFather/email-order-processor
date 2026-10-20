import type { ProductActiveFilter } from "../../types/product";

type ProductToolbarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  activeFilter: ProductActiveFilter;
  onFilterChange: (filter: ProductActiveFilter) => void;
  syncMsg: string;
  isSavingAll: boolean;
  modifiedCount: number;
  onSaveAll: () => void;
  onDiscardAll: () => void;
  isSyncing: boolean;
  onSync: () => void;
  onResetSync: () => void;
  totalProductsCount: number;
  filteredCount: number;
  activeCount: number;
  onDeleteAll: () => void;
};

const FILTERS: ProductActiveFilter[] = ["all", "active", "inactive"];

export function ProductToolbar({
  search,
  onSearchChange,
  activeFilter,
  onFilterChange,
  syncMsg,
  isSavingAll,
  modifiedCount,
  onSaveAll,
  onDiscardAll,
  isSyncing,
  onSync,
  onResetSync,
  totalProductsCount,
  filteredCount,
  activeCount,
  onDeleteAll,
}: ProductToolbarProps) {
  return (
    <div className="sticky top-4 z-20 bg-slate-900/95 backdrop-blur-md border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Search products by name or ID..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:border-indigo-500"
          />
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
            {FILTERS.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => onFilterChange(filter)}
                className={`px-3 py-1 rounded-md font-medium capitalize cursor-pointer transition-colors ${
                  activeFilter === filter
                    ? "bg-indigo-600 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {syncMsg && (
            <span className="text-xs text-emerald-400 font-medium mr-1">
              {syncMsg}
            </span>
          )}

          {/* Confirm inline edits button on top */}
          <button
            type="button"
            onClick={onSaveAll}
            disabled={modifiedCount === 0 || isSavingAll}
            className={`px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer transition-colors flex items-center gap-1.5 ${
              modifiedCount > 0
                ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20"
                : "bg-slate-800 text-slate-500 cursor-not-allowed opacity-60"
            }`}
            title="Confirm and save all inline edits"
          >
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
                d="M5 13l4 4L19 7"
              />
            </svg>
            {isSavingAll
              ? "Saving..."
              : modifiedCount > 0
              ? `Save Changes (${modifiedCount})`
              : "Save Changes"}
          </button>

          {modifiedCount > 0 && (
            <button
              type="button"
              onClick={onDiscardAll}
              disabled={isSavingAll}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium cursor-pointer transition-colors"
              title="Discard unsaved inline edits"
            >
              Discard
            </button>
          )}

          <button
            type="button"
            onClick={onSync}
            disabled={isSyncing}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium cursor-pointer flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isSyncing ? "Syncing..." : "Sync WooCommerce"}
          </button>

          <button
            type="button"
            onClick={onResetSync}
            disabled={isSyncing}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium cursor-pointer transition-colors"
            title="Reset sync date so next sync checks all products from beginning"
          >
            Reset Sync
          </button>

          <button
            type="button"
            onClick={onDeleteAll}
            disabled={totalProductsCount === 0}
            className="px-3 py-2 bg-red-950/60 hover:bg-red-900/80 border border-red-800/80 text-red-300 hover:text-red-200 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium cursor-pointer transition-colors"
            title="Remove all products and reset sync date"
          >
            Remove All
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/60">
        <div>
          Showing {filteredCount} of {totalProductsCount} products
          {totalProductsCount > 0 && (
            <span className="ml-2 text-slate-500">
              ({activeCount} active, {totalProductsCount - activeCount} inactive)
            </span>
          )}
        </div>
        {modifiedCount > 0 && (
          <span className="text-amber-400 font-medium">
            ● {modifiedCount} unsaved change(s) — click "Save Changes" on top
          </span>
        )}
      </div>
    </div>
  );
}
