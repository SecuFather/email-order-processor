export type Company = {
  nip: string;
  name: string;
  address: string;
  zip_code: string;
  city: string;
  discount: number;
  deadline: number;
};

export type CompaniesResponse = {
  companies: Company[];
  my_nip?: string | null;
};

export const EMPTY_COMPANY: Company = {
  nip: "",
  name: "",
  address: "",
  zip_code: "",
  city: "",
  discount: 0,
  deadline: 0,
};
