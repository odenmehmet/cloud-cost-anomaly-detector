# Automated Cloud Cost Anomaly Detection and Root-Cause Attribution

> A Level 1 Cloud Computing course project for detecting cloud cost anomalies in CUR-like billing data using Rolling Z-score, STL decomposition, Isolation Forest, and explainable warning/critical alerts.

---

## Overview

Cloud billing data is noisy and difficult to interpret. Daily cost may change because of normal weekly usage patterns, traffic changes, deployment cycles, or legitimate business growth. However, unexpected cost increases can also indicate abnormal usage, inefficient resource behavior, or configuration-related cost problems.

This project builds a lightweight and reproducible academic prototype that:

1. Generates or reads CUR-like cloud billing data.
2. Detects anomalous cost behavior using three complementary methods.
3. Converts detections into warning and critical alerts.
4. Explains alerts using service and region contributor analysis.
5. Visualizes the complete workflow through a Streamlit dashboard.
6. Evaluates detection performance using injected anomaly labels.

The project is intentionally scoped for a Level 1 Cloud Computing course demo. It is not intended to be a production FinOps platform.

---

## Course Context

| Field | Value |
|---|---|
| Course | Cloud Computing |
| Semester | 2025–2026 Spring |
| Project | Project 13 |
| Level | Level 1 / Standard |
| Official Project Title | Automated Cloud Cost Anomaly Detection and Root-Cause Attribution |
| Practical Implementation Scope | Cloud Cost Anomaly Detection and Contributor Analysis |
| Team Members | Mehmet Öden, Emre Keser |
| Repository | `cloud-cost-anomaly-detector` |

---

## Problem Definition

Cloud cost anomalies are difficult to detect from raw billing data because normal variation, seasonality, and legitimate usage increases can look similar to unexpected cost spikes.

This project addresses that problem by comparing multiple anomaly detection methods on controlled CUR-like billing data and presenting the results through an explainable dashboard.

---

## Final Project Scope

This repository follows a focused Level 1 scope.

### In Scope

- Synthetic CUR-like labeled billing data
- Daily cloud cost aggregation
- Rolling Z-score anomaly detection
- STL decomposition based anomaly detection
- Isolation Forest based anomaly detection
- Warning and critical alert generation
- Method agreement based alerting
- Service and region contributor analysis
- Streamlit dashboard
- Evaluation using injected anomaly labels
- Precision, recall, F1-score, false positives, and detection delay

### Out of Scope

The following features are deliberately excluded to keep the project realistic and aligned with Level 1 expectations:

- Multi-cloud billing normalization
- Full FOCUS implementation
- Production deployment
- Real AWS S3 / Athena / CUR ingestion pipeline
- Airflow, dbt, QuickSight, or data warehouse integration
- Causal root-cause attribution
- Kubernetes event correlation
- Deployment log correlation
- Auto-remediation
- Slack, email, or SMS notification system
- Authentication or multi-tenant dashboard
- Prophet, LSTM, Autoencoder, or advanced deep learning models

---

## Important Scope Note

Although the official project title includes the phrase **Root-Cause Attribution**, this Level 1 implementation does **not** claim causal root-cause analysis.

Instead, the project provides lightweight **contributor analysis**:

> Given a detected cost anomaly, the dashboard shows which service and region contributed most to the cost increase.

This helps interpret the alert, but it does not prove causality.

---

## Dataset Decision

The main dataset will be a **synthetic CUR-like labeled billing dataset**.

Publicly available, real, labeled AWS CUR anomaly datasets are difficult to use for academic evaluation because real cloud billing data is often private, anonymized, incomplete, or unlabeled. Therefore, this project uses controlled synthetic data with known injected anomalies.

This makes the system:

- Reproducible
- Safe to publish on GitHub
- Suitable for precision/recall/F1 evaluation
- Easy to explain in a course demo

Public AWS CUR / CUR 2.0 / Data Exports documentation and public billing schema examples may be used only for schema realism. They are not the main evaluation dataset.

---

## Planned Main Data Schema

The synthetic dataset will imitate a simplified daily CUR-like billing structure.

```text
usage_date
service
region
usage_amount
usage_unit
cost_usd
operation
usage_type
tag_environment
tag_team
line_item_type
source_record_count
is_anomaly
anomaly_type
anomaly_id
planned_event
```

### Field Meaning

| Field | Description |
|---|---|
| `usage_date` | Daily billing date |
| `service` | Cloud service name, e.g., EC2, S3, Lambda |
| `region` | Cloud region |
| `usage_amount` | Simulated usage amount |
| `usage_unit` | Unit of usage |
| `cost_usd` | Daily cost in USD |
| `operation` | Simulated operation type |
| `usage_type` | Simulated usage type |
| `tag_environment` | Environment tag such as prod, staging, dev |
| `tag_team` | Team tag such as platform, data, web, ml |
| `line_item_type` | Simplified billing line item type |
| `source_record_count` | Number of source records represented after aggregation |
| `is_anomaly` | Ground-truth anomaly label |
| `anomaly_type` | Type of injected anomaly |
| `anomaly_id` | ID linking to the anomaly catalog |
| `planned_event` | Indicates legitimate planned usage increase |

---

## Planned Anomaly Catalog Schema

A separate anomaly catalog will document injected anomaly events.

```text
anomaly_id
anomaly_type
start_date
end_date
affected_service
affected_region
magnitude
planned_event
description
```

This catalog allows the evaluation module and dashboard to explain each injected anomaly clearly.

---

## Planned Anomaly Types

The synthetic dataset will include both true anomalies and normal-but-challenging cost patterns.

| Type | Label | Purpose |
|---|---|---|
| One-day spike | Anomaly | Tests sudden single-day cost increases |
| Persistent step increase | Anomaly | Tests sustained cost level changes |
| Gradual drift | Anomaly | Tests slow cost increases over time |
| Service-local anomaly | Anomaly | Tests service/region-specific cost changes |
| Seasonal normal variation | Normal | Tests weekly seasonality handling |
| Legitimate usage increase | Normal / Planned event | Tests false positives under valid growth |

---

## Detection Methods

The project compares three complementary anomaly detection methods.

---

### 1. Rolling Z-score

Rolling Z-score is used as a simple statistical baseline.

It compares daily cost against a rolling mean and rolling standard deviation.

Expected strengths:

- Easy to implement
- Easy to explain
- Strong for sudden one-day spikes
- Useful as a baseline

Expected weaknesses:

- Sensitive to seasonality
- Can over-flag legitimate usage increases
- Weak for gradual drift
- Assumes relatively stable historical behavior

---

### 2. STL Decomposition

STL decomposition separates a time series into trend, seasonal, and residual components.

The system will detect anomalies by identifying unusually large residuals.

Expected strengths:

- Handles weekly seasonality better than basic Z-score
- Provides interpretable actual vs expected cost
- Works well for dashboard explanation
- Useful for explaining why a day was unusual

Expected weaknesses:

- Requires enough historical data
- Parameter choice matters
- May adapt to persistent level changes over time

---

### 3. Isolation Forest

Isolation Forest is used as a lightweight machine learning based outlier detector.

Unlike the previous two methods, it can use multiple daily features.

Planned features include:

```text
total_cost
pct_change_1d
pct_change_7d
day_of_week
top_service_share
top_region_share
service_count
```

Expected strengths:

- Can use multiple features
- Can detect non-linear anomaly patterns
- Useful for service/region distribution changes

Expected weaknesses:

- Less transparent than Z-score and STL
- Requires careful feature design
- Requires contamination/threshold tuning

---

## Alert Policy

The project separates anomaly detection from alerting.

Each method can independently flag a day as suspicious. The alert layer then combines the method outputs into a final alert decision.

### Planned Alert Rules

| Alert Level | Rule |
|---|---|
| No Alert | No method flags the day |
| Warning | One method flags the day and deviation is meaningful |
| Critical | Two or more methods flag the day and deviation is large |
| Critical Override | All three methods flag the same day |

### Initial Threshold Plan

```text
Warning:
- At least 1 method flagged
- Relative deviation >= 15%

Critical:
- At least 2 methods flagged
- Relative deviation >= 25%

Critical Override:
- 3 methods flagged
```

Thresholds may be tuned during evaluation using the synthetic validation data.

---

## Contributor Analysis

For each alert, the system will compute lightweight service and region contribution summaries.

Example questions answered by contributor analysis:

- Which service contributed most to the cost increase?
- Which region contributed most to the cost increase?
- How much higher was the selected service cost compared to its previous 7-day average?

Planned contributor output fields:

```text
usage_date
service
region
cost_usd
previous_7d_avg_cost
delta_cost
contribution_share
rank
```

This analysis is used only for explainability. It is not causal root-cause attribution.

---

## Planned Pipeline

```text
1. Generate synthetic CUR-like billing data
2. Preprocess daily cost data
3. Build daily features
4. Run Rolling Z-score
5. Run STL decomposition
6. Run Isolation Forest
7. Merge method outputs
8. Generate warning/critical alerts
9. Produce service/region contributor analysis
10. Evaluate detection performance
11. Render Streamlit dashboard
```

---

## System Architecture

```text
Data Source
    ↓
Preprocessing
    ↓
Feature Engineering
    ↓
Detection Methods
    ├── Rolling Z-score
    ├── STL Decomposition
    └── Isolation Forest
    ↓
Alert Layer
    ↓
Contributor Analysis
    ↓
Evaluation
    ↓
Streamlit Dashboard
```

---

## Dashboard Plan

The dashboard will be implemented with Streamlit as a simple multipage app.

### Page 1 — Overview

Purpose:

- Show daily total cost trend
- Show anomaly markers
- Show warning and critical alert counts
- Provide a quick alert table

Planned components:

- Total cost line chart
- Warning and critical markers
- KPI cards
- Alert summary table
- Date range filter

---

### Page 2 — Anomaly Detail

Purpose:

- Explain why a selected day was flagged

Planned components:

- Selected alert date
- Actual cost vs expected cost
- Method-level flags and scores
- Alert reason
- Top service contributors
- Top region contributors
- Injected anomaly description, if available

---

### Page 3 — Evaluation

Purpose:

- Compare detection methods quantitatively

Planned components:

- Precision, recall, and F1-score table
- False positives per 30 days
- Detection delay
- Evaluation by anomaly type
- Short interpretation of method strengths and weaknesses

---

## Evaluation Plan

Because the synthetic dataset contains known injected anomaly labels, the project can evaluate detection performance directly.

### Main Metrics

| Metric | Meaning |
|---|---|
| Precision | How many detected anomalies were correct |
| Recall | How many true anomalies were detected |
| F1-score | Balance between precision and recall |
| False positives per 30 days | Alert noise level |
| Detection delay | How quickly range anomalies are detected |

### Matching Strategy

Two evaluation modes are planned:

| Mode | Description |
|---|---|
| Exact-day matching | Prediction must match the true anomaly day exactly |
| ±1 day tolerance | Prediction is accepted if it is within one day of the true anomaly |

---

## Repository Structure

```text
cloud-cost-anomaly-detector/
│
├── app/
│   ├── streamlit_app.py
│   └── pages/
│       ├── 1_Overview.py
│       ├── 2_Anomaly_Detail.py
│       └── 3_Evaluation.py
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_generator.py
│   ├── preprocessing.py
│   ├── features.py
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── zscore.py
│   │   ├── stl.py
│   │   └── isolation_forest.py
│   ├── alerts.py
│   ├── contributors.py
│   └── evaluation.py
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   └── outputs/
│
├── reports/
│   └── demo_notes.md
│
├── tests/
│
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── run_pipeline.py
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/odenmehmet/cloud-cost-anomaly-detector.git
cd cloud-cost-anomaly-detector
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

Run the pipeline first to generate the CSV outputs, then start the Streamlit dashboard.

### Run the pipeline

```bash
python run_pipeline.py
```

Current behavior:

- Generate synthetic CUR-like billing data
- Preprocess daily cost data
- Run all detection methods
- Generate alerts
- Generate contributor analysis
- Evaluate results
- Save dashboard-ready outputs

### Run the dashboard

```bash
streamlit run app/streamlit_app.py
```

Current behavior:

- Open the Streamlit dashboard
- Show cost trends
- Display warning and critical alerts
- Show anomaly details
- Display evaluation results
- Provide a polished Level 1 demo flow without running the pipeline automatically

---

## Generated Outputs

The following files are generated by the pipeline.

```text
data/raw/synthetic_cur_like_daily.csv
data/raw/anomaly_catalog.csv
data/processed/daily_total_cost.csv
data/processed/daily_service_cost.csv
data/processed/daily_region_cost.csv
data/processed/daily_service_region_cost.csv
data/processed/daily_features.csv
data/outputs/zscore_results.csv
data/outputs/stl_results.csv
data/outputs/stl_components.csv
data/outputs/isolation_forest_results.csv
data/outputs/method_results.csv
data/outputs/alert_method_summary.csv
data/outputs/alerts.csv
data/outputs/contributors.csv
reports/evaluation_summary.csv
reports/evaluation_by_type.csv
reports/detection_delay.csv
reports/false_positive_days.csv
reports/evaluation_daily_predictions.csv
```

These files should not be committed by default unless explicitly needed for final course submission.

---

## Data Policy

No real cloud billing data should be committed to this repository.

Real AWS CUR files may contain sensitive information such as account structure, service usage, tags, environments, teams, and cost details. This project uses synthetic data for reproducibility, privacy, and controlled evaluation.

Generated CSV files are ignored by default through `.gitignore`.

---

## Current Phase Status

Phase 9 UI polish and demo readiness is complete in this working tree.

| Phase | Status |
|---|---|
| Phase 0 — Research & Project Lock | Completed |
| Phase 1 — Repository Structure | Completed |
| Phase 2 — Synthetic Data Generator | Completed |
| Phase 3 — Preprocessing & Features | Completed |
| Phase 4 — Detection Methods | Completed |
| Phase 5 — Alerts & Contributors | Completed |
| Phase 6 — Evaluation | Completed |
| Phase 7 — Streamlit Dashboard | Completed |
| Phase 8 — Integration & QA | Completed |
| Phase 9 — Demo Polish | Completed |

---

## Development Roadmap

### Phase 1 — Repository Structure

- Create project folders
- Add placeholder files
- Add README, requirements, license, and gitignore
- Define project boundaries

### Phase 2 — Synthetic Data Generator

- Generate reproducible CUR-like daily billing data
- Inject controlled anomalies
- Create anomaly catalog

### Phase 3 — Preprocessing and Feature Engineering

- Aggregate daily costs
- Build features for detection methods
- Prepare method input files

### Phase 4 — Detection Methods

- Implement Rolling Z-score
- Implement STL decomposition
- Implement Isolation Forest

### Phase 5 — Alerts and Contributor Analysis

- Merge method outputs
- Generate warning/critical alerts
- Compute top service and region contributors

### Phase 6 — Evaluation

- Calculate precision, recall, and F1-score
- Calculate false positives per 30 days
- Calculate detection delay
- Compare methods by anomaly type

### Phase 7 — Streamlit Dashboard

- Build Overview page
- Build Anomaly Detail page
- Build Evaluation page

### Phase 8 — Integration and QA

- Connect pipeline outputs to dashboard
- Validate generated files
- Test demo scenarios
- Clean repository

### Phase 9 — Demo Polish

- Finalize README
- Prepare demo script
- Capture screenshots if needed
- Rehearse final presentation flow

---

## Known Limitations

- The main dataset is synthetic, so it may not capture every pattern found in real production billing systems.
- The project focuses on daily granularity, not hourly billing streams.
- Contributor analysis is not causal root-cause attribution.
- Detection thresholds may need tuning depending on generated data characteristics.
- The dashboard is designed for a course demo, not production monitoring.

---

## Future Work

Possible extensions after the Level 1 demo:

- Support real AWS CUR 2.0 exports as optional input
- Add configurable anomaly generation scenarios
- Add more robust threshold tuning
- Add FOCUS-style schema mapping
- Add EWMA or MAD as lightweight additional baselines
- Add richer service-level drill-downs
- Add exportable evaluation reports

Advanced extensions such as multi-cloud normalization, causal root-cause attribution, deployment event correlation, or deep learning based anomaly detection are intentionally left out of this Level 1 implementation.

---

## Team

| Member | Primary Responsibility |
|---|---|
| Mehmet Öden | Dataset design, preprocessing, detection pipeline, evaluation |
| Emre Keser | Dashboard, alert visualization, integration testing, demo preparation |

---

## License

This project is licensed under the MIT License.

---

## Academic Note

This repository is developed as part of a Cloud Computing course project. The implementation is designed for educational demonstration, method comparison, and explainable anomaly detection rather than production cloud cost monitoring.
