## Data Directory

This directory contains raw, processed, and output data for the cloud cost anomaly detection pipeline.

### Directory Structure
- **raw/**: Synthetic CUR-like labeled billing data (generated in Phase 2)
- **processed/**: Cleaned, validated, and preprocessed daily cost data
- **outputs/**: Anomaly detection results and evaluation metrics

### Important Notes

**No real cloud billing data should be committed to this repository.** All data is:
- **Synthetic and reproducible**: Generated using a fixed random seed for consistent evaluation
- **Generated in later phases**: Raw and processed CSV files are created by `data_generator.py`
- **Ephemeral**: Output files can be regenerated without loss

### Phase 2 Generated Files
- `raw/synthetic_cur_like_daily.csv`: Synthetic CUR-like daily billing rows with service, region, environment, team, and ground-truth labels
- `raw/anomaly_catalog.csv`: Catalog of injected true anomalies and planned usage events

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
- `outputs/alerts.csv`: Warning and critical alerts based on method agreement and relative cost deviation
- `outputs/contributors.csv`: Top service-region contributors for each alert date

### Future Phase Files
- `outputs/evaluation_summary.csv`: Precision, recall, F1, FP rate, detection delay

### Git Policy
Generated CSV files should be left uncommitted unless the repository owner explicitly wants sample data committed.
