import type {
  Alert,
  CalibrationSummary,
  Contributor,
  DailyFeature,
  DashboardManifest,
  DataLoadResult,
  DetectionDelay,
  EvaluationByType,
  EventLevelEvaluation,
  EvaluationSummary,
  FalsePositiveDay,
  MethodResult,
  ScenarioRobustness,
  StlComponent,
  SuppressedAlert,
} from "./types";

const GENERATED_ROOT = "/generated";

async function fetchGenerated<T>(filename: string, fallback: T): Promise<[T, string | null]> {
  try {
    const response = await fetch(`${GENERATED_ROOT}/${filename}`, { cache: "no-store" });
    if (!response.ok) {
      return [fallback, filename];
    }
    return [(await response.json()) as T, null];
  } catch {
    return [fallback, filename];
  }
}

export async function loadDashboardData(): Promise<DataLoadResult> {
  const [
    manifest,
    dailyFeatures,
    methodResults,
    alerts,
    suppressedAlerts,
    contributors,
    stlComponents,
    calibrationSummary,
    evaluationSummary,
    eventLevelEvaluation,
    evaluationByType,
    detectionDelay,
    falsePositiveDays,
    scenarioRobustness,
  ] = await Promise.all([
    fetchGenerated<DashboardManifest | null>("dashboard_manifest.json", null),
    fetchGenerated<DailyFeature[]>("daily_features.json", []),
    fetchGenerated<MethodResult[]>("method_results.json", []),
    fetchGenerated<Alert[]>("alerts.json", []),
    fetchGenerated<SuppressedAlert[]>("suppressed_alerts.json", []),
    fetchGenerated<Contributor[]>("contributors.json", []),
    fetchGenerated<StlComponent[]>("stl_components.json", []),
    fetchGenerated<CalibrationSummary[]>("calibration_summary.json", []),
    fetchGenerated<EvaluationSummary[]>("evaluation_summary.json", []),
    fetchGenerated<EventLevelEvaluation[]>("event_level_evaluation.json", []),
    fetchGenerated<EvaluationByType[]>("evaluation_by_type.json", []),
    fetchGenerated<DetectionDelay[]>("detection_delay.json", []),
    fetchGenerated<FalsePositiveDay[]>("false_positive_days.json", []),
    fetchGenerated<ScenarioRobustness[]>("scenario_robustness.json", []),
  ]);

  const results = [
    manifest,
    dailyFeatures,
    methodResults,
    alerts,
    suppressedAlerts,
    contributors,
    stlComponents,
    calibrationSummary,
    evaluationSummary,
    eventLevelEvaluation,
    evaluationByType,
    detectionDelay,
    falsePositiveDays,
    scenarioRobustness,
  ] as const;

  return {
    data: {
      manifest: results[0][0],
      dailyFeatures: results[1][0],
      methodResults: results[2][0],
      alerts: results[3][0],
      suppressedAlerts: results[4][0],
      contributors: results[5][0],
      stlComponents: results[6][0],
      calibrationSummary: results[7][0],
      evaluationSummary: results[8][0],
      eventLevelEvaluation: results[9][0],
      evaluationByType: results[10][0],
      detectionDelay: results[11][0],
      falsePositiveDays: results[12][0],
      scenarioRobustness: results[13][0],
    },
    missingFiles: results
      .map(([, missing]) => missing)
      .filter((filename): filename is string => Boolean(filename)),
  };
}
