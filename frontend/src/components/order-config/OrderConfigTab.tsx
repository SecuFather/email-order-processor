import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/log";
import type { OrderMakerConfigData } from "../../types/orderConfig";
import { fetchOrderConfig, saveOrderConfig } from "../../api/orderConfig";
import { ToolMappingsSection } from "./ToolMappingsSection";
import { TemplatesSection } from "./TemplatesSection";

type OrderConfigTabProps = {
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

const INITIAL_CONFIG: OrderMakerConfigData = {
  model: "",
  system_prompt: "",
  search_tool: "search_product",
  set_request_tool: "set_order_text",
  set_product_tool: "set_order_product",
  search_row_template: "{rank}. {name} (ID: {id})",
  search_empty_template: "No products found.",
  set_text_template: "Saved order text at {at}: {text}",
  set_product_template: "Set product at {at}: {name} (ID: {product_id}), amount: {amount}",
  set_product_not_found_template: "Product {product_id} not found.",
  set_product_no_text_template: "No order text at {at}. Set order text first.",
  resolve_ambiguity_tool: "resolve_ambiguity",
  resolve_ambiguity_template: "Resolved ambiguity: chosen product is {name} (ID: {id})",
  resolve_ambiguity_none_template: "No ambiguity rule found for IDs: {ids}.",
};

export function OrderConfigTab({ onAddLog }: OrderConfigTabProps) {
  const [config, setConfig] = useState<OrderMakerConfigData>(INITIAL_CONFIG);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    setIsLoading(true);
    try {
      const cfg = await fetchOrderConfig();
      setConfig(cfg);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load order configuration";
      onAddLog({
        level: "error",
        title: "Failed to load order configuration",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  function handleFieldChange(field: keyof OrderMakerConfigData, value: string) {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      await saveOrderConfig(config);
      setSaveSuccessMsg("Configuration saved!");
      setTimeout(() => setSaveSuccessMsg(""), 3000);
      onAddLog({
        level: "info",
        title: "Order configuration saved",
        message: "Order Maker settings and templates updated successfully.",
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save order configuration";
      onAddLog({
        level: "error",
        title: "Failed to save order configuration",
        message,
      });
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full">
        Loading order configuration...
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            Order Configuration
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure the LLM model, system prompt instructions, tool function mappings, and templates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {saveSuccessMsg && (
            <span className="text-xs text-emerald-400 font-medium">
              {saveSuccessMsg}
            </span>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold cursor-pointer transition-colors shadow-sm"
          >
            {isSaving ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>

      {/* Model & System Prompt */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Model
          </label>
          <input
            type="text"
            value={config.model}
            onChange={(e) => handleFieldChange("model", e.target.value)}
            placeholder="e.g. qwen2.5:14b"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            System Prompt
          </label>
          <textarea
            rows={14}
            value={config.system_prompt}
            onChange={(e) => handleFieldChange("system_prompt", e.target.value)}
            placeholder="Enter instructions and tool guidelines for the order processing model..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-y"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            The system prompt directs the assistant on parsing customer order documents and using catalog tools.
          </span>
        </div>
      </div>

      {/* Tool Mappings */}
      <ToolMappingsSection config={config} onChange={handleFieldChange} />

      {/* Output Formatting Templates */}
      <TemplatesSection config={config} onChange={handleFieldChange} />
    </div>
  );
}
