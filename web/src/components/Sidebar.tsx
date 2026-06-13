import {
  Activity,
  BarChart3,
  Database,
  Gauge,
  Home,
} from "lucide-react";
import type { PageId } from "../lib/types";

interface SidebarProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  dataReady: boolean;
}

const NAV_ITEMS: Array<{
  page: PageId;
  label: string;
  description: string;
  icon: typeof Home;
}> = [
  { page: "home", label: "Home", description: "Workspace summary", icon: Home },
  { page: "overview", label: "Cost Overview", description: "Trends and alerts", icon: Gauge },
  {
    page: "anomaly-detail",
    label: "Alert Investigation",
    description: "Incident evidence",
    icon: Activity,
  },
  {
    page: "evaluation",
    label: "Method Evaluation",
    description: "Performance results",
    icon: BarChart3,
  },
];

export function Sidebar({ currentPage, onNavigate, dataReady }: SidebarProps) {
  return (
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => onNavigate("home")}>
        <span>
          <strong>Cloud Cost</strong>
          <small>Anomaly Detector</small>
        </span>
      </button>

      <nav className="sidebar__nav" aria-label="Primary navigation">
        <span className="sidebar__label">Workspace</span>
        {NAV_ITEMS.map(({ page, label, description, icon: Icon }) => (
          <button
            type="button"
            key={page}
            className={currentPage === page ? "nav-item nav-item--active" : "nav-item"}
            onClick={() => onNavigate(page)}
            aria-current={currentPage === page ? "page" : undefined}
          >
            <Icon aria-hidden="true" />
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </button>
        ))}
      </nav>

      <div className={`data-status ${dataReady ? "data-status--ready" : ""}`}>
        <Database aria-hidden="true" />
        <span>
          <strong>{dataReady ? "Data loaded" : "Data export needed"}</strong>
          <small>{dataReady ? "Exported pipeline outputs" : "Run the Windows launcher"}</small>
        </span>
      </div>
    </aside>
  );
}
