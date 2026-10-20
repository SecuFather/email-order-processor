export type Client = {
  email: string;
  nip: string;
  created_at: string;
  company_name?: string | null;
};

export const EMPTY_CLIENT: Client = {
  email: "",
  nip: "",
  created_at: "",
  company_name: null,
};
