import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { EmailAttachment, EmailDetail, ToolCall } from "../../types/email";

type ViewerTab = "body" | "attachment" | "notes" | "order" | "chat";

type EmlViewerProps = {
  email: EmailDetail | null;
  isLoading: boolean;
  isGeneratingOrder: boolean;
  isSubmittingOrder: boolean;
  activeAttachment: EmailAttachment | null;
  globalNip: string | null;
  globalShippingId: number | null;
  onSelectAttachment: (att: EmailAttachment | null) => void;
  onClickNip: (id: number) => void;
  onClickShipping: (id: number) => void;
  onSaveNotes: (id: number, notes: string) => Promise<void>;
  onRunOrder: (id: number) => Promise<void>;
  onAcceptOrder: (id: number) => Promise<void>;
};

function formatToolCall(tc: ToolCall): string {
  const args = Object.entries(tc.function.arguments || {})
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
  return `${tc.function.name}(${args})`;
}

export function EmlViewer({
  email,
  isLoading,
  isGeneratingOrder,
  isSubmittingOrder,
  activeAttachment,
  globalNip,
  globalShippingId,
  onSelectAttachment,
  onClickNip,
  onClickShipping,
  onSaveNotes,
  onRunOrder,
  onAcceptOrder,
}: EmlViewerProps) {
  const [activeTab, setActiveTab] = useState<ViewerTab>("body");
  const [notes, setNotes] = useState("");
  const [isSavingNotes, setIsSavingNotes] = useState(false);

  useEffect(() => {
    setActiveTab("body");
  }, [email?.id]);

  useEffect(() => {
    setNotes(email?.notes ?? "");
  }, [email?.id, email?.notes]);

  useEffect(() => {
    if (
      email &&
      activeTab === "order" &&
      !isGeneratingOrder &&
      Object.keys(email.cart).length === 0 &&
      email.messages.length === 0
    ) {
      onRunOrder(email.id);
    }
  }, [email?.id, activeTab]);

  if (isLoading) {
    return (
      <div className="py-28 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-sm">
        Loading email...
      </div>
    );
  }

  if (!email) {
    return (
      <div className="py-28 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
        Select an email from the list on the right or upload a new .eml file.
      </div>
    );
  }

  async function handleSave() {
    setIsSavingNotes(true);
    try {
      await onSaveNotes(email!.id, notes);
    } finally {
      setIsSavingNotes(false);
    }
  }

  const nipTitle =
    globalNip && email.nip !== globalNip
      ? `Click to set NIP to ${globalNip}`
      : "Click to clear NIP";

  const shippingTitle =
    globalShippingId && email.shipping_id !== globalShippingId
      ? `Click to set Shipping ID to #${globalShippingId}`
      : "Click to clear Shipping ID";

  const segments = Object.values(email.cart).sort((a, b) => a.at - b.at);
  const discount = email.company_discount ?? 0;
  const discountFactor = 1 - discount / 100;

  const totalGross = segments.reduce(
    (sum, seg) =>
      sum +
      Object.values(seg.products ?? {}).reduce(
        (pSum, p) =>
          pSum + ((p.product?.price_cents ?? 0) * (p.amount ?? 0)) / 100,
        0
      ),
    0
  );
  const totalNet = segments.reduce(
    (sum, seg) =>
      sum +
      Object.values(seg.products ?? {}).reduce((pSum, p) => {
        const gross = ((p.product?.price_cents ?? 0) * (p.amount ?? 0)) / 100;
        const taxClass = p.product?.tax_class ?? 23;
        return pSum + (gross * 100) / (100 + taxClass);
      }, 0),
    0
  );
  const totalGrossDiscounted = totalGross * discountFactor;
  const totalNetDiscounted = totalNet * discountFactor;

  const totalCartQuantity = segments.reduce(
    (sum, seg) =>
      sum +
      Object.values(seg.products ?? {}).reduce(
        (qSum, p) => qSum + (p.amount ?? 0),
        0
      ),
    0
  );
  const totalProductsCount = segments.reduce(
    (sum, seg) => sum + Object.keys(seg.products ?? {}).length,
    0
  );
  const promptTokens = email.messages.reduce(
    (sum, m) => sum + (m.stats?.prompt_tokens ?? 0),
    0
  );
  const evalTokens = email.messages.reduce(
    (sum, m) => sum + (m.stats?.eval_tokens ?? 0),
    0
  );

  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2.5 text-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="text-base font-semibold text-white">
            {email.title || email.subject || "(No subject)"}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {email.fakturownia_url && (
              <a
                href={email.fakturownia_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-2.5 py-1 rounded text-xs font-mono font-medium bg-amber-950/60 text-amber-400 border border-amber-700/50 hover:bg-amber-900/60 transition-colors"
                title="Open invoice in Fakturownia"
              >
                FV #{email.fakturownia_number || email.fakturownia_id} ↗
              </a>
            )}
            {email.woocommerce_id ? (
              email.woocommerce_url ? (
                <a
                  href={email.woocommerce_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 rounded text-xs font-mono font-medium bg-purple-950/60 text-purple-400 border border-purple-700/50 hover:bg-purple-900/60 transition-colors"
                  title="Open order in WooCommerce"
                >
                  WC #{email.woocommerce_id} ↗
                </a>
              ) : (
                <span className="px-2.5 py-1 rounded text-xs font-mono font-medium bg-purple-950/60 text-purple-400 border border-purple-700/50">
                  WC #{email.woocommerce_id}
                </span>
              )
            ) : (
              <button
                type="button"
                onClick={() => onAcceptOrder(email.id)}
                disabled={isSubmittingOrder || totalProductsCount === 0 || !email.nip}
                title={
                  !email.nip
                    ? "NIP is required to accept order"
                    : totalProductsCount === 0
                    ? "Cart is empty"
                    : "Create invoice and submit order"
                }
                className="px-2.5 py-1 rounded text-xs font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white cursor-pointer transition-colors"
              >
                {isSubmittingOrder ? "Accepting..." : "Accept order"}
              </button>
            )}

            <button
              type="button"
              onClick={() => onClickNip(email.id)}
              title={nipTitle}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium cursor-pointer transition-colors ${
                email.nip
                  ? "bg-emerald-950/60 text-emerald-400 border border-emerald-700/50 hover:bg-emerald-900/60"
                  : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-slate-200"
              }`}
            >
              {email.nip
                ? email.company_name
                  ? `${email.nip} (${email.company_name})`
                  : email.nip
                : "No NIP"}
            </button>

            <button
              type="button"
              onClick={() => onClickShipping(email.id)}
              title={shippingTitle}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium cursor-pointer transition-colors ${
                email.shipping_id
                  ? "bg-sky-950/60 text-sky-400 border border-sky-700/50 hover:bg-sky-900/60"
                  : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-slate-200"
              }`}
            >
              {email.shipping_id
                ? email.shipping_name
                  ? `Ship #${email.shipping_id} (${email.shipping_name})`
                  : `Ship #${email.shipping_id}`
                : "No Shipping"}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-400">
          <div>
            <span className="font-semibold text-slate-300">From:</span>{" "}
            {email.sender || email.from}
          </div>
          <div>
            <span className="font-semibold text-slate-300">Date:</span>{" "}
            {email.date}
          </div>
          {(email.recipient || email.to) && (
            <div className="sm:col-span-2">
              <span className="font-semibold text-slate-300">To:</span>{" "}
              {email.recipient || email.to}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            setActiveTab("body");
            onSelectAttachment(null);
          }}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer ${
            activeTab === "body"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          Email Body
        </button>
        {email.attachments.map((att, i) => (
          <button
            key={i}
            type="button"
            onClick={() => {
              setActiveTab("attachment");
              onSelectAttachment(att);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer ${
              activeTab === "attachment" && activeAttachment === att
                ? "bg-indigo-600 text-white"
                : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
            }`}
          >
            {att.filename}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setActiveTab("notes")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer ${
            activeTab === "notes"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          Notes
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("order")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer ${
            activeTab === "order"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          Order
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer ${
            activeTab === "chat"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          Chat
        </button>
      </div>

      {/* Keep Email Body and Attachments mounted so PDF/iframe scroll position is preserved across tab switches */}
      <iframe
        srcDoc={email.html}
        title="Email Body"
        sandbox="allow-same-origin allow-popups"
        className={`w-full h-[650px] bg-white rounded-xl border border-slate-800 ${
          activeTab === "body"
            ? "block"
            : "fixed -left-[9999px] top-0 invisible pointer-events-none"
        }`}
      />

      {email.attachments.map((att, i) => {
        const isCurrentAtt =
          activeTab === "attachment" && activeAttachment === att;
        return att.url ? (
          <iframe
            key={i}
            src={att.url}
            title={att.filename}
            className={`w-full h-[650px] bg-white rounded-xl border border-slate-800 ${
              isCurrentAtt
                ? "block"
                : "fixed -left-[9999px] top-0 invisible pointer-events-none"
            }`}
          />
        ) : (
          <div
            key={i}
            className={`bg-slate-900 border border-slate-800 rounded-xl p-5 prose prose-invert max-w-none overflow-auto h-[650px] ${
              isCurrentAtt ? "block" : "hidden"
            }`}
          >
            <Markdown remarkPlugins={[remarkGfm]}>{att.markdown}</Markdown>
          </div>
        );
      })}

      {activeTab === "notes" && (
        <div className="space-y-3">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes..."
            className="w-full h-[600px] bg-slate-900 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 resize-y"
          />
          <div>
            <button
              type="button"
              disabled={isSavingNotes}
              onClick={handleSave}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white cursor-pointer transition-colors"
            >
              {isSavingNotes ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}

      {activeTab === "order" && (
        <div className="space-y-3">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="text-slate-400 font-semibold uppercase tracking-wider">
                Cart ({segments.length}{" "}
                {segments.length === 1 ? "segment" : "segments"},{" "}
                {totalProductsCount}{" "}
                {totalProductsCount === 1 ? "product" : "products"},{" "}
                {totalCartQuantity} units
                {discount > 0 ? `, discount ${discount}%` : ""})
              </div>
              <div className="flex items-center gap-2">
                {email.fakturownia_url && (
                  <a
                    href={email.fakturownia_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-amber-950/80 text-amber-300 border border-amber-800/60 hover:bg-amber-900 transition-colors"
                    title="Open invoice in Fakturownia"
                  >
                    FV #{email.fakturownia_number || email.fakturownia_id} ↗
                  </a>
                )}
                {email.woocommerce_id ? (
                  email.woocommerce_url ? (
                    <a
                      href={email.woocommerce_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60 hover:bg-purple-900 transition-colors"
                      title="Open order in WooCommerce"
                    >
                      WC #{email.woocommerce_id} ↗
                    </a>
                  ) : (
                    <span className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60">
                      WC #{email.woocommerce_id}
                    </span>
                  )
                ) : (
                  <button
                    type="button"
                    disabled={isSubmittingOrder || totalProductsCount === 0 || !email.nip}
                    onClick={() => onAcceptOrder(email.id)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white cursor-pointer transition-colors"
                    title={
                      !email.nip
                        ? "NIP is required to accept order"
                        : totalProductsCount === 0
                        ? "Cart is empty"
                        : "Create invoice and submit order"
                    }
                  >
                    {isSubmittingOrder ? "Accepting..." : "Accept order"}
                  </button>
                )}
                <button
                  type="button"
                  disabled={isGeneratingOrder}
                  onClick={() => onRunOrder(email.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white cursor-pointer transition-colors"
                >
                  {isGeneratingOrder ? "Generating..." : "Re-run"}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-slate-800/80 font-mono">
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg px-3 py-2">
                <div className="text-[10px] font-sans uppercase text-slate-500">
                  Net (no discount)
                </div>
                <div className="text-slate-200 font-semibold mt-0.5">
                  {totalNet.toFixed(2)} zł
                </div>
              </div>
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg px-3 py-2">
                <div className="text-[10px] font-sans uppercase text-slate-500">
                  Gross (no discount)
                </div>
                <div className="text-slate-200 font-semibold mt-0.5">
                  {totalGross.toFixed(2)} zł
                </div>
              </div>
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg px-3 py-2">
                <div className="text-[10px] font-sans uppercase text-slate-500">
                  Net (with {discount}% disc.)
                </div>
                <div className="text-emerald-400 font-semibold mt-0.5">
                  {totalNetDiscounted.toFixed(2)} zł
                </div>
              </div>
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg px-3 py-2">
                <div className="text-[10px] font-sans uppercase text-slate-500">
                  Gross (with {discount}% disc.)
                </div>
                <div className="text-emerald-400 font-semibold mt-0.5">
                  {totalGrossDiscounted.toFixed(2)} zł
                </div>
              </div>
            </div>
          </div>

          {segments.length === 0 ? (
            <div className="py-28 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
              {isGeneratingOrder
                ? "Generating order with AI..."
                : "Cart is empty."}
            </div>
          ) : (
            <div className="space-y-3">
              {segments.map((seg) => {
                const prods = Object.values(seg.products ?? {});
                return (
                  <div
                    key={seg.at}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3"
                  >
                    <div className="flex items-center gap-2.5 border-b border-slate-800/80 pb-2.5">
                      <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800/60 text-[11px] font-mono text-indigo-300 font-semibold shrink-0">
                        #{seg.at}
                      </span>
                      {seg.text && (
                        <span
                          className="text-xs text-indigo-200 font-medium italic truncate"
                          title={seg.text}
                        >
                          "{seg.text}"
                        </span>
                      )}
                      <span className="text-[11px] text-slate-500 font-mono">
                        ({prods.length})
                      </span>
                    </div>

                    {prods.length === 0 ? (
                      <div className="py-3 text-center bg-slate-950/40 border border-dashed border-slate-800/80 rounded-lg text-slate-500 text-xs italic">
                        No products added to this segment yet.
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        {prods.map((p) => {
                          const taxClass = p.product?.tax_class ?? 23;
                          const unitGross = (p.product?.price_cents ?? 0) / 100;
                          const unitNet = (unitGross * 100) / (100 + taxClass);
                          const lineGross = unitGross * p.amount;
                          const lineNet = unitNet * p.amount;
                          const lineGrossDisc = lineGross * discountFactor;
                          const lineNetDisc = lineNet * discountFactor;

                          return (
                            <div
                              key={p.product_id}
                              className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 flex gap-3.5 items-center"
                            >
                              {p.product?.image_src ? (
                                <a
                                  href={p.product.permalink || undefined}
                                  target={
                                    p.product.permalink ? "_blank" : undefined
                                  }
                                  rel="noopener noreferrer"
                                  className="w-16 h-16 rounded-md bg-slate-900 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center hover:opacity-90 transition-opacity"
                                >
                                  <img
                                    src={p.product.image_src}
                                    alt={p.product.name}
                                    className="w-full h-full object-cover"
                                  />
                                </a>
                              ) : (
                                <div className="w-16 h-16 rounded-md bg-slate-900 border border-slate-800 shrink-0 flex items-center justify-center text-[10px] text-slate-600 font-mono">
                                  no image
                                </div>
                              )}

                              <div className="flex-1 min-w-0 space-y-1.5">
                                <div className="flex items-baseline justify-between gap-2">
                                  <a
                                    href={p.product?.permalink || undefined}
                                    target={
                                      p.product?.permalink ? "_blank" : undefined
                                    }
                                    rel="noopener noreferrer"
                                    className="text-sm font-semibold text-white hover:text-indigo-300 transition-colors line-clamp-1"
                                    title={
                                      p.product?.name ??
                                      `Product #${p.product_id}`
                                    }
                                  >
                                    {p.product?.name ??
                                      `Product #${p.product_id}`}
                                  </a>
                                  <span className="text-slate-300 text-xs font-mono shrink-0">
                                    Qty: {p.amount}
                                  </span>
                                </div>

                                <div className="flex items-center justify-between gap-3 text-[11px] pt-1 border-t border-slate-800/60 flex-wrap font-mono text-slate-400">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span>ID: #{p.product_id}</span>
                                    <span>•</span>
                                    <span>VAT {taxClass}%</span>
                                    <span>•</span>
                                    <span>
                                      Unit: {unitNet.toFixed(2)} net /{" "}
                                      {unitGross.toFixed(2)} gross
                                    </span>
                                    {p.product?.stock_quantity != null && (
                                      <>
                                        <span>•</span>
                                        <span
                                          className={
                                            p.amount > p.product.stock_quantity
                                              ? "text-amber-400 font-bold"
                                              : "text-slate-400"
                                          }
                                        >
                                          Stock: {p.product.stock_quantity}
                                        </span>
                                      </>
                                    )}
                                  </div>

                                  <div className="flex items-center gap-3 flex-wrap">
                                    <span>
                                      No disc: {lineNet.toFixed(2)} net /{" "}
                                      {lineGross.toFixed(2)} gross
                                    </span>
                                    <span className="text-emerald-400 font-semibold">
                                      Disc: {lineNetDisc.toFixed(2)} net /{" "}
                                      {lineGrossDisc.toFixed(2)} gross
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === "chat" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2.5">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Conversation ({email.messages.filter((m) => m.role !== "tool").length} turns)
              </h2>
              {isGeneratingOrder && (
                <span className="text-[11px] font-mono text-indigo-400 animate-pulse">
                  ● Streaming
                </span>
              )}
            </div>
            <span className="text-xs font-mono text-slate-500">
              Prompt: {promptTokens} tok | Eval: {evalTokens} tok
            </span>
          </div>

          {email.messages.length === 0 ? (
            <div className="py-20 text-center text-slate-500 text-sm">
              No conversation yet. Open the Order tab to generate an order.
            </div>
          ) : (
            <div className="space-y-3">
              {email.messages.map((m, i) => {
                if (m.role === "tool") return null;
                const isActiveTurn =
                  isGeneratingOrder &&
                  m.role === "assistant" &&
                  i === email.messages.length - 1;
                return (
                  <div
                    key={i}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2.5 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-bold uppercase ${
                          m.role === "assistant"
                            ? "text-emerald-400"
                            : "text-indigo-400"
                        }`}
                      >
                        {m.role}
                      </span>
                      {m.stats && (
                        <span className="text-[11px] font-mono text-slate-500">
                          (in: {m.stats.prompt_tokens}, out: {m.stats.eval_tokens})
                        </span>
                      )}
                    </div>

                    {m.role === "assistant" && (m.thinking || isActiveTurn) && (
                      <div className="bg-slate-900/70 border border-slate-800 rounded p-2.5 text-xs font-mono text-slate-400 whitespace-pre-wrap">
                        <span className="text-[10px] uppercase font-semibold text-slate-500 block mb-1">
                          Thinking
                        </span>
                        {m.thinking || "Thinking..."}
                      </div>
                    )}

                    {m.content && (
                      <div
                        className={`text-xs font-mono text-slate-200 whitespace-pre-wrap ${
                          m.role === "user" ? "max-h-36 overflow-y-auto" : ""
                        }`}
                      >
                        {m.content}
                      </div>
                    )}

                    {m.tool_calls &&
                      m.tool_calls.map((tc, tcIdx) => {
                        const toolMsg = email.messages[i + 1 + tcIdx];
                        return (
                          <div
                            key={tcIdx}
                            className="bg-amber-950/30 border border-amber-800/50 rounded p-3 space-y-1.5 text-xs font-mono"
                          >
                            <div className="font-semibold text-amber-300">
                              🔧 {formatToolCall(tc)}
                            </div>
                            {toolMsg?.role === "tool" && toolMsg.content && (
                              <div className="text-slate-300 bg-slate-900 border border-amber-700/40 rounded p-2 text-xs whitespace-pre-wrap">
                                {toolMsg.content}
                              </div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
