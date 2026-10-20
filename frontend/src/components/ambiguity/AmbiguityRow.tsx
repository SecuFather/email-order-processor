import { useState, type KeyboardEvent } from "react";
import type { AmbiguityPair, CreateAmbiguityPairPayload } from "../../types/ambiguity";

const TD_PROD_A = "py-2.5 px-3 min-w-[200px] w-1/3";
const TD_PROD_B = "py-2.5 px-3 min-w-[200px] w-1/3";
const TD_CHOSEN = "py-2.5 px-3 min-w-[200px] w-1/3";
const TD_ACTIONS = "py-2.5 px-3 w-28 min-w-[100px] text-right whitespace-nowrap";

const ACTIONS_CONTAINER_CLASS = "flex items-center justify-end gap-1.5";
const SAVE_BUTTON_ACTIVE_CLASS =
  "p-1 rounded cursor-pointer transition-colors hover:bg-emerald-600/20 text-emerald-400";
const SAVE_BUTTON_DISABLED_CLASS =
  "p-1 rounded transition-colors text-slate-600 cursor-not-allowed";
const DISCARD_BUTTON_CLASS =
  "p-1 hover:bg-amber-600/20 text-amber-400 rounded cursor-pointer transition-colors";
const DELETE_BUTTON_CLASS =
  "p-1 hover:bg-red-600/20 text-slate-500 hover:text-red-400 rounded cursor-pointer transition-colors";

function getRowClassName(isNew: boolean): string {
  if (isNew) {
    return "transition-colors border-b bg-slate-900/90 border-b-2 border-indigo-500/30";
  }
  return "transition-colors border-b hover:bg-slate-800/40 border-slate-800/60";
}

function getInputClassName(isNew: boolean, isMono = false): string {
  const font = isMono
    ? "font-mono text-emerald-400 placeholder-slate-500"
    : "text-slate-100 placeholder-slate-500";
  const border = isNew
    ? "border-slate-800 hover:border-slate-700 focus:border-indigo-500 bg-slate-950"
    : "border-transparent hover:border-slate-700 focus:border-indigo-500 bg-transparent";
  return `w-full border rounded px-2.5 py-1 text-sm focus:bg-slate-950 focus:outline-none transition-colors ${font} ${border}`;
}

type AmbiguityRowProps = {
  pair: AmbiguityPair;
  onSave: (draft: CreateAmbiguityPairPayload) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
};

export function AmbiguityRow({ pair, onSave, onDelete }: AmbiguityRowProps) {
  const isNew = pair.id === 0;

  const [pairA, setPairA] = useState("");
  const [pairB, setPairB] = useState("");
  const [pairChosen, setPairChosen] = useState<"A" | "B">("A");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const numA = parseInt(pairA, 10);
  const numB = parseInt(pairB, 10);
  const isModified = Boolean(pairA.trim() || pairB.trim());
  const canSave = Boolean(numA && numB && numA !== numB && !isSaving);

  function handleDiscard() {
    setPairA("");
    setPairB("");
    setPairChosen("A");
  }

  async function handleSave() {
    if (!canSave) return;
    setIsSaving(true);
    try {
      const chosenId = pairChosen === "A" ? numA : numB;
      await onSave({
        product_id_a: numA,
        product_id_b: numB,
        chosen_product_id: chosenId,
      });
      handleDiscard();
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (isDeleting || isNew) return;
    if (
      window.confirm(
        `Delete ambiguity rule for product #${pair.product_id_a} and #${pair.product_id_b}?`
      )
    ) {
      setIsDeleting(true);
      try {
        await onDelete(pair.id);
      } finally {
        setIsDeleting(false);
      }
    }
  }

  function handleKeyDown(
    e: KeyboardEvent<HTMLInputElement | HTMLSelectElement>
  ) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleDiscard();
    }
  }

  if (isNew) {
    return (
      <tr className={getRowClassName(true)}>
        {/* Product A Input */}
        <td className={TD_PROD_A}>
          <input
            type="number"
            value={pairA}
            onChange={(e) => setPairA(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Product ID A..."
            className={getInputClassName(true, true)}
          />
        </td>

        {/* Product B Input */}
        <td className={TD_PROD_B}>
          <input
            type="number"
            value={pairB}
            onChange={(e) => setPairB(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Product ID B..."
            className={getInputClassName(true, true)}
          />
        </td>

        {/* Preferred Selector */}
        <td className={TD_CHOSEN}>
          <select
            value={pairChosen}
            onChange={(e) => setPairChosen(e.target.value as "A" | "B")}
            onKeyDown={handleKeyDown}
            className="w-full border border-slate-800 hover:border-slate-700 focus:border-indigo-500 bg-slate-950 rounded px-2.5 py-1 text-sm font-mono text-slate-200 focus:outline-none transition-colors cursor-pointer"
          >
            <option value="A">
              {numA ? `Choose ID A (#${numA})` : "Choose ID A"}
            </option>
            <option value="B">
              {numB ? `Choose ID B (#${numB})` : "Choose ID B"}
            </option>
          </select>
        </td>

        {/* Actions */}
        <td className={TD_ACTIONS}>
          <div className={ACTIONS_CONTAINER_CLASS}>
            {isModified && (
              <>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!canSave}
                  className={
                    canSave
                      ? SAVE_BUTTON_ACTIVE_CLASS
                      : SAVE_BUTTON_DISABLED_CLASS
                  }
                  title="Save new ambiguity rule"
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
                </button>

                <button
                  type="button"
                  onClick={handleDiscard}
                  className={DISCARD_BUTTON_CLASS}
                  title="Discard input"
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
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </>
            )}
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr className={getRowClassName(false)}>
      {/* Product A */}
      <td className={TD_PROD_A}>
        <span className="font-mono text-slate-200 text-sm">
          #{pair.product_id_a}
        </span>
        {pair.name_a && (
          <span className="text-slate-400 font-sans text-xs ml-1.5">
            ({pair.name_a})
          </span>
        )}
      </td>

      {/* Product B */}
      <td className={TD_PROD_B}>
        <span className="font-mono text-slate-200 text-sm">
          #{pair.product_id_b}
        </span>
        {pair.name_b && (
          <span className="text-slate-400 font-sans text-xs ml-1.5">
            ({pair.name_b})
          </span>
        )}
      </td>

      {/* Preferred Choice */}
      <td className={TD_CHOSEN}>
        <span className="font-mono text-emerald-400 font-semibold text-sm">
          #{pair.chosen_product_id}
        </span>
        {pair.chosen_name && (
          <span className="text-slate-300 font-sans text-xs font-normal ml-1.5">
            ({pair.chosen_name})
          </span>
        )}
      </td>

      {/* Actions */}
      <td className={TD_ACTIONS}>
        <div className={ACTIONS_CONTAINER_CLASS}>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className={DELETE_BUTTON_CLASS}
            title="Delete ambiguity rule"
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
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </td>
    </tr>
  );
}
