import { useEffect, useState, type KeyboardEvent } from "react";
import type { Client } from "../../types/client";

const TD_EMAIL = "py-2.5 px-3 min-w-[260px] w-1/3";
const TD_NIP = "py-2.5 px-3 w-48 min-w-[180px] whitespace-nowrap";
const TD_COMPANY = "py-2.5 px-3 min-w-[220px] w-1/2";
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

type ClientRowProps = {
  client: Client;
  globalNip?: string | null;
  isUsed: boolean;
  onToggleUse: (nip: string) => void;
  onSave: (originalEmail: string, draft: Client) => Promise<void>;
  onDelete: (email: string) => Promise<void>;
};

export function ClientRow({
  client,
  globalNip,
  isUsed,
  onToggleUse,
  onSave,
  onDelete,
}: ClientRowProps) {
  const [draft, setDraft] = useState<Client>(client);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    setDraft(client);
  }, [client]);

  const isNew = !client.email;
  const isModified = isNew
    ? Boolean(draft.email.trim() || draft.nip.trim())
    : draft.email !== client.email || draft.nip !== client.nip;

  const effectiveNip = draft.nip.trim() || (globalNip ?? "");
  const canSave = Boolean(draft.email.trim() && effectiveNip) && !isSaving;

  function handleDiscard() {
    setDraft(client);
  }

  async function handleSave() {
    if (!isModified || isSaving) return;
    const cleanEmail = draft.email.trim();
    const cleanNip = draft.nip.trim() || (globalNip ?? "");
    if (!cleanEmail || !cleanNip) return;

    setIsSaving(true);
    try {
      await onSave(client.email, { ...draft, email: cleanEmail, nip: cleanNip });
      if (isNew) {
        setDraft(client);
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (isDeleting || isNew) return;
    if (window.confirm(`Delete client mapping for "${client.email}"?`)) {
      setIsDeleting(true);
      try {
        await onDelete(client.email);
      } finally {
        setIsDeleting(false);
      }
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
    ? globalNip || "NIP (10 digits)..."
    : globalNip || "NIP";

  return (
    <tr className={getRowClassName(isNew, isModified, isUsed)}>
      {/* Email */}
      <td className={TD_EMAIL}>
        <input
          type="email"
          value={draft.email}
          onChange={(e) => setDraft((prev) => ({ ...prev, email: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder={isNew ? "New client email..." : "Email address"}
          className={getInputClassName(isModified, draft.email !== client.email, isNew)}
        />
      </td>

      {/* NIP */}
      <td className={TD_NIP}>
        <input
          type="text"
          value={draft.nip}
          onChange={(e) => setDraft((prev) => ({ ...prev, nip: e.target.value }))}
          onKeyDown={handleKeyDown}
          placeholder={nipPlaceholder}
          className={getInputClassName(isModified, draft.nip !== client.nip, isNew, true)}
        />
      </td>

      {/* Company Name */}
      <td className={TD_COMPANY}>
        {isNew ? (
          <span className="text-xs text-slate-500 italic">
            Auto-resolved from NIP
          </span>
        ) : client.company_name ? (
          <span className="text-sm text-slate-200 font-medium">{client.company_name}</span>
        ) : (
          <span className="text-xs text-slate-500 italic">No company linked</span>
        )}
      </td>

      {/* Actions */}
      <td className={TD_ACTIONS}>
        <div className={ACTIONS_CONTAINER_CLASS}>
          {isNew ? (
            isModified && (
              <>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!canSave}
                  className={canSave ? SAVE_BUTTON_ACTIVE_CLASS : SAVE_BUTTON_DISABLED_CLASS}
                  title="Save new client mapping"
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
            )
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
                onClick={() => onToggleUse(client.nip)}
                className={getUseButtonClassName(isUsed)}
                title="Use this company NIP"
              >
                Use
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className={DELETE_BUTTON_CLASS}
                title="Delete client mapping"
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
