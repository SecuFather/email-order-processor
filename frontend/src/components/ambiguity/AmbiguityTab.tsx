import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/log";
import type { AmbiguityPair, CreateAmbiguityPairPayload } from "../../types/ambiguity";
import {
  createAmbiguityPair,
  deleteAmbiguityPair,
  fetchAmbiguityPairs,
} from "../../api/ambiguity";
import { AmbiguityTable } from "./AmbiguityTable";

type AmbiguityTabProps = {
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function AmbiguityTab({ onAddLog }: AmbiguityTabProps) {
  const [pairs, setPairs] = useState<AmbiguityPair[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadPairs();
  }, []);

  async function loadPairs() {
    setIsLoading(true);
    try {
      const data = await fetchAmbiguityPairs();
      setPairs(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load ambiguity rules";
      onAddLog({
        level: "error",
        title: "Failed to load ambiguity rules",
        message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddPair(draft: CreateAmbiguityPairPayload) {
    try {
      await createAmbiguityPair(draft);
      const updated = await fetchAmbiguityPairs();
      setPairs(updated);
      onAddLog({
        level: "info",
        title: "Ambiguity rule created",
        message: `Set preferred product #${draft.chosen_product_id} for pair #${draft.product_id_a} and #${draft.product_id_b}`,
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create ambiguity rule";
      onAddLog({
        level: "error",
        title: "Failed to create ambiguity rule",
        message,
      });
      throw err;
    }
  }

  async function handleDeletePair(pairId: number) {
    try {
      await deleteAmbiguityPair(pairId);
      setPairs((prev) => prev.filter((p) => p.id !== pairId));
      onAddLog({
        level: "info",
        title: "Ambiguity rule deleted",
        message: `Removed ambiguity rule #${pairId}`,
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete ambiguity rule";
      onAddLog({
        level: "error",
        title: "Failed to delete ambiguity rule",
        message,
      });
    }
  }

  return (
    <div className="w-full">
      <AmbiguityTable
        pairs={pairs}
        isLoading={isLoading}
        onCreatePair={handleAddPair}
        onDeletePair={handleDeletePair}
      />
    </div>
  );
}
