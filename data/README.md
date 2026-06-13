## Data Directory

This directory contains raw, processed, and output data for the cloud cost anomaly detection pipeline.

### Directory Structure
- **raw/**: Synthetic CUR-like labeled billing data (generated in Phase 2)
- **processed/**: Cleaned, validated, and preprocessed daily cost data
- **outputs/**: Detector, alert, and contributor analysis outputs

### Important Notes

**No real cloud billing data should be committed to this repository.** All data is:
- **Synthetic and reproducible**: Generated using a fixed random seed for consistent evaluation
- **Regenerable**: Raw, processed, output, and report CSV files are created by the pipeline modules
- **Ephemeral**: Output files can be regenerated without loss

### Phase 2 Generated Files
- `raw/synthetic_cur_like_daily.csv`: Synthetic CUR-like daily billing rows with stable account, billing-period, service, region, tag, and label fields
- `raw/anomaly_catalog.csv`: Catalog of injected true anomalies
- `raw/planned_event_catalog.csv`: Separate catalog of legitimate planned usage events

### Phase 3 Processed Files
- `processed/daily_total_cost.csv`: Daily total cost and usage aggregate with labels
- `processed/daily_service_cost.csv`: Daily service-level cost and usage aggregate
- `processed/daily_region_cost.csv`: Daily region-level cost and usage aggregate
- `processed/daily_service_region_cost.csv`: Daily service-region aggregate for later contributor analysis
- `processed/daily_features.csv`: Detector-ready daily feature table for later algorithms

### Phase 4 Detector Output Files
- `outputs/zscore_results.csv`: Rolling Z-score detector results
- `outputs/stl_results.csv`: STL residual detector results
- `outputs/stl_components.csv`: STL trend, seasonal, residual, and expected-cost components
- `outputs/isolation_forest_results.csv`: Isolation Forest detector results
- `outputs/method_results.csv`: Stacked method-level detector results for later alert logic

### Phase 5 Alert and Contributor Files
- `outputs/alert_method_summary.csv`: Daily method agreement and alert-decision summary
- `outputs/alerts.csv`: Operational warning and critical alerts based on agreement and upward relative cost deviation
- `outputs/suppressed_alerts.csv`: Planned-event detector candidates excluded from operational alerts
- `outputs/contributors.csv`: Top service-region contributors for each alert date

### Phase 6 Evaluation Reports
- `../reports/evaluation_summary.csv`: Precision, recall, F1, false positives per 30 days, exact-day and tolerant matching
- `../reports/calibration_summary.csv`: Bounded detector candidate sweep and selected settings
- `../reports/event_level_evaluation.csv`: Event precision, recall, and F1 for contiguous prediction runs
- `../reports/evaluation_by_type.csv`: Recall by injected anomaly type
- `../reports/detection_delay.csv`: Event-level detection delay by subject
- `../reports/false_positive_days.csv`: Exact-day false-positive listing
- `../reports/evaluation_daily_predictions.csv`: Daily ground-truth labels and prediction flags

### Git Policy
Generated CSV files should be left uncommitted unless the repository owner explicitly wants sample data committed.
