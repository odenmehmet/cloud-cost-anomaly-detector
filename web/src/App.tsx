import { lazy, Suspense, useEffect, useState } from "react";
import { EmptyState } from "./components/EmptyState";
import { Layout } from "./components/Layout";
import { loadDashboardData } from "./lib/data";
import type { DataLoadResult, PageId } from "./lib/types";

const Home = lazy(() => import("./pages/Home").then((module) => ({ default: module.Home })));
const Data = lazy(() => import("./pages/Data").then((module) => ({ default: module.Data })));
const Overview = lazy(() =>
  import("./pages/Overview").then((module) => ({ default: module.Overview })),
);
const AnomalyDetail = lazy(() =>
  import("./pages/AnomalyDetail").then((module) => ({ default: module.AnomalyDetail })),
);
const Evaluation = lazy(() =>
  import("./pages/Evaluation").then((module) => ({ default: module.Evaluation })),
);

const PAGE_PATHS: Record<PageId, string> = {
  home: "/",
  data: "/data",
  overview: "/overview",
  "anomaly-detail": "/anomaly-detail",
  evaluation: "/evaluation",
};

function parseRoute(): { page: PageId; alertId?: string } {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  const page =
    (Object.entries(PAGE_PATHS).find(([, value]) => value === path)?.[0] as PageId | undefined) ??
    "home";
  const alertId = new URLSearchParams(query).get("alert") ?? undefined;
  return { page, alertId };
}

export default function App() {
  const [route, setRoute] = useState(parseRoute);
  const [result, setResult] = useState<DataLoadResult | null>(null);

  useEffect(() => {
    const onHashChange = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    void loadDashboardData().then(setResult);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [route.alertId, route.page]);

  const navigate = (page: PageId) => {
    window.location.hash = PAGE_PATHS[page];
  };

  const selectAlert = (alertId: string) => {
    window.location.hash = `${PAGE_PATHS["anomaly-detail"]}?alert=${encodeURIComponent(alertId)}`;
  };

  if (!result) {
    return (
      <div className="loading-screen">
        <div className="loading-mark" />
        <strong>Loading dashboard data</strong>
        <span>Reading exported pipeline outputs...</span>
      </div>
    );
  }

  const { data, missingFiles } = result;
  const manifest = data.manifest;
  const coreDataMissing = !manifest || data.dailyFeatures.length === 0;

  return (
    <Layout
      page={route.page}
      manifest={manifest}
      missingFiles={missingFiles}
      onNavigate={navigate}
    >
      <Suspense
        fallback={
          <div className="page">
            <div className="loading-inline">Loading view...</div>
          </div>
        }
      >
        {coreDataMissing ? (
          <div className="page">
            <EmptyState />
          </div>
        ) : route.page === "home" ? (
          <Home manifest={manifest!} onNavigate={navigate} />
        ) : route.page === "data" ? (
          <Data sample={data.syntheticSample} />
        ) : route.page === "overview" ? (
          <Overview
            daily={data.dailyFeatures}
            alerts={data.alerts}
            methods={data.methodResults}
            stl={data.stlComponents}
            suppressed={data.suppressedAlerts}
            onSelectAlert={selectAlert}
          />
        ) : route.page === "anomaly-detail" ? (
          <AnomalyDetail
            alerts={data.alerts}
            daily={data.dailyFeatures}
            methods={data.methodResults}
            contributors={data.contributors}
            stl={data.stlComponents}
            initialAlertId={route.alertId}
            onAlertChange={selectAlert}
          />
        ) : (
          <Evaluation
            summary={data.evaluationSummary}
            eventLevel={data.eventLevelEvaluation}
            calibration={data.calibrationSummary}
            byType={data.evaluationByType}
            delays={data.detectionDelay}
            falsePositives={data.falsePositiveDays}
            scenarioRobustness={data.scenarioRobustness}
          />
        )}
      </Suspense>
    </Layout>
  );
}
