export type Shipping = {
  id: number;
  nip: string;
  name: string;
  address: string;
  zip_code: string;
  city: string;
  phone: string;
  email: string;
  created_at?: string;
  updated_at?: string;
  company_name?: string | null;
};

export type ShippingsResponse = {
  shippings: Shipping[];
};

export const EMPTY_SHIPPING: Shipping = {
  id: 0,
  nip: "",
  name: "",
  address: "",
  zip_code: "",
  city: "",
  phone: "",
  email: "",
  company_name: null,
};
