import { useState } from "react";
import { AppHeader } from "./components/layout/AppHeader";
import { CompaniesTab } from "./components/companies/CompaniesTab";
import { ClientsTab } from "./components/clients/ClientsTab";
import { ShippingTab } from "./components/shipping/ShippingTab";
import { EmailsTab } from "./components/emails/EmailsTab";
import { ProductsTab } from "./components/products/ProductsTab";
import { VariantsTab } from "./components/variants/VariantsTab";
import { ConfigTab } from "./components/config/ConfigTab";
import { AmbiguityTab } from "./components/ambiguity/AmbiguityTab";
import { LogsTab } from "./components/logs/LogsTab";
import type { LogEntry } from "./types/log";
import type { ProductActiveFilter } from "./types/product";

const ROOT_CONTAINER_CLASS = "min-h-screen w-full bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 space-y-6";

export default function App() {
  const [activeTab, setActiveTab] = useState("companies");
  const [globalNip, setGlobalNip] = useState<string | null>(null);
  const [globalShippingId, setGlobalShippingId] = useState<number | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [hasLogAlert, setHasLogAlert] = useState(false);
  const [productActiveFilter, setProductActiveFilter] =
    useState<ProductActiveFilter>("active");

  function handleToggleGlobalNip(nip: string) {
    setGlobalNip((prev) => (prev === nip ? null : nip));
  }

  function handleToggleGlobalShippingId(id: number) {
    setGlobalShippingId((prev) => (prev === id ? null : id));
  }

  function handleSelectTab(tab: string) {
    setActiveTab(tab);
    if (tab === "log") {
      setHasLogAlert(false);
    }
  }

  function handleAddLog(entry: Omit<LogEntry, "id" | "timestamp">) {
    const newEntry: LogEntry = {
      ...entry,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    setLogs((prev) => [newEntry, ...prev]);
    if (entry.level === "error") {
      setHasLogAlert(true);
    }
  }

  return (
    <div className={ROOT_CONTAINER_CLASS}>
      <AppHeader
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        hasLogAlert={hasLogAlert}
      />

      <main className="w-full">
        {activeTab === "companies" && (
          <CompaniesTab
            globalNip={globalNip}
            onSelectGlobalNip={handleToggleGlobalNip}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "clients" && (
          <ClientsTab
            globalNip={globalNip}
            onSelectGlobalNip={handleToggleGlobalNip}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "shipping" && (
          <ShippingTab
            globalNip={globalNip}
            globalShippingId={globalShippingId}
            onSelectGlobalShippingId={handleToggleGlobalShippingId}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "emails" && (
          <EmailsTab
            globalNip={globalNip}
            globalShippingId={globalShippingId}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "products" && (
          <ProductsTab
            activeFilter={productActiveFilter}
            onFilterChange={setProductActiveFilter}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "variants" && (
          <VariantsTab
            activeFilter={productActiveFilter}
            onAddLog={handleAddLog}
          />
        )}
        {activeTab === "config" && (
          <ConfigTab onAddLog={handleAddLog} />
        )}
        {activeTab === "ambiguity" && (
          <AmbiguityTab onAddLog={handleAddLog} />
        )}
        {activeTab === "log" && (
          <LogsTab
            logs={logs}
            onClearLogs={() => setLogs([])}
          />
        )}
      </main>
    </div>
  );
}
