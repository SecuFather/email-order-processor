import type { OrderMakerConfigData } from "../../types/orderConfig";

type ToolMappingsSectionProps = {
  config: OrderMakerConfigData;
  onChange: (field: keyof OrderMakerConfigData, value: string) => void;
};

const TOOLS = [
  {
    field: "search_tool" as const,
    label: "Search Tool Name",
    placeholder: "search_product",
    desc: "maps search_product(phrase, limit, page)",
  },
  {
    field: "set_request_tool" as const,
    label: "Set Order Text Tool Name",
    placeholder: "set_order_text",
    desc: "maps set_order_text(at, text)",
  },
  {
    field: "set_product_tool" as const,
    label: "Set Order Product Tool Name",
    placeholder: "set_order_product",
    desc: "maps set_order_product(at, product_id, amount)",
  },
  {
    field: "resolve_ambiguity_tool" as const,
    label: "Resolve Ambiguity Tool Name",
    placeholder: "resolve_ambiguity",
    desc: "maps resolve_ambiguity(ids)",
  },
];

export function ToolMappingsSection({ config, onChange }: ToolMappingsSectionProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Tool Function Names
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Tool function names exposed to the model for order parsing and store catalog matching.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {TOOLS.map((t) => (
          <div key={t.field}>
            <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
              {t.label}
            </label>
            <input
              type="text"
              value={config[t.field]}
              onChange={(e) => onChange(t.field, e.target.value)}
              placeholder={t.placeholder}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-[10px] text-slate-500 block mt-1">
              {t.desc}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
