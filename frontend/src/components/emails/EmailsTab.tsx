import { useEffect, useState } from "react";
import type { EmailAttachment, EmailDetail, EmailSummary } from "../../types/email";
import type { LogEntry } from "../../types/log";
import {
  createEmail,
  fetchEmailDetail,
  fetchEmails,
  streamEmailOrder,
  submitEmailWooCommerceOrder,
  updateEmail,
} from "../../api/emails";
import { EmailList } from "./EmailList";
import { EmlViewer } from "./EmlViewer";

type EmailsTabProps = {
  globalNip: string | null;
  globalShippingId: number | null;
  onAddLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
};

export function EmailsTab({
  globalNip,
  globalShippingId,
  onAddLog,
}: EmailsTabProps) {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<EmailDetail | null>(null);
  const [activeAttachment, setActiveAttachment] = useState<EmailAttachment | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGeneratingOrder, setIsGeneratingOrder] = useState(false);
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);

  useEffect(() => {
    loadEmails();
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      setSelectedEmail(null);
      setActiveAttachment(null);
      return;
    }
    loadEmailDetail(selectedId);
  }, [selectedId]);

  async function loadEmails() {
    setIsLoadingList(true);
    try {
      const data = await fetchEmails();
      setEmails(data.emails);
      if (data.emails.length > 0 && selectedId === null) {
        setSelectedId(data.emails[0].id);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load emails";
      onAddLog({ level: "error", title: "Failed to load emails", message });
    } finally {
      setIsLoadingList(false);
    }
  }

  async function loadEmailDetail(id: number) {
    setIsLoadingDetail(true);
    setActiveAttachment(null);
    try {
      const detail = await fetchEmailDetail(id);
      setSelectedEmail(detail);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load email content";
      onAddLog({ level: "error", title: "Failed to load email content", message });
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function handleUploadFiles(files: FileList) {
    setIsUploading(true);
    try {
      let lastCreated: EmailSummary | null = null;
      for (const file of Array.from(files)) {
        const emlText = await file.text();
        lastCreated = await createEmail(emlText);
      }
      const data = await fetchEmails();
      setEmails(data.emails);
      if (lastCreated) {
        setSelectedId(lastCreated.id);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to upload email";
      onAddLog({ level: "error", title: "Failed to upload email", message });
    } finally {
      setIsUploading(false);
    }
  }

  async function handleClickNip(id: number) {
    const currentNip = selectedEmail?.id === id ? selectedEmail.nip : null;
    const nextNip = currentNip === globalNip ? null : globalNip;
    try {
      const updated = await updateEmail(id, { nip: nextNip });
      setEmails((prev) => prev.map((e) => (e.id === id ? updated : e)));
      if (selectedEmail && selectedEmail.id === id) {
        setSelectedEmail({
          ...selectedEmail,
          nip: updated.nip,
          company_name: updated.company_name,
          company_discount: updated.company_discount,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update email NIP";
      onAddLog({
        level: "error",
        title: "Failed to update email NIP",
        message,
        details: { id, nip: nextNip },
      });
    }
  }

  async function handleClickShipping(id: number) {
    const currentShippingId = selectedEmail?.id === id ? selectedEmail.shipping_id : null;
    const nextShippingId = currentShippingId === globalShippingId ? null : globalShippingId;
    try {
      const updated = await updateEmail(id, { shipping_id: nextShippingId });
      setEmails((prev) => prev.map((e) => (e.id === id ? updated : e)));
      if (selectedEmail && selectedEmail.id === id) {
        setSelectedEmail({
          ...selectedEmail,
          shipping_id: updated.shipping_id,
          shipping_name: updated.shipping_name,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update email shipping";
      onAddLog({
        level: "error",
        title: "Failed to update email shipping",
        message,
        details: { id, shipping_id: nextShippingId },
      });
    }
  }

  async function handleSaveNotes(id: number, notes: string) {
    try {
      const updated = await updateEmail(id, { notes });
      setEmails((prev) => prev.map((e) => (e.id === id ? updated : e)));
      if (selectedEmail && selectedEmail.id === id) {
        setSelectedEmail({
          ...selectedEmail,
          notes: updated.notes,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save email notes";
      onAddLog({
        level: "error",
        title: "Failed to save email notes",
        message,
        details: { id },
      });
    }
  }

  async function handleRunOrder(id: number) {
    if (isGeneratingOrder) return;
    setIsGeneratingOrder(true);
    try {
      await streamEmailOrder(id, (event) => {
        setSelectedEmail((prev) => {
          if (!prev || prev.id !== id) return prev;
          if (event.type === "start") {
            return { ...prev, messages: event.messages, cart: event.cart };
          }
          if (event.type === "turn") {
            return { ...prev, messages: [...prev.messages, event.message] };
          }
          if (event.type === "assistant") {
            return {
              ...prev,
              messages: [...prev.messages.slice(0, -1), event.message],
            };
          }
          if (event.type === "tool") {
            return {
              ...prev,
              messages: [...prev.messages, event.message],
              cart: event.cart,
            };
          }
          if (event.type === "done") {
            return { ...prev, messages: event.messages, cart: event.cart };
          }
          return prev;
        });
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to generate order";
      onAddLog({
        level: "error",
        title: "Failed to generate order",
        message,
        details: { id },
      });
    } finally {
      setIsGeneratingOrder(false);
    }
  }

  async function handleAcceptOrder(id: number) {
    if (isSubmittingOrder) return;
    const email = emails.find((e) => e.id === id) || (selectedEmail?.id === id ? selectedEmail : null);
    if (!email?.nip) {
      onAddLog({
        level: "error",
        title: "Cannot accept order",
        message: "NIP is required to accept order and issue invoice.",
        details: { id },
      });
      return;
    }

    const confirmed = window.confirm(
      `Czy na pewno chcesz wystawić fakturę w Fakturowni dla NIP: ${email.nip}${email.company_name ? ` (${email.company_name})` : ""} i utworzyć zamówienie w WooCommerce? Tej operacji nie można łatwo cofnąć.`
    );
    if (!confirmed) return;

    setIsSubmittingOrder(true);
    try {
      const res = await submitEmailWooCommerceOrder(id, true);
      const updatedFields = {
        woocommerce_id: res.woocommerce_id,
        woocommerce_url: res.order_url,
        fakturownia_id: res.fakturownia_id,
        fakturownia_number: res.fakturownia_number,
        fakturownia_url: res.fakturownia_url,
      };
      setEmails((prev) =>
        prev.map((e) => (e.id === id ? { ...e, ...updatedFields } : e))
      );
      if (selectedEmail && selectedEmail.id === id) {
        setSelectedEmail({
          ...selectedEmail,
          ...updatedFields,
        });
      }
      onAddLog({
        level: "info",
        title: "Order accepted",
        message: `Created WooCommerce order #${res.woocommerce_id}${res.fakturownia_number ? ` and invoice ${res.fakturownia_number}` : ""}`,
        details: { id, ...res },
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to accept order";
      onAddLog({
        level: "error",
        title: "Failed to accept order",
        message,
        details: { id },
      });
    } finally {
      setIsSubmittingOrder(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <div className="lg:col-span-8">
        <EmlViewer
          email={selectedEmail}
          isLoading={isLoadingDetail}
          isGeneratingOrder={isGeneratingOrder}
          isSubmittingOrder={isSubmittingOrder}
          activeAttachment={activeAttachment}
          globalNip={globalNip}
          globalShippingId={globalShippingId}
          onSelectAttachment={setActiveAttachment}
          onClickNip={handleClickNip}
          onClickShipping={handleClickShipping}
          onSaveNotes={handleSaveNotes}
          onRunOrder={handleRunOrder}
          onAcceptOrder={handleAcceptOrder}
        />
      </div>

      <div className="lg:col-span-4">
        <EmailList
          emails={emails}
          selectedId={selectedId}
          isLoading={isLoadingList}
          isUploading={isUploading}
          onSelectEmail={setSelectedId}
          onUploadFiles={handleUploadFiles}
        />
      </div>
    </div>
  );
}
