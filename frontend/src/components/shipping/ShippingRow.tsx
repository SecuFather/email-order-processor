import { useEffect, useState, type KeyboardEvent } from "react";
import type { Shipping } from "../../types/shipping";
import type { LogEntry } from "../../types/log";
import { extractShippingFromText } from "../../api/shipping";

const TD_NIP = "py-2.5 px-3 w-48 min-w-[170px] whitespace-nowrap";
const TD_NAME = "py-2.5 px-3 min-w-[240px] w-full";
const TD_ADDRESS = "py-2.5 px-3 w-72 min-w-[220px]";
const TD_ZIP = "py-2.5 px-3 w-32 min-w-[110px] max-w-[130px]";
const TD_CITY = "py-2.5 px-3 w-48 min-w-[160px] max-w-[220px]";
const TD_PHONE = "py-2.5 px-3 w-60 min-w-[210px]";
const TD_EMAIL = "py-2.5 px-3 w-80 min-w-[300px]";
const TD_ACTIONS = "py-2.5 px-3 w-28 min-w-[100px] text-right whitespace-nowrap";

const ACTIONS_CONTAINER_CLASS = "flex items-center justify-end gap-1.5";
const SAVE_BUTTON_ACTIVE_CLASS = "p-1 rounded cursor-pointer transition-colors hover:bg-emerald-600/20 text-emerald-400";
const SAVE_BUTTON_DISABLED_CLASS = "p-1 rounded transition-colors text-slate-600 cursor-not-allowed";
const DISCARD_BUTTON_CLASS = "p-1 hover:bg-amber-600/20 text-amber-400 rounded cursor-pointer transition-colors";
const DELETE_BUTTON_CLASS = "p-1 hover:bg-red-600/20 text-slate-500 hover:text-red-400 rounded cursor-pointer transition-colors";

function getRowClassName(isNew: boolean, isModified: boolean, isUsed: boolean): string {
  if (isNew) {
    return "transition-colors border-b bg-slate-900/90 border-b-2 border-indigo-500/30";
  }
  if (isModified) {
    return "transition-colors border-b bg-amber-950/25 border-l-4 border-l-amber-500 hover:bg-amber-950/35 border-slate-800/60";
  }
  if (isUsed) {
    return "transition-colors border-b bg-indigo-950/20 hover:bg-indigo-950/30 border-slate-800/60";
  }
  return "transition-colors border-b hover:bg-slate-800/40 border-slate-800/60";
}

function getInputClassName(isModified: boolean, isFieldModified: boolean, isNew: boolean, isMono = false): string {
  const font = isMono ? "font-mono text-emerald-400 placeholder-slate-500" : "text-slate-100 placeholder-slate-500";
  const border =
    isModified && isFieldModified
      ? "border-amber-500 bg-amber-950/40"
      : isNew
      ? "border-slate-800 hover:border-slate-700 focus:border-indigo-500 bg-slate-950"
      : "border-transparent hover:border-slate-700 focus:border-indigo-500 bg-transparent";
  return `w-full border rounded px-2.5 py-1 text-sm focus:bg-slate-950 focus:outline-none transition-colors ${font} ${border}`;
}

function getUseButtonClassName(isUsed: boolean): string {
  return `px-2.5 py-0.5 rounded text-xs font-medium cursor-pointer transition-colors ${
    isUsed
      ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm ring-1 ring-indigo-400"
      : "bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
  }`;
}

type ShippingRowProps = {
  shipping: Shipping;
  globalNip?: string | null;
  isUsed: boolean;
  onToggleUse: (id: number) => void;
  onSave: (id: number, draft: Shipping) => Promise<void>;
  onDelete: (id: number, name: string) => Promise<void>;
  onAddLog?: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function ShippingRow({
  shipping,
  globalNip,
  isUsed,
  onToggleUse,
  onSave,
  onDelete,
  onAddLog,
}: ShippingRowProps) {
  const [draft, setDraft] = useState<Shipping>(shipping);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);

  useEffect(() => {
    setDraft(shipping);
  }, [shipping]);

  const isNew = !shipping.id;
  const isModified = isNew
    ? Boolean(
        draft.nip.trim() ||
        draft.name.trim() ||
        draft.address.trim() ||
        draft.zip_code.trim() ||
        draft.city.trim() ||
        draft.phone.trim() ||
        draft.email.trim()
      )
    : draft.nip !== shipping.nip ||
      draft.name !== shipping.name ||
      draft.address !== shipping.address ||
      draft.zip_code !== shipping.zip_code ||
      draft.city !== shipping.city ||
      draft.phone !== shipping.phone ||
      draft.email !== shipping.email;

  const canSave = Boolean(draft.name.trim()) && !isSaving;

  function handleDiscard() {
    setDraft(shipping);
  }

  async function handleSave() {
    if (!isModified || !canSave) return;
    const cleanNip = draft.nip.trim() || (isNew ? (globalNip ?? "") : "");

    setIsSaving(true);
    try {
      await onSave(shipping.id, {
        ...draft,
        nip: cleanNip,
        name: draft.name.trim(),
        address: draft.address.trim(),
        zip_code: draft.zip_code.trim(),
        city: draft.city.trim(),
        phone: draft.phone.trim(),
        email: draft.email.trim(),
      });
      if (isNew) {
        setDraft(shipping);
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (isDeleting || isNew) return;
    if (window.confirm(`Delete shipping address "${shipping.name}"?`)) {
      setIsDeleting(true);
      try {
        await onDelete(shipping.id, shipping.name);
      } finally {
        setIsDeleting(false);
      }
    }
  }

  async function handleGetFromClipboard() {
    if (isExtracting) return;
    try {
      const text = await navigator.clipboard.readText();
      if (!text || !text.trim()) {
        onAddLog?.({
          level: "error",
          title: "Clipboard Empty",
          message: "Clipboard contains no text to extract shipping information from.",
        });
        return;
      }

      setIsExtracting(true);
      const parsed = await extractShippingFromText(text);
      setDraft((prev) => ({
        ...prev,
        nip: parsed.nip || (globalNip ?? ""),
        name: parsed.name,
        address: parsed.address,
        zip_code: parsed.zip_code,
        city: parsed.city,
        phone: parsed.phone,
        email: parsed.email,
      }));

      onAddLog?.({
        level: "info",
        title: "Shipping Extracted",
        message: `Extracted shipping info for "${parsed.name || "Recipient"}" from clipboard. Review and click save.`,
        details: parsed,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to extract shipping from clipboard";
      onAddLog?.({
        level: "error",
        title: "Extraction Failed",
        message: msg,
      });
    } finally {
      setIsExtracting(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleDiscard();
    }
  }

  const nipPlaceholder = isNew
    ? globalNip || "NIP..."
    : globalNip || "NIP";

  return (
    <tr className={getRowClassName(isNew, isModified, isUsed)}>
      {/* NIP */}
      <td className={TD_NIP}>
        <input
          type="text"
          value={draft.nip}
          onChange={(e) => setDraft((prev) => ({ ...prev, nip: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder={nipPlaceholder}
          className={getInputClassName(isModified, draft.nip !== shipping.nip, isNew, true)}
        />
      </td>

      {/* Recipient / Name */}
      <td className={TD_NAME}>
        <input
          type="text"
          value={draft.name}
          onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder={isNew ? "Recipient / Facility Name" : "Name"}
          className={getInputClassName(isModified, draft.name !== shipping.name, isNew)}
        />
      </td>

      {/* Street Address */}
      <td className={TD_ADDRESS}>
        <input
          type="text"
          value={draft.address}
          onChange={(e) => setDraft((prev) => ({ ...prev, address: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder={isNew ? "Street Address" : "Address"}
          className={getInputClassName(isModified, draft.address !== shipping.address, isNew)}
        />
      </td>

      {/* Zip Code */}
      <td className={TD_ZIP}>
        <input
          type="text"
          value={draft.zip_code}
          onChange={(e) => setDraft((prev) => ({ ...prev, zip_code: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder="00-000"
          className={getInputClassName(isModified, draft.zip_code !== shipping.zip_code, isNew, true)}
        />
      </td>

      {/* City */}
      <td className={TD_CITY}>
        <input
          type="text"
          value={draft.city}
          onChange={(e) => setDraft((prev) => ({ ...prev, city: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder="City"
          className={getInputClassName(isModified, draft.city !== shipping.city, isNew)}
        />
      </td>

      {/* Phone */}
      <td className={TD_PHONE}>
        <input
          type="tel"
          value={draft.phone}
          onChange={(e) => setDraft((prev) => ({ ...prev, phone: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder="Phone (optional)"
          className={getInputClassName(isModified, draft.phone !== shipping.phone, isNew)}
        />
      </td>

      {/* Email */}
      <td className={TD_EMAIL}>
        <input
          type="email"
          value={draft.email}
          onChange={(e) => setDraft((prev) => ({ ...prev, email: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder="Email (optional)"
          className={getInputClassName(isModified, draft.email !== shipping.email, isNew)}
        />
      </td>

      {/* Actions */}
      <td className={TD_ACTIONS}>
        <div className={ACTIONS_CONTAINER_CLASS}>
          {isNew ? (
            <>
              {isModified && (
                <>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={!canSave}
                    className={canSave ? SAVE_BUTTON_ACTIVE_CLASS : SAVE_BUTTON_DISABLED_CLASS}
                    title="Save new shipping address"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </button>

                  <button
                    type="button"
                    onClick={handleDiscard}
                    className={DISCARD_BUTTON_CLASS}
                    title="Discard input"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={handleGetFromClipboard}
                disabled={isExtracting}
                className="p-1 rounded transition-colors text-indigo-400 hover:text-indigo-300 hover:bg-indigo-600/20 disabled:text-slate-600 disabled:cursor-not-allowed cursor-pointer"
                title="Get shipping from clipboard"
              >
                {isExtracting ? (
                  <svg className="w-4 h-4 animate-spin text-indigo-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                )}
              </button>
            </>
          ) : isModified ? (
            <>
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                className={canSave ? SAVE_BUTTON_ACTIVE_CLASS : SAVE_BUTTON_DISABLED_CLASS}
                title="Save changes"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>

              <button
                type="button"
                onClick={handleDiscard}
                className={DISCARD_BUTTON_CLASS}
                title="Discard changes"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => onToggleUse(shipping.id)}
                className={getUseButtonClassName(isUsed)}
                title="Use this shipping address"
              >
                Use
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className={DELETE_BUTTON_CLASS}
                title="Delete shipping address"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
