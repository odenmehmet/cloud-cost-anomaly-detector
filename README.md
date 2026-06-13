# Project 13 Level 1: Automated Cloud Cost Anomaly Detection

This Cloud Computing Level 1 project generates synthetic AWS CUR-like billing data,
calibrates three explainable anomaly detectors, creates agreement-based operational
alerts, suppresses cataloged planned events, ranks service and region contributors,
and evaluates results against injected labels.

The official user interface is the React, Vite, and TypeScript dashboard in `web/`.
Contributor ranking is descriptive and non-causal.

## Implemented

- Deterministic synthetic CUR-like billing data with account, service, region, cost,
  usage, environment, team, anomaly, and planned-event fields
- Rolling Z-score, STL Decomposition, and Isolation Forest detectors
- Small detector threshold and sensitivity calibration sweep
- Agreement and cost-deviation alert policy
- Planned-event explanation and operational suppression
- Positive cost-increase contributor ranking with an explicit fallback mode
- Exact-day, within-one-day, event-level, delay, and false-positive evaluation
- React/Vite dashboard backed by exported pipeline outputs

## Scope Exclusions

- Real AWS billing ingestion
- Live alert notifications or production monitoring
- Causal root-cause attribution
- Multi-cloud normalization
- Kubernetes or cloud activity-log correlation
- Advanced forecasting, deep learning, or Level 2 integrations

## Setup and Quick Start

Prerequisites:

- Windows PowerShell
- Python 3.11 or newer
- Node.js 18 or newer with npm

From the repository root:

```powershell
.\run_web.bat
```

The runner:

1. Creates `.venv/` when needed.
2. Installs or updates Python requirements inside `.venv/`.
3. Runs the Python pipeline.
4. validates generated outputs.
5. Exports the existing CSV outputs to static JSON.
6. Installs web dependencies when `web/node_modules/` is missing.
7. Starts Vite on `http://127.0.0.1:5173`, or the next available port.

Generated CSV and dashboard JSON files are intentionally not committed. A clean
checkout becomes runnable through `run_web.bat`, which regenerates and validates all
required data before starting the dashboard.

If local PowerShell policy blocks a batch invocation, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_web.ps1
```

## Production Build

```powershell
.\build_web.bat
```

The build runner performs the same Python pipeline, smoke check, and JSON export
before running `npm run build`.

## Pipeline and Test Commands

Run only the Python pipeline:

```powershell
.\.venv\Scripts\python run_pipeline.py
```

Run the output integrity and policy checks:

```powershell
.\.venv\Scripts\python tests\smoke_check_outputs.py
```

Export dashboard JSON after running the pipeline:

```powershell
.\.venv\Scripts\python scripts\export_web_data.py
```

## Manual Setup

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

Manual production build:

```powershell
cd web
npm run build
```

## Dashboard

The dashboard reads JSON exported from existing pipeline CSV outputs. It does not
recalculate detector results, alert rules, contributor values, or evaluation metrics.

- **Home**: dataset and alert KPIs, pipeline overview, primary views, and scope.
- **Cost Overview**: daily cost, 7-day moving average, STL expected cost, anomaly
  labels, planned events, operational alerts, suppressions, and detector flag counts.
- **Anomaly Detail**: alert status, local cost context, method evidence, and ranked
  service/region contributors.
- **Evaluation**: day-level and event-level metrics, selected calibration settings,
  anomaly-type recall, detection delay, and false-positive detail.

## Pipeline

```text
Synthetic CUR-like records
        |
Preprocessing and daily aggregation
        |
Feature engineering
        |
Bounded detector sensitivity calibration
        |
Rolling Z-score + STL Decomposition + Isolation Forest
        |
Agreement and upward-deviation alert policy
        |
Planned-event suppression
        |
Service and region contributor ranking
        |
Evaluation against injected anomaly labels
        |
Static JSON export
        |
React web dashboard
```

## Detection Methods

- **Rolling Z-score** compares daily cost with a rolling baseline.
- **STL Decomposition** separates trend, weekly seasonality, and residual behavior.
- **Isolation Forest** identifies unusual multivariate daily feature patterns.
- **Agreement Alert** requires detector evidence and a meaningful upward cost
  deviation. A cataloged planned event is exported as a suppression, not an
  operational warning or critical alert.

Calibration uses a small documented candidate grid. The selection score weights
day-level F1 at 75% and event recall at 25%; selected parameters and every candidate
remain visible in `reports/calibration_summary.csv`. The frontend does not recompute
thresholds or metrics.

## Contributor Analysis

For each alert, the pipeline compares service/region cost with its previous 7-day
average and ranks only positive increases. If no positive deltas exist, it explicitly
falls back to current-cost ranking and labels the basis accordingly. This answers
where cost changed most; it does not prove why and is not causal attribution.

## Evaluation

Evaluation uses injected synthetic anomaly labels and reports:

- Precision
- Recall
- F1 score
- False positives per 30 days
- Recall by anomaly type
- Detection delay
- Exact-day and one-day-tolerance matching
- Event precision, recall, and F1 over contiguous prediction runs
- Raw agreement candidates versus final operational alerts
- Planned-event suppressions as a distinct prediction source

Low values remain visible. Gradual anomaly windows are intentionally difficult for
the simple detectors used in this course scope.

### Metric Definitions

- **Exact-day matching**: a predicted day is correct only when it is the same date as
  an injected anomaly day.
- **Within-one-day matching**: a prediction may match one injected day within one day
  before or after it. One prediction cannot credit multiple true days.
- **Event-level detection**: an anomaly event is detected when at least one prediction
  run overlaps its cataloged event window, with an optional one-day tolerance.
- **Raw detector metrics**: evaluate Rolling Z-score, STL, and Isolation Forest flags
  before the agreement policy.
- **Raw alert candidate metrics**: evaluate agreement and severity candidates before
  planned-event suppression.
- **Operational alert metrics**: evaluate final user-facing alerts after
  planned-event suppression.

Day-level recall is conservative for persistent and gradual events because every
labeled day must be matched. Event-level recall answers the different question of
whether the system detected each anomaly event at least once.

## Generated Outputs

Main generated files include:

```text
data/raw/synthetic_cur_like_daily.csv
data/raw/anomaly_catalog.csv
data/raw/planned_event_catalog.csv
data/processed/daily_features.csv
data/outputs/method_results.csv
data/outputs/alerts.csv
data/outputs/suppressed_alerts.csv
data/outputs/contributors.csv
reports/calibration_summary.csv
reports/evaluation_summary.csv
reports/event_level_evaluation.csv
reports/evaluation_by_type.csv
reports/detection_delay.csv
reports/false_positive_days.csv
web/public/generated/*.json
```

Generated CSV and JSON files are ignored by Git. The dashboard launcher creates them
before Vite starts; `web/public/generated/.gitkeep` retains the required directory.

## Repository Structure

```text
.
|-- run_web.bat
|-- build_web.bat
|-- run_pipeline.py
|-- requirements.txt
|-- scripts/
|   |-- run_web.ps1
|   |-- build_web.ps1
|   `-- export_web_data.py
|-- src/
|   |-- data_generator.py
|   |-- preprocessing.py
|   |-- features.py
|   |-- calibration.py
|   |-- alerts.py
|   |-- contributors.py
|   |-- evaluation.py
|   `-- detectors/
|-- tests/
|   `-- smoke_check_outputs.py
|-- reports/
|   `-- demo_notes.md
`-- web/
    |-- package.json
    |-- public/generated/
    `-- src/
```

## Python Environment

The supported workflow uses the local `.venv/` rather than Anaconda base. The
requirements include compatible `numexpr` and `bottleneck` versions, which removes
the pandas acceleration warnings seen in older base environments.

## License

See [LICENSE](LICENSE).
