import { useState } from "react";
import type { LogEntry } from "../../types/log";
import { OrderConfigTab } from "../order-config/OrderConfigTab";
import { ShippingConfigSection } from "./ShippingConfigSection";

type ConfigTabProps = {
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

type ConfigSubTab = "order" | "shipping";

export function ConfigTab({ onAddLog }: ConfigTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<ConfigSubTab>("order");

  return (
    <div className="w-full space-y-6">
      {/* Sub-tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setActiveSubTab("order")}
          className={`px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors cursor-pointer ${
            activeSubTab === "order"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
          }`}
        >
          Order
        </button>
        <button
          type="button"
          onClick={() => setActiveSubTab("shipping")}
          className={`px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors cursor-pointer ${
            activeSubTab === "shipping"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
          }`}
        >
          Shipping
        </button>
      </div>

      {activeSubTab === "order" && <OrderConfigTab onAddLog={onAddLog} />}
      {activeSubTab === "shipping" && <ShippingConfigSection onAddLog={onAddLog} />}
    </div>
  );
}
