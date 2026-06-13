import type { ReactNode } from "react";
import type { DashboardManifest, PageId } from "../lib/types";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  page: PageId;
  manifest: DashboardManifest | null;
  missingFiles: string[];
  onNavigate: (page: PageId) => void;
  children: ReactNode;
}

const PAGE_TITLES: Record<PageId, string> = {
  home: "Home",
  overview: "Cost Overview",
  "anomaly-detail": "Alert Investigation",
  evaluation: "Method Evaluation",
};

export function Layout({
  page,
  manifest,
  missingFiles,
  onNavigate,
  children,
}: LayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar
        currentPage={page}
        onNavigate={onNavigate}
        dataReady={Boolean(manifest) && missingFiles.length === 0}
      />
      <main className="main-shell">
        <header className="topbar">
          <button className="mobile-brand" type="button" onClick={() => onNavigate("home")}>
            Cloud Cost Anomaly Detector
          </button>
          <div>
            <span>Workspace</span>
            <strong>{PAGE_TITLES[page]}</strong>
          </div>
          <div className="topbar__meta">
            <span>Report generated</span>
            <strong>{manifest?.generated_at?.slice(0, 10) ?? "Not available"}</strong>
          </div>
        </header>
        {missingFiles.length > 0 && manifest ? (
          <div className="missing-banner">
            Some dashboard data is unavailable: {missingFiles.join(", ")}. Empty sections are
            shown instead of errors.
          </div>
        ) : null}
        <div className="page-transition">{children}</div>
      </main>
    </div>
  );
}
