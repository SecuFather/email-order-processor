import { useEffect, useState } from "react";
import type { Client } from "../../types/client";
import type { LogEntry } from "../../types/log";
import {
  createClient,
  deleteClient,
  fetchClients,
  updateClient,
} from "../../api/clients";
import { ClientTable } from "./ClientTable";

type ClientsTabProps = {
  globalNip: string | null;
  onSelectGlobalNip: (nip: string) => void;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function ClientsTab({
  globalNip,
  onSelectGlobalNip,
  onAddLog,
}: ClientsTabProps) {
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadClients();
  }, []);

  async function loadClients() {
    setIsLoading(true);
    try {
      const data = await fetchClients();
      setClients(data.clients);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load clients";
      onAddLog({
        level: "error",
        title: "Failed to load clients",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateClient(draft: { email: string; nip: string }) {
    try {
      const created = await createClient(draft);
      setClients((prev) => [created, ...prev.filter((c) => c.email !== created.email)]);
      onAddLog({
        level: "info",
        title: "Client mapping created",
        message: `Mapped ${created.email} ↔ NIP ${created.nip}`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create client mapping";
      onAddLog({
        level: "error",
        title: "Failed to create client mapping",
        message,
        details: draft,
      });
      throw err;
    }
  }

  async function handleSaveClient(originalEmail: string, draft: Client) {
    try {
      const updated = await updateClient(originalEmail, {
        email: draft.email,
        nip: draft.nip,
      });
      setClients((prev) =>
        prev.map((c) => (c.email === originalEmail ? updated : c))
      );
      onAddLog({
        level: "info",
        title: "Client mapping updated",
        message: `Updated mapping for ${updated.email} ↔ NIP ${updated.nip}`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update client mapping";
      onAddLog({
        level: "error",
        title: "Failed to update client mapping",
        message,
        details: { originalEmail, ...draft },
      });
      throw err;
    }
  }

  async function handleDeleteClient(email: string) {
    try {
      await deleteClient(email);
      setClients((prev) => prev.filter((c) => c.email !== email));
      onAddLog({
        level: "info",
        title: "Client mapping deleted",
        message: `Removed mapping for ${email}`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete client mapping";
      onAddLog({
        level: "error",
        title: "Failed to delete client mapping",
        message,
        details: { email },
      });
    }
  }

  return (
    <div className="w-full">
      <ClientTable
        clients={clients}
        globalNip={globalNip}
        isLoading={isLoading}
        onCreateClient={handleCreateClient}
        onToggleUse={onSelectGlobalNip}
        onSave={handleSaveClient}
        onDelete={handleDeleteClient}
      />
    </div>
  );
}
