import { useEffect, useState } from "react";
import type { Shipping } from "../../types/shipping";
import type { LogEntry } from "../../types/log";
import {
  createShipping,
  deleteShipping,
  fetchShippings,
  updateShipping,
} from "../../api/shipping";
import { ShippingTable } from "./ShippingTable";

type ShippingTabProps = {
  globalNip: string | null;
  globalShippingId: number | null;
  onSelectGlobalShippingId: (id: number) => void;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function ShippingTab({
  globalNip,
  globalShippingId,
  onSelectGlobalShippingId,
  onAddLog,
}: ShippingTabProps) {
  const [shippings, setShippings] = useState<Shipping[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadShippings();
  }, []);

  async function loadShippings() {
    setIsLoading(true);
    try {
      const data = await fetchShippings();
      setShippings(data.shippings);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load shipping addresses";
      onAddLog({
        level: "error",
        title: "Failed to load shipping addresses",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateShipping(_: number, draft: Shipping) {
    try {
      const created = await createShipping({
        nip: draft.nip,
        name: draft.name,
        address: draft.address,
        zip_code: draft.zip_code,
        city: draft.city,
        phone: draft.phone,
        email: draft.email,
      });
      setShippings((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
      onAddLog({
        level: "info",
        title: "Shipping address created",
        message: `Created shipping address "${created.name}"`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create shipping address";
      onAddLog({
        level: "error",
        title: "Failed to create shipping address",
        message,
        details: {
          nip: draft.nip,
          name: draft.name,
          address: draft.address,
          zip_code: draft.zip_code,
          city: draft.city,
          phone: draft.phone,
          email: draft.email,
        },
      });
      throw err;
    }
  }

  async function handleSaveShipping(id: number, draft: Shipping) {
    try {
      const updated = await updateShipping(id, {
        nip: draft.nip,
        name: draft.name,
        address: draft.address,
        zip_code: draft.zip_code,
        city: draft.city,
        phone: draft.phone,
        email: draft.email,
      });
      setShippings((prev) =>
        prev.map((s) => (s.id === id ? updated : s))
      );
      onAddLog({
        level: "info",
        title: "Shipping address updated",
        message: `Updated shipping address "${updated.name}"`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update shipping address";
      onAddLog({
        level: "error",
        title: "Failed to update shipping address",
        message,
        details: draft,
      });
      throw err;
    }
  }

  async function handleDeleteShipping(id: number, name: string) {
    try {
      await deleteShipping(id);
      setShippings((prev) => prev.filter((s) => s.id !== id));
      if (globalShippingId === id) {
        onSelectGlobalShippingId(id);
      }
      onAddLog({
        level: "info",
        title: "Shipping address deleted",
        message: `Removed shipping address "${name}"`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete shipping address";
      onAddLog({
        level: "error",
        title: "Failed to delete shipping address",
        message,
        details: { id, name },
      });
    }
  }

  return (
    <div className="w-full">
      <ShippingTable
        shippings={shippings}
        globalNip={globalNip}
        globalShippingId={globalShippingId}
        isLoading={isLoading}
        onCreateShipping={handleCreateShipping}
        onToggleUse={onSelectGlobalShippingId}
        onSave={handleSaveShipping}
        onDelete={handleDeleteShipping}
        onAddLog={onAddLog}
      />
    </div>
  );
}
