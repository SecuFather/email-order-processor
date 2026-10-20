import type {
  AmbiguityPair,
  CreateAmbiguityPairPayload,
} from "../types/ambiguity";

export async function fetchAmbiguityPairs(): Promise<AmbiguityPair[]> {
  const res = await fetch("/api/order-maker/ambiguity-pairs");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch ambiguity rules");
  }
  const data = await res.json();
  return data.pairs;
}

export async function createAmbiguityPair(
  payload: CreateAmbiguityPairPayload
): Promise<void> {
  const res = await fetch("/api/order-maker/ambiguity-pairs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create ambiguity rule");
  }
}

export async function deleteAmbiguityPair(pairId: number): Promise<void> {
  const res = await fetch(`/api/order-maker/ambiguity-pairs/${pairId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete ambiguity rule");
  }
}
