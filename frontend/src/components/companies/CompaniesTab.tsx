import { useEffect, useState } from "react";
import type { Company } from "../../types/company";
import type { LogEntry } from "../../types/log";
import {
  createCompany,
  deleteCompany,
  fetchCompanies,
  updateCompany,
} from "../../api/companies";
import { CompanyTable } from "./CompanyTable";

type CompaniesTabProps = {
  globalNip: string | null;
  onSelectGlobalNip: (nip: string) => void;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function CompaniesTab({
  globalNip,
  onSelectGlobalNip,
  onAddLog,
}: CompaniesTabProps) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [myNip, setMyNip] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadCompanies();
  }, []);

  async function loadCompanies() {
    setIsLoading(true);
    try {
      const data = await fetchCompanies();
      setCompanies(data.companies);
      setMyNip(data.my_nip ?? null);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddCompany(nip: string, draft: Company) {
    try {
      const created = await createCompany({ ...draft, nip });
      setCompanies((prev) => [created, ...prev.filter((c) => c.nip !== created.nip)]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to add company";
      onAddLog({
        level: "error",
        title: "Failed to add company",
        message,
        details: {
          nip,
          name: draft.name,
          address: draft.address,
          zip_code: draft.zip_code,
          city: draft.city,
          discount: draft.discount,
          deadline: draft.deadline,
        },
      });
      throw err;
    }
  }

  async function handleSaveCompany(nip: string, draft: Company) {
    const updated = await updateCompany(nip, draft);
    setCompanies((prev) =>
      prev.map((c) => (c.nip === nip ? updated : c))
    );
  }

  async function handleDeleteCompany(nip: string) {
    await deleteCompany(nip);
    setCompanies((prev) => prev.filter((c) => c.nip !== nip));
    if (globalNip === nip) {
      onSelectGlobalNip(nip);
    }
  }

  return (
    <div className="w-full">
      <CompanyTable
        companies={companies}
        myNip={myNip}
        globalNip={globalNip}
        isLoading={isLoading}
        onCreateCompany={handleAddCompany}
        onToggleUse={onSelectGlobalNip}
        onSave={handleSaveCompany}
        onDelete={handleDeleteCompany}
        onAddLog={onAddLog}
      />
    </div>
  );
}
