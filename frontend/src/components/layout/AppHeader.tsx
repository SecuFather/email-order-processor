type Tab = {
  id: string;
  label: string;
};

const TABS: Tab[] = [
  { id: "companies", label: "Companies" },
  { id: "clients", label: "Clients" },
  { id: "shipping", label: "Shipping" },
  { id: "emails", label: "Emails" },
  { id: "products", label: "Products" },
  { id: "variants", label: "Variants" },
  { id: "config", label: "Config" },
  { id: "ambiguity", label: "Ambiguity Rules" },
  { id: "log", label: "Log" },
];

const HEADER_CLASS = "flex items-center justify-between pb-4 border-b border-slate-800";
const BRAND_CONTAINER_CLASS = "flex items-center gap-6";
const TITLE_CLASS = "text-xl font-bold tracking-tight text-white flex items-center gap-2";
const NAV_CLASS = "flex items-center gap-2";

function getTabClass(isActive: boolean): string {
  return `px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
    isActive
      ? "bg-indigo-600 text-white shadow-sm"
      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
  }`;
}

type AppHeaderProps = {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  hasLogAlert?: boolean;
};

export function AppHeader({ activeTab, onSelectTab, hasLogAlert }: AppHeaderProps) {
  return (
    <header className={HEADER_CLASS}>
      <div className={BRAND_CONTAINER_CLASS}>
        <h1 className={TITLE_CLASS}>
          <span>🏢</span> Order Manager
        </h1>

        <nav className={NAV_CLASS}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => onSelectTab(tab.id)}
              className={getTabClass(activeTab === tab.id)}
            >
              <span className="flex items-center gap-1.5">
                <span>{tab.label}</span>
                {tab.id === "log" && hasLogAlert && (
                  <span
                    data-testid="log-alert-spot"
                    className="w-2 h-2 rounded-full bg-red-500 shadow-sm shadow-red-500/80"
                  />
                )}
              </span>
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
