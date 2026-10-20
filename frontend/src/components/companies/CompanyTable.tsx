import { EMPTY_COMPANY, type Company } from "../../types/company";
import type { LogEntry } from "../../types/log";
import { CompanyRow } from "./CompanyRow";

const TABLE_CONTAINER_CLASS = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm w-full";
const TABLE_WRAPPER_CLASS = "overflow-x-auto w-full";
const TABLE_CLASS = "w-full text-left text-sm table-auto";
const THEAD_CLASS = "bg-slate-950/70 text-xs uppercase text-slate-400 border-b border-slate-800";
const TBODY_CLASS = "divide-y divide-slate-800/60";
const EMPTY_STATE_CLASS = "py-20 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl w-full";
const EMPTY_ROW_CLASS = "py-12 text-center text-slate-500 text-sm";

const TH_NIP = "py-3 px-3 w-52 min-w-[200px] whitespace-nowrap";
const TH_NAME = "py-3 px-3 min-w-[320px] w-full";
const TH_ADDRESS = "py-3 px-3 w-80 min-w-[280px]";
const TH_ZIP = "py-3 px-3 w-32 min-w-[110px] max-w-[130px]";
const TH_CITY = "py-3 px-3 w-52 min-w-[180px] max-w-[240px]";
const TH_DISCOUNT = "py-3 px-3 w-36 min-w-[130px] max-w-[160px]";
const TH_DEADLINE = "py-3 px-3 w-28 min-w-[95px] max-w-[115px]";
const TH_ACTIONS = "py-3 px-3 w-28 min-w-[100px] text-right";

type CompanyTableProps = {
  companies: Company[];
  myNip?: string | null;
  globalNip?: string | null;
  isLoading: boolean;
  onCreateCompany: (nip: string, draft: Company) => Promise<void>;
  onToggleUse: (nip: string) => void;
  onSave: (nip: string, draft: Company) => Promise<void>;
  onDelete: (nip: string, name: string) => Promise<void>;
  onAddLog?: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function CompanyTable({
  companies,
  myNip,
  globalNip,
  isLoading,
  onCreateCompany,
  onToggleUse,
  onSave,
  onDelete,
  onAddLog,
}: CompanyTableProps) {
  if (isLoading && companies.length === 0) {
    return <div className={EMPTY_STATE_CLASS}>Loading companies...</div>;
  }

  return (
    <div className={TABLE_CONTAINER_CLASS}>
      <div className={TABLE_WRAPPER_CLASS}>
        <table className={TABLE_CLASS}>
          <thead className={THEAD_CLASS}>
            <tr>
              <th className={TH_NIP}>NIP</th>
              <th className={TH_NAME}>Company Name</th>
              <th className={TH_ADDRESS}>Address</th>
              <th className={TH_ZIP}>Zip Code</th>
              <th className={TH_CITY}>City</th>
              <th className={TH_DISCOUNT}>Discount</th>
              <th className={TH_DEADLINE}>Deadline</th>
              <th className={TH_ACTIONS}>Actions</th>
            </tr>
          </thead>
          <tbody className={TBODY_CLASS}>
            <CompanyRow
              key="new-company-row"
              company={EMPTY_COMPANY}
              isUsed={false}
              onToggleUse={() => {}}
              onSave={onCreateCompany}
              onDelete={async () => {}}
              onAddLog={onAddLog}
            />

            {companies.map((c) => (
              <CompanyRow
                key={c.nip}
                company={c}
                myNip={myNip}
                isUsed={Boolean(globalNip && globalNip === c.nip)}
                onToggleUse={onToggleUse}
                onSave={onSave}
                onDelete={onDelete}
                onAddLog={onAddLog}
              />
            ))}

            {companies.length === 0 && (
              <tr>
                <td colSpan={8} className={EMPTY_ROW_CLASS}>
                  No companies in database yet. Enter company details in the top row to add your first company.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
