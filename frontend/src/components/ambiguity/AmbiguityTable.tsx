import {
  EMPTY_AMBIGUITY_PAIR,
  type AmbiguityPair,
  type CreateAmbiguityPairPayload,
} from "../../types/ambiguity";
import { AmbiguityRow } from "./AmbiguityRow";

const TABLE_CONTAINER_CLASS =
  "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm w-full";
const TABLE_WRAPPER_CLASS = "overflow-x-auto w-full";
const TABLE_CLASS = "w-full text-left text-sm table-auto";
const THEAD_CLASS =
  "bg-slate-950/70 text-xs uppercase text-slate-400 border-b border-slate-800";
const TBODY_CLASS = "divide-y divide-slate-800/60";
const EMPTY_STATE_CLASS =
  "py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full";
const EMPTY_ROW_CLASS = "py-12 text-center text-slate-500 text-sm";

const TH_PROD_A = "py-3 px-3 min-w-[200px] w-1/3";
const TH_PROD_B = "py-3 px-3 min-w-[200px] w-1/3";
const TH_CHOSEN = "py-3 px-3 min-w-[200px] w-1/3";
const TH_ACTIONS = "py-3 px-3 w-28 min-w-[100px] text-right";

type AmbiguityTableProps = {
  pairs: AmbiguityPair[];
  isLoading: boolean;
  onCreatePair: (draft: CreateAmbiguityPairPayload) => Promise<void>;
  onDeletePair: (id: number) => Promise<void>;
};

export function AmbiguityTable({
  pairs,
  isLoading,
  onCreatePair,
  onDeletePair,
}: AmbiguityTableProps) {
  if (isLoading && pairs.length === 0) {
    return (
      <div className={EMPTY_STATE_CLASS}>
        Loading ambiguity resolution rules...
      </div>
    );
  }

  return (
    <div className={TABLE_CONTAINER_CLASS}>
      <div className={TABLE_WRAPPER_CLASS}>
        <table className={TABLE_CLASS}>
          <thead className={THEAD_CLASS}>
            <tr>
              <th className={TH_PROD_A}>Product A</th>
              <th className={TH_PROD_B}>Product B</th>
              <th className={TH_CHOSEN}>Preferred Choice</th>
              <th className={TH_ACTIONS}>Actions</th>
            </tr>
          </thead>
          <tbody className={TBODY_CLASS}>
            <AmbiguityRow
              key="new-ambiguity-row"
              pair={EMPTY_AMBIGUITY_PAIR}
              onSave={onCreatePair}
              onDelete={async () => {}}
            />

            {pairs.map((p) => (
              <AmbiguityRow
                key={p.id}
                pair={p}
                onSave={async () => {}}
                onDelete={onDeletePair}
              />
            ))}

            {pairs.length === 0 && (
              <tr>
                <td colSpan={4} className={EMPTY_ROW_CLASS}>
                  No ambiguity resolution rules found. Enter product IDs in the
                  top row to add your first rule.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
