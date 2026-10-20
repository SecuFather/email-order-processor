import type { Product } from "./product";

export type EmailSummary = {
  id: number;
  nip: string | null;
  company_name: string | null;
  company_discount: number;
  shipping_id: number | null;
  shipping_name: string | null;
  woocommerce_id: number | null;
  woocommerce_url?: string | null;
  fakturownia_id?: number | null;
  fakturownia_number?: string | null;
  fakturownia_url?: string | null;
  date: string;
  sender: string;
  recipient: string;
  title: string;
  notes: string;
  created_at: string;
};

export type EmailAttachment = {
  filename: string;
  url?: string;
  markdown?: string;
};

export type OrderCartProduct = {
  product_id: number;
  amount: number;
  product?: Product | null;
};

export type OrderCartSegment = {
  at: number;
  text?: string;
  products?: Record<string, OrderCartProduct>;
};

export type OrderCart = Record<string, OrderCartSegment>;

export type ToolCall = {
  function: {
    name: string;
    arguments: Record<string, unknown>;
  };
};

export type ChatMessage = {
  role: "user" | "assistant" | "tool";
  content: string;
  thinking?: string;
  tool_name?: string;
  tool_calls?: ToolCall[] | null;
  stats?: {
    prompt_tokens: number;
    eval_tokens: number;
  };
};

export type EmailOrderStreamEvent =
  | { type: "start"; messages: ChatMessage[]; cart: OrderCart }
  | { type: "turn"; message: ChatMessage }
  | { type: "assistant"; message: ChatMessage }
  | { type: "tool"; message: ChatMessage; cart: OrderCart }
  | {
      type: "done";
      cart: OrderCart;
      messages: ChatMessage[];
      stats: { prompt_tokens: number; eval_tokens: number };
    };

export type EmailDetail = EmailSummary & {
  eml_text: string;
  subject: string | null;
  from: string | null;
  to: string | null;
  html: string;
  attachments: EmailAttachment[];
  cart: OrderCart;
  messages: ChatMessage[];
};
