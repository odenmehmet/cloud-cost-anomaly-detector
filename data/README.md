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

### Data Files (Generated Later)
- `raw/synthetic_cur_like_daily.csv`: Synthetic daily cost data with service/region breakdown
- `raw/anomaly_catalog.csv`: Ground truth anomaly labels and metadata
- `processed/features.csv`: Engineered features for anomaly detection
- `outputs/alerts.csv`: Generated warning and critical alerts
- `outputs/evaluation_summary.csv`: Precision, recall, F1, FP rate, detection delay
- `outputs/contributor_analysis.csv`: Service/region contribution to cost anomalies

### Git Policy
The `.gitignore` file excludes all CSV files in this directory from version control.
