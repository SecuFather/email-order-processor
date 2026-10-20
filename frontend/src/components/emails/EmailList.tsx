import { useRef, type DragEvent } from "react";
import type { EmailSummary } from "../../types/email";

type EmailListProps = {
  emails: EmailSummary[];
  selectedId: number | null;
  isLoading: boolean;
  isUploading: boolean;
  onSelectEmail: (id: number) => void;
  onUploadFiles: (files: FileList) => void;
};

export function EmailList({
  emails,
  selectedId,
  isLoading,
  isUploading,
  onSelectEmail,
  onUploadFiles,
}: EmailListProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      onUploadFiles(e.dataTransfer.files);
    }
  }

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[780px]"
    >
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between gap-2 bg-slate-900/90">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Emails ({emails.length})
        </h2>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".eml"
            multiple
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                onUploadFiles(e.target.files);
                e.target.value = "";
              }
            }}
            className="hidden"
          />
          <button
            type="button"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white cursor-pointer transition-colors"
          >
            {isUploading ? "Adding..." : "+ Upload .eml"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/70">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-500">
            Loading emails...
          </div>
        ) : emails.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No emails stored yet. Drop .eml files here or click "+ Upload .eml".
          </div>
        ) : (
          emails.map((item) => {
            const isSelected = item.id === selectedId;
            return (
              <div
                key={item.id}
                onClick={() => onSelectEmail(item.id)}
                className={`p-3.5 cursor-pointer transition-colors space-y-1.5 ${
                  isSelected
                    ? "bg-indigo-950/40 border-l-4 border-l-indigo-500"
                    : "hover:bg-slate-800/40"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-slate-100 line-clamp-1">
                    {item.title || "(No subject)"}
                  </div>
                  {item.woocommerce_id && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60 shrink-0">
                      WC #{item.woocommerce_id}
                    </span>
                  )}
                </div>

                <div className="text-xs text-slate-400 truncate">
                  {item.sender}
                  {item.recipient ? ` → ${item.recipient}` : ""}
                </div>

                <div className="text-[11px] text-slate-500 truncate">
                  {item.date}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
