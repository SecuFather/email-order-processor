export type AmbiguityPair = {
  id: number;
  product_id_a: number;
  product_id_b: number;
  chosen_product_id: number;
  name_a: string | null;
  name_b: string | null;
  chosen_name: string | null;
};

export const EMPTY_AMBIGUITY_PAIR: AmbiguityPair = {
  id: 0,
  product_id_a: 0,
  product_id_b: 0,
  chosen_product_id: 0,
  name_a: null,
  name_b: null,
  chosen_name: null,
};

export type CreateAmbiguityPairPayload = {
  product_id_a: number;
  product_id_b: number;
  chosen_product_id: number;
};
