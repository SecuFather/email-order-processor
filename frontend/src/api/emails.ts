import type {
  EmailAttachment,
  EmailDetail,
  EmailOrderStreamEvent,
  EmailSummary,
} from "../types/email";

type RawAttachment = {
  filename: string;
  content_type?: string;
  data?: string;
  url?: string;
  markdown?: string;
};

export async function fetchEmails(): Promise<{ emails: EmailSummary[] }> {
  const res = await fetch("/api/emails");
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch emails");
  }
  return res.json();
}

export async function fetchEmailDetail(id: number): Promise<EmailDetail> {
  const res = await fetch(`/api/emails/${id}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch email details");
  }
  const data = await res.json();
  const attachments: EmailAttachment[] = (data.attachments as RawAttachment[]).map((a) => ({
    filename: a.filename,
    markdown: a.markdown,
    url:
      a.url ||
      (a.data &&
        URL.createObjectURL(
          new Blob([Uint8Array.from(atob(a.data), (c) => c.charCodeAt(0))], {
            type: a.content_type,
          })
        )),
  }));
  return { ...data, attachments };
}

export async function createEmail(eml_text: string): Promise<EmailSummary> {
  const res = await fetch("/api/emails", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ eml_text }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to add email");
  }
  return res.json();
}

export async function updateEmail(
  id: number,
  data: {
    nip?: string | null;
    shipping_id?: number | null;
    notes?: string;
    woocommerce_id?: number | null;
  }
): Promise<EmailSummary> {
  const res = await fetch(`/api/emails/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update email");
  }
  return res.json();
}

export async function submitEmailWooCommerceOrder(
  id: number,
  confirmed: boolean = true
): Promise<{
  ok: boolean;
  woocommerce_id: number;
  order_url: string;
  fakturownia_id?: number;
  fakturownia_number?: string;
  fakturownia_url?: string;
}> {
  const res = await fetch(`/api/emails/${id}/submit-woocommerce`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit WooCommerce order");
  }
  return res.json();
}

export async function streamEmailOrder(
  id: number,
  onEvent: (event: EmailOrderStreamEvent) => void
): Promise<void> {
  const res = await fetch(`/api/emails/${id}/order`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to generate order");
  }
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop()!;

    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.startsWith("data: ")) {
        onEvent(JSON.parse(trimmed.slice(6)) as EmailOrderStreamEvent);
      }
    }
  }
}
