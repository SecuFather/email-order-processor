import type { Client } from "../types/client";

export async function fetchClients(nip?: string): Promise<{ clients: Client[] }> {
  const url = nip ? `/api/clients?nip=${encodeURIComponent(nip)}` : "/api/clients";
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch clients");
  }
  return res.json();
}

export async function createClient(data: { email: string; nip: string }): Promise<Client> {
  const res = await fetch("/api/clients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create client");
  }
  return res.json();
}

export async function updateClient(
  originalEmail: string,
  data: { email: string; nip: string }
): Promise<Client> {
  const res = await fetch(`/api/clients/${encodeURIComponent(originalEmail)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update client");
  }
  return res.json();
}

export async function deleteClient(email: string): Promise<void> {
  const res = await fetch(`/api/clients/${encodeURIComponent(email)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete client");
  }
}
