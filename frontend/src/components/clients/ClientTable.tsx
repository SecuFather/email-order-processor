import { EMPTY_CLIENT, type Client } from "../../types/client";
import { ClientRow } from "./ClientRow";

const TABLE_CONTAINER_CLASS = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm w-full";
const TABLE_WRAPPER_CLASS = "overflow-x-auto w-full";
const TABLE_CLASS = "w-full text-left text-sm table-auto";
const THEAD_CLASS = "bg-slate-950/70 text-xs uppercase text-slate-400 border-b border-slate-800";
const TBODY_CLASS = "divide-y divide-slate-800/60";
const EMPTY_STATE_CLASS = "py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full";
const EMPTY_ROW_CLASS = "py-12 text-center text-slate-500 text-sm";

const TH_EMAIL = "py-3 px-3 min-w-[260px] w-1/3";
const TH_NIP = "py-3 px-3 w-48 min-w-[180px] whitespace-nowrap";
const TH_COMPANY = "py-3 px-3 min-w-[220px] w-1/2";
const TH_ACTIONS = "py-3 px-3 w-28 min-w-[100px] text-right";

type ClientTableProps = {
  clients: Client[];
  globalNip?: string | null;
  isLoading: boolean;
  onCreateClient: (draft: { email: string; nip: string }) => Promise<void>;
  onToggleUse: (nip: string) => void;
  onSave: (originalEmail: string, draft: Client) => Promise<void>;
  onDelete: (email: string) => Promise<void>;
};

export function ClientTable({
  clients,
  globalNip,
  isLoading,
  onCreateClient,
  onToggleUse,
  onSave,
  onDelete,
}: ClientTableProps) {
  if (isLoading && clients.length === 0) {
    return <div className={EMPTY_STATE_CLASS}>Loading client mappings...</div>;
  }

  return (
    <div className={TABLE_CONTAINER_CLASS}>
      <div className={TABLE_WRAPPER_CLASS}>
        <table className={TABLE_CLASS}>
          <thead className={THEAD_CLASS}>
            <tr>
              <th className={TH_EMAIL}>Email Address</th>
              <th className={TH_NIP}>NIP</th>
              <th className={TH_COMPANY}>Linked Company</th>
              <th className={TH_ACTIONS}>Actions</th>
            </tr>
          </thead>
          <tbody className={TBODY_CLASS}>
            <ClientRow
              key="new-client-row"
              client={EMPTY_CLIENT}
              globalNip={globalNip}
              isUsed={false}
              onToggleUse={() => {}}
              onSave={async (_, draft) => onCreateClient(draft)}
              onDelete={async () => {}}
            />

            {clients.map((c) => (
              <ClientRow
                key={c.email}
                client={c}
                globalNip={globalNip}
                isUsed={Boolean(globalNip && globalNip === c.nip)}
                onToggleUse={onToggleUse}
                onSave={onSave}
                onDelete={onDelete}
              />
            ))}

            {clients.length === 0 && (
              <tr>
                <td colSpan={4} className={EMPTY_ROW_CLASS}>
                  No client mappings found. Enter email and NIP in the top row to map your first client.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
