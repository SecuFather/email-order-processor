import { EMPTY_SHIPPING, type Shipping } from "../../types/shipping";
import type { LogEntry } from "../../types/log";
import { ShippingRow } from "./ShippingRow";

const TABLE_CONTAINER_CLASS = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm w-full";
const TABLE_WRAPPER_CLASS = "overflow-x-auto w-full";
const TABLE_CLASS = "w-full text-left text-sm table-auto";
const THEAD_CLASS = "bg-slate-950/70 text-xs uppercase text-slate-400 border-b border-slate-800";
const TBODY_CLASS = "divide-y divide-slate-800/60";
const EMPTY_STATE_CLASS = "py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full";
const EMPTY_ROW_CLASS = "py-12 text-center text-slate-500 text-sm";

const TH_NIP = "py-3 px-3 w-48 min-w-[170px] whitespace-nowrap";
const TH_NAME = "py-3 px-3 min-w-[240px] w-full";
const TH_ADDRESS = "py-3 px-3 w-72 min-w-[220px]";
const TH_ZIP = "py-3 px-3 w-32 min-w-[110px] max-w-[130px]";
const TH_CITY = "py-3 px-3 w-48 min-w-[160px] max-w-[220px]";
const TH_PHONE = "py-3 px-3 w-60 min-w-[210px]";
const TH_EMAIL = "py-3 px-3 w-80 min-w-[300px]";
const TH_ACTIONS = "py-3 px-3 w-28 min-w-[100px] text-right";

type ShippingTableProps = {
  shippings: Shipping[];
  globalNip?: string | null;
  globalShippingId?: number | null;
  isLoading: boolean;
  onCreateShipping: (id: number, draft: Shipping) => Promise<void>;
  onToggleUse: (id: number) => void;
  onSave: (id: number, draft: Shipping) => Promise<void>;
  onDelete: (id: number, name: string) => Promise<void>;
  onAddLog?: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function ShippingTable({
  shippings,
  globalNip,
  globalShippingId,
  isLoading,
  onCreateShipping,
  onToggleUse,
  onSave,
  onDelete,
  onAddLog,
}: ShippingTableProps) {
  if (isLoading && shippings.length === 0) {
    return <div className={EMPTY_STATE_CLASS}>Loading shipping addresses...</div>;
  }

  return (
    <div className={TABLE_CONTAINER_CLASS}>
      <div className={TABLE_WRAPPER_CLASS}>
        <table className={TABLE_CLASS}>
          <thead className={THEAD_CLASS}>
            <tr>
              <th className={TH_NIP}>NIP</th>
              <th className={TH_NAME}>Recipient / Name</th>
              <th className={TH_ADDRESS}>Address</th>
              <th className={TH_ZIP}>Zip Code</th>
              <th className={TH_CITY}>City</th>
              <th className={TH_PHONE}>Phone</th>
              <th className={TH_EMAIL}>Email</th>
              <th className={TH_ACTIONS}>Actions</th>
            </tr>
          </thead>
          <tbody className={TBODY_CLASS}>
            <ShippingRow
              key="new-shipping-row"
              shipping={EMPTY_SHIPPING}
              globalNip={globalNip}
              isUsed={false}
              onToggleUse={() => {}}
              onSave={onCreateShipping}
              onDelete={async () => {}}
              onAddLog={onAddLog}
            />

            {shippings.map((s) => (
              <ShippingRow
                key={s.id}
                shipping={s}
                globalNip={globalNip}
                isUsed={globalShippingId === s.id}
                onToggleUse={onToggleUse}
                onSave={onSave}
                onDelete={onDelete}
                onAddLog={onAddLog}
              />
            ))}

            {shippings.length === 0 && (
              <tr>
                <td colSpan={8} className={EMPTY_ROW_CLASS}>
                  No shipping addresses in database yet. Enter details in the top row to add your first shipping address.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
