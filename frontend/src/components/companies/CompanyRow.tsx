import { useEffect, useState, type KeyboardEvent } from "react";
import type { Company } from "../../types/company";
import type { LogEntry } from "../../types/log";
import { fetchCompanyFromGus } from "../../api/companies";

const TD_NIP = "py-2.5 px-3 w-52 min-w-[200px] whitespace-nowrap";
const TD_NAME = "py-2.5 px-3 min-w-[320px] w-full";
const TD_ADDRESS = "py-2.5 px-3 w-80 min-w-[280px]";
const TD_ZIP = "py-2.5 px-3 w-32 min-w-[110px] max-w-[130px]";
const TD_CITY = "py-2.5 px-3 w-52 min-w-[180px] max-w-[240px]";
const TD_DISCOUNT = "py-2.5 px-3 w-36 min-w-[130px] max-w-[160px]";
const TD_DEADLINE = "py-2.5 px-3 w-28 min-w-[95px] max-w-[115px]";
const TD_ACTIONS = "py-2.5 px-3 w-28 min-w-[100px] text-right whitespace-nowrap";

const DISCOUNT_CONTAINER_CLASS = "relative flex items-center";
const DISCOUNT_SUFFIX_CLASS = "text-xs text-slate-500 ml-1 select-none";
const DEADLINE_CONTAINER_CLASS = "relative flex items-center";
const DEADLINE_SUFFIX_CLASS = "text-xs text-slate-500 ml-1 select-none";
const ACTIONS_CONTAINER_CLASS = "flex items-center justify-end gap-1.5";

const NIP_INPUT_CLASS = "w-full bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded px-2.5 py-1 text-sm font-mono text-emerald-400 placeholder-slate-500 focus:outline-none";
const SAVE_BUTTON_ACTIVE_CLASS = "p-1 rounded cursor-pointer transition-colors hover:bg-emerald-600/20 text-emerald-400";
const SAVE_BUTTON_DISABLED_CLASS = "p-1 rounded transition-colors text-slate-600 cursor-not-allowed";
const DISCARD_BUTTON_CLASS = "p-1 hover:bg-amber-600/20 text-amber-400 rounded cursor-pointer transition-colors";
const DELETE_BUTTON_CLASS = "p-1 hover:bg-red-600/20 text-slate-500 hover:text-red-400 rounded cursor-pointer transition-colors";

function getRowClassName(isNew: boolean, isModified: boolean): string {
  if (isNew) {
    return "transition-colors border-b bg-slate-900/90 border-b-2 border-indigo-500/30";
  }
  if (isModified) {
    return "transition-colors border-b bg-amber-950/25 border-l-4 border-l-amber-500 hover:bg-amber-950/35 border-slate-800/60";
  }
  return "transition-colors border-b hover:bg-slate-800/40 border-slate-800/60";
}

function getNipTextClassName(isMyCompany: boolean): string {
  return isMyCompany
    ? "font-mono font-medium text-emerald-400 text-xs underline underline-offset-4 decoration-2"
    : "font-mono font-medium text-emerald-400 text-xs";
}

function getInputClassName(isModified: boolean, isFieldModified: boolean, isNew: boolean, isMono = false): string {
  const font = isMono ? "font-mono" : "";
  const border =
    isModified && isFieldModified
      ? "border-amber-500 bg-amber-950/40"
      : isNew
      ? "border-slate-800 hover:border-slate-700 focus:border-indigo-500"
      : "border-transparent hover:border-slate-700 focus:border-indigo-500";
  return `w-full bg-transparent border rounded px-2.5 py-1 text-sm text-slate-100 focus:bg-slate-950 focus:outline-none transition-colors ${font} ${border}`;
}

function getUseButtonClassName(isUsed: boolean): string {
  return `px-2.5 py-0.5 rounded text-xs font-medium cursor-pointer transition-colors ${
    isUsed
      ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm ring-1 ring-indigo-400"
      : "bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
  }`;
}

type CompanyRowProps = {
  company: Company;
  myNip?: string | null;
  isUsed: boolean;
  onToggleUse: (nip: string) => void;
  onSave: (nip: string, draft: Company) => Promise<void>;
  onDelete: (nip: string, name: string) => Promise<void>;
  onAddLog?: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function CompanyRow({
  company,
  myNip,
  isUsed,
  onToggleUse,
  onSave,
  onDelete,
  onAddLog,
}: CompanyRowProps) {
  const [draft, setDraft] = useState<Company>(company);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isFetchingGus, setIsFetchingGus] = useState(false);

  useEffect(() => {
    setDraft(company);
  }, [company]);

  const isNew = !company.nip;
  const isMyCompany = Boolean(!isNew && myNip && company.nip === myNip);
  const isModified = isNew
    ? Boolean(
        draft.nip.trim() ||
        draft.name.trim() ||
        draft.address.trim() ||
        draft.zip_code.trim() ||
        draft.city.trim() ||
        Number(draft.discount) > 0 ||
        Number(draft.deadline) > 0
      )
    : draft.name !== company.name ||
      draft.address !== company.address ||
      draft.zip_code !== company.zip_code ||
      draft.city !== company.city ||
      Number(draft.discount) !== Number(company.discount) ||
      Number(draft.deadline) !== Number(company.deadline);

  function handleDiscard() {
    setDraft(company);
  }

  async function handleSave() {
    if (!isModified || isSaving) return;
    const cleanNip = (isNew ? draft.nip : company.nip).trim();
    if (!cleanNip) return;

    setIsSaving(true);
    try {
      await onSave(cleanNip, { ...draft, nip: cleanNip });
      if (isNew) {
        setDraft(company);
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (isDeleting || isNew) return;
    if (window.confirm(`Delete company "${company.name || company.nip}"?`)) {
      setIsDeleting(true);
      try {
        await onDelete(company.nip, company.name);
      } finally {
        setIsDeleting(false);
      }
    }
  }

  async function handleFetchGus() {
    const rawNip = isNew ? draft.nip : company.nip;
    const cleanNip = rawNip.replace(/\D/g, "");
    if (!cleanNip || isFetchingGus) return;

    setIsFetchingGus(true);
    try {
      const info = await fetchCompanyFromGus(cleanNip);
      setDraft((prev) => ({
        ...prev,
        nip: cleanNip,
        name: info.name || prev.name,
        address: info.address || prev.address,
        zip_code: info.zip_code || prev.zip_code,
        city: info.city || prev.city,
      }));
      onAddLog?.({
        level: "info",
        title: "Fetched GUS Data",
        message: `Successfully fetched info for ${info.name || cleanNip}`,
        details: { ...info },
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to fetch company info";
      onAddLog?.({
        level: "error",
        title: "GUS Lookup Failed",
        message: msg,
        details: { nip: cleanNip },
      });
      alert(msg);
    } finally {
      setIsFetchingGus(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
  }

  return (
    <tr className={getRowClassName(isNew, isModified)}>
      {/* NIP */}
      <td className={TD_NIP}>
        {isNew ? (
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={draft.nip}
              onChange={(e) => setDraft((prev) => ({ ...prev, nip: e.target.value }))}
              onKeyDown={handleKeyDown}
              placeholder="New NIP..."
              className="flex-1 min-w-0 bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded px-2.5 py-1 text-sm font-mono text-emerald-400 placeholder-slate-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={handleFetchGus}
              disabled={isFetchingGus || !draft.nip.trim()}
              className="p-1.5 rounded transition-colors text-sky-400 hover:text-sky-300 hover:bg-sky-600/20 disabled:text-slate-600 disabled:cursor-not-allowed disabled:hover:bg-transparent cursor-pointer shrink-0"
              title="Fetch company info from GUS API"
            >
              {isFetchingGus ? (
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              )}
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-1.5">
            <span className={getNipTextClassName(isMyCompany)}>{company.nip}</span>
            <button
              type="button"
              onClick={handleFetchGus}
              disabled={isFetchingGus}
              className="p-1 rounded transition-colors text-slate-500 hover:text-sky-400 hover:bg-sky-600/20 disabled:text-slate-700 disabled:cursor-not-allowed cursor-pointer shrink-0"
              title="Update info from GUS API"
            >
              {isFetchingGus ? (
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
            </button>
          </div>
        )}
      </td>

      {/* Company Name */}
      <td className={TD_NAME}>
        <input
          type="text"
          value={draft.name}
          onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
          onKeyDown={handleKeyDown}
          className={getInputClassName(isModified, draft.name !== company.name, isNew)}
          placeholder={isNew ? "Company Name (optional)" : "Company Name"}
        />
      </td>

      {/* Street Address */}
      <td className={TD_ADDRESS}>
        <input
          type="text"
          value={draft.address}
          onChange={(e) => setDraft((prev) => ({ ...prev, address: e.target.value }))}
          onKeyDown={handleKeyDown}
          className={getInputClassName(isModified, draft.address !== company.address, isNew)}
          placeholder="Address"
        />
      </td>

      {/* Zip Code */}
      <td className={TD_ZIP}>
        <input
          type="text"
          value={draft.zip_code}
          onChange={(e) => setDraft((prev) => ({ ...prev, zip_code: e.target.value }))}
          onKeyDown={handleKeyDown}
          className={getInputClassName(isModified, draft.zip_code !== company.zip_code, isNew, true)}
          placeholder="00-000"
        />
      </td>

      {/* City */}
      <td className={TD_CITY}>
        <input
          type="text"
          value={draft.city}
          onChange={(e) => setDraft((prev) => ({ ...prev, city: e.target.value }))}
          onKeyDown={handleKeyDown}
          className={getInputClassName(isModified, draft.city !== company.city, isNew)}
          placeholder="City"
        />
      </td>

      {/* Discount */}
      <td className={TD_DISCOUNT}>
        <div className={DISCOUNT_CONTAINER_CLASS}>
          <input
            type="number"
            min="0"
            max="100"
            step="any"
            value={draft.discount}
            onChange={(e) =>
              setDraft((prev) => ({
                ...prev,
                discount: parseFloat(e.target.value) || 0,
              }))
            }
            onKeyDown={handleKeyDown}
            className={getInputClassName(
              isModified,
              Number(draft.discount) !== Number(company.discount),
              isNew,
              true
            )}
          />
          <span className={DISCOUNT_SUFFIX_CLASS}>%</span>
        </div>
      </td>

      {/* Deadline */}
      <td className={TD_DEADLINE}>
        <div className={DEADLINE_CONTAINER_CLASS}>
          <input
            type="number"
            min="0"
            step="1"
            value={draft.deadline}
            onChange={(e) =>
              setDraft((prev) => ({
                ...prev,
                deadline: parseInt(e.target.value, 10) || 0,
              }))
            }
            onKeyDown={handleKeyDown}
            className={getInputClassName(
              isModified,
              Number(draft.deadline) !== Number(company.deadline),
              isNew,
              true
            )}
          />
          <span className={DEADLINE_SUFFIX_CLASS}>d</span>
        </div>
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
                  disabled={isSaving || !draft.nip.trim()}
                  className={draft.nip.trim() && !isSaving ? SAVE_BUTTON_ACTIVE_CLASS : SAVE_BUTTON_DISABLED_CLASS}
                  title="Save new company"
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
                disabled={isSaving}
                className={SAVE_BUTTON_ACTIVE_CLASS}
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
                onClick={() => onToggleUse(company.nip)}
                className={getUseButtonClassName(isUsed)}
                title="Use company for orders"
              >
                Use
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className={DELETE_BUTTON_CLASS}
                title="Delete company"
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
