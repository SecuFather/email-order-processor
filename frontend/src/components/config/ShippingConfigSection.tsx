import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/log";
import type { ShippingConfigData } from "../../types/shippingConfig";
import { fetchShippingConfig, saveShippingConfig } from "../../api/shippingConfig";

type ShippingConfigSectionProps = {
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

const INITIAL_CONFIG: ShippingConfigData = {
  model: "",
  system_prompt: "",
};

export function ShippingConfigSection({ onAddLog }: ShippingConfigSectionProps) {
  const [config, setConfig] = useState<ShippingConfigData>(INITIAL_CONFIG);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    setIsLoading(true);
    try {
      const cfg = await fetchShippingConfig();
      setConfig(cfg);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load shipping configuration";
      onAddLog({
        level: "error",
        title: "Failed to load shipping configuration",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  function handleFieldChange(field: keyof ShippingConfigData, value: string) {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      await saveShippingConfig(config);
      setSaveSuccessMsg("Configuration saved!");
      setTimeout(() => setSaveSuccessMsg(""), 3000);
      onAddLog({
        level: "info",
        title: "Shipping configuration saved",
        message: "Shipping model and prompt settings updated successfully.",
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save shipping configuration";
      onAddLog({
        level: "error",
        title: "Failed to save shipping configuration",
        message,
      });
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full">
        Loading shipping configuration...
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            Shipping Configuration
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure the LLM model and system prompt instructions for extracting shipping addresses from clipboard text using structured output.
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
            placeholder="e.g. qwen2.5:14b (leave blank to use default order model)"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            If left blank, the model specified in Order configuration will be used.
          </span>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            System Prompt
          </label>
          <textarea
            rows={12}
            value={config.system_prompt}
            onChange={(e) => handleFieldChange("system_prompt", e.target.value)}
            placeholder="Enter instructions for extracting shipping details from unstructured text..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-y"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            Directs the assistant on parsing recipient name, street address, postal code, city, phone, email, and tax NIP.
          </span>
        </div>
      </div>
    </div>
  );
}
