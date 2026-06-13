# Project 13 Level 1 Demo Notes

## Start

From the repository root:

```powershell
.\run_web.bat
```

The command creates the local virtual environment, runs the pipeline and output
checks, exports dashboard JSON, and starts the React dashboard.

## 3-5 Minute Demo Flow

1. **Home: 30-45 seconds**
   - Confirm the date range and alert counts.
   - Explain that true anomaly days are injected labels while alerts are final policy
     outputs, so the counts are not expected to match.
   - State that synthetic data makes labels deterministic and evaluation reproducible.

2. **Cost Overview: 60 seconds**
   - Show daily cost, the 7-day moving average, and STL expected cost.
   - Explain that the three detectors provide complementary statistical evidence.
   - Toggle planned-event markers and show the separate suppression table.
   - Explain that final alerts require detector agreement and a meaningful upward
     deviation, then select an alert from the summary table.

3. **Alert Investigation: 60 seconds**
   - Use `ALERT-0001` if available.
   - Show ground-truth status, method agreement, local cost context, and contributor
     ranking.
   - Confirm that the top contributor dimension matches rank 1 in the table.
   - Emphasize that contributor ranking identifies where cost increased, not why.

4. **Planned-event suppression: 30 seconds**
   - Return to Cost Overview and open the suppressed planned-events section.
   - Show that the candidate retains detector evidence and deviation context.
   - Explain that cataloged legitimate growth is excluded from operational alerts.

5. **Method Evaluation: 60-90 seconds**
   - Switch between Exact day and Within one day.
   - Distinguish raw detectors, raw candidates, and operational alerts.
   - Compare day-level precision, recall, F1, and false positives per 30 days.
   - Compare day-level recall with event-level detection.
   - Open selected calibration settings and explain the bounded sweep.
   - State that agreement alerts trade maximum recall for higher-confidence operations.

## Key Talking Points

- **Why synthetic data?** Real billing data is unavailable and unlabeled. Synthetic
  data provides reproducible anomaly and planned-event ground truth.
- **Why multiple detectors?** Z-score captures baseline deviation, STL accounts for
  weekly structure, and Isolation Forest evaluates multivariate behavior.
- **Why agreement alerts?** Individual detectors are noisy. Agreement plus severity
  thresholds produces fewer, more trustworthy operational alerts.
- **Why can day-level recall be conservative?** Persistent and gradual events label
  multiple days, while detecting an event once may still be operationally useful.
- **Why is contributor ranking non-causal?** It compares cost changes by dimension but
  does not use deployment, activity-log, or causal evidence.

## Expected Questions

### Why are true anomaly days different from the alert count?

True anomaly days are every labeled day across injected event windows. Alerts are only
the dates that pass detector agreement and severity policy.

### Why is recall not perfect?

The detectors are intentionally simple, anomaly shapes vary, and thresholds balance
missed detections against false-positive noise. Metrics were not manually forced.

### Why are planned events not final alerts?

They may trigger raw detectors, but the planned-event catalog explains them. They are
retained as suppressions for auditability and excluded from operational alerts.

### Is this real AWS data?

No. It is deterministic AWS CUR-like synthetic data designed for a Level 1 course
project and reproducible evaluation.

### Is this root-cause attribution?

No. The project performs non-causal contributor ranking. It identifies which
service-region dimensions increased most, not the underlying cause.

### What is Level 1 versus Level 2?

Level 1 covers synthetic billing, daily aggregation, explainable detectors, alert
policy, contributor ranking, evaluation, and a local dashboard. Level 2 would require
live cloud ingestion, operational integrations, or richer activity correlation, which
are intentionally excluded.

## Backup Alert Selection

If alert IDs change:

- For the true-anomaly example, select the first critical alert with
  `is_true_anomaly = 1`.
- For the planned-event example, use the first row in
  `data/outputs/suppressed_alerts.csv`.

## Manual Fallback

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python run_pipeline.py
.\.venv\Scripts\python tests\smoke_check_outputs.py
.\.venv\Scripts\python scripts\export_web_data.py
cd web
npm install
npm run dev
```

## Pre-Demo Checks

1. Run `.\build_web.bat`.
2. Run `.\run_web.bat`.
3. Confirm all four routes load without console errors.
4. Confirm `ALERT-0001` exists or use the first critical true alert.
5. Confirm `PLAN-001` appears under suppressed planned events.
6. Keep a browser window at desktop width and avoid zooming during the demo.
