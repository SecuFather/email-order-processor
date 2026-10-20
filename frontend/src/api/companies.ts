import type { CompaniesResponse, Company } from "../types/company";

export async function fetchCompanies(): Promise<CompaniesResponse> {
  const res = await fetch("/api/companies");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch companies");
  }
  return res.json();
}

export async function createCompany(
  data: Partial<Company> & { nip: string }
): Promise<Company> {
  const res = await fetch("/api/companies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create company");
  }
  return res.json();
}

export async function updateCompany(
  nip: string,
  data: Partial<Company>
): Promise<Company> {
  const res = await fetch(`/api/companies/${nip}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update company");
  }
  return res.json();
}

export async function deleteCompany(nip: string): Promise<void> {
  const res = await fetch(`/api/companies/${nip}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete company");
  }
}

export type GusCompany = {
  nip: string;
  name: string;
  address: string;
  zip_code: string;
  city: string;
};

export async function fetchCompanyFromGus(nip: string): Promise<GusCompany> {
  const res = await fetch(`/api/companies/lookup/${encodeURIComponent(nip)}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch company info from GUS");
  }
  return res.json();
}
