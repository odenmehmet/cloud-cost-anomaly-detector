# Demo Notes

## Pre-Demo Commands

Run these from the repository root before opening the dashboard:

```bash
python run_pipeline.py
streamlit run app/streamlit_app.py
```

The dashboard reads existing CSV outputs only. It does not run the pipeline automatically.

## 5-7 Minute Demo Flow

1. Start on the homepage and explain the Level 1 scope: synthetic CUR-like data, anomaly detection, alerting, contributor analysis, and evaluation.
2. Open **Overview** and show the daily cost trend, true anomaly markers, warning alerts, and critical alerts.
3. Open **Anomaly Detail** and select `ALERT-0001` / `2025-11-20` if available. Explain it as a critical true anomaly caused by a one-day spike.
4. Still in **Anomaly Detail**, use the local context chart to compare actual cost against the STL expected cost around the alert date.
5. Point out the method rows and contributor table. Emphasize that contributor analysis identifies service/region cost contributors, not causal root-cause attribution.
6. Select `ALERT-0002` / `2025-12-02` if available. Explain it as a planned-event false positive that remains useful for evaluation.
7. Open **Evaluation** and compare precision, recall, F1, false positives per 30 days, recall by anomaly type, and detection delay.

## Key Talking Points

- The dataset is synthetic and CUR-like, so it is reproducible and safe to publish.
- Three simple detectors are compared: Rolling Z-score, STL decomposition, and Isolation Forest.
- The final alert layer uses method agreement plus relative cost deviation.
- Warning and critical alerts are generated without notification delivery.
- The alert detail page includes local cost context and top service/region cost increases.
- Contributor analysis is service/region based and non-causal.
- Evaluation is intentionally honest: harder cases such as gradual drift may have lower recall.
- Planned event false positives show why human interpretation matters.

## Recommended Demo Examples

| Scenario | Preferred Alert | Date | How to Explain |
|---|---|---|---|
| Critical true anomaly | `ALERT-0001` | `2025-11-20` | One-day spike detected by method agreement. |
| Planned event false positive | `ALERT-0002` | `2025-12-02` | Not a true anomaly; useful for false-positive analysis. |

## Backup Plan

If alert IDs change after future data updates:

- For the true anomaly example, use the first critical alert where `is_true_anomaly = 1`.
- For the planned-event example, use the first alert where `planned_event = 1`.
- If no planned event is alerted, use the first row in `reports/false_positive_days.csv` with `planned_event = 1`.
