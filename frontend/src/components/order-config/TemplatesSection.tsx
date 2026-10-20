import type { OrderMakerConfigData } from "../../types/orderConfig";

type TemplatesSectionProps = {
  config: OrderMakerConfigData;
  onChange: (field: keyof OrderMakerConfigData, value: string) => void;
};

const TEMPLATES = [
  {
    field: "search_row_template" as const,
    label: "Search Row Format",
    vars: "vars: {rank}, {name}, {id}, {price}, {stock}",
    colSpan: "col-span-1",
  },
  {
    field: "search_empty_template" as const,
    label: "Search Empty Format",
    vars: "",
    colSpan: "col-span-1",
  },
  {
    field: "set_text_template" as const,
    label: "Set Order Text Format",
    vars: "vars: {at}, {text}",
    colSpan: "col-span-1",
  },
  {
    field: "set_product_template" as const,
    label: "Set Order Product Format",
    vars: "vars: {at}, {name}, {product_id}, {amount}, {price}, {stock}",
    colSpan: "col-span-1",
  },
  {
    field: "set_product_not_found_template" as const,
    label: "Set Product Not Found Format",
    vars: "vars: {product_id}, {at}",
    colSpan: "col-span-1",
  },
  {
    field: "set_product_no_text_template" as const,
    label: "Set Product Without Text Format",
    vars: "vars: {at}, {product_id}, {set_request_tool}",
    colSpan: "col-span-1",
  },
  {
    field: "resolve_ambiguity_template" as const,
    label: "Resolve Ambiguity Match Format",
    vars: "vars: {ids}, {id}, {name}",
    colSpan: "col-span-1",
  },
  {
    field: "resolve_ambiguity_none_template" as const,
    label: "Resolve Ambiguity None Found Format",
    vars: "vars: {ids}",
    colSpan: "col-span-1",
  },
];

export function TemplatesSection({ config, onChange }: TemplatesSectionProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Tool Output Formatting Templates
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Templates applied when serializing tool outputs into the model message context.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TEMPLATES.map((tmpl) => (
          <div key={tmpl.field} className={tmpl.colSpan}>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              {tmpl.label} {tmpl.vars && <span className="text-slate-500 font-mono">({tmpl.vars})</span>}
            </label>
            <input
              type="text"
              value={config[tmpl.field]}
              onChange={(e) => onChange(tmpl.field, e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
