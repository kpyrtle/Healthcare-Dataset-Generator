# Healthcare Dataset Generator

Generates a large synthetic clinical dataset with realistic, intentionally flawed data for testing validation and cleaning pipelines.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic run (340,000 patients, auto-detected cores, CSV output)
python generate_dataset.py

# Parallel run using 8 cores, Parquet output (faster write, smaller file)
python generate_dataset.py --cores 8 --format parquet

# Skip summary (e.g. when scripting / timing runs)
python generate_dataset.py --no-verbose

# Override defaults
python generate_dataset.py --n-patients 5000 --seed 99 --output my_data.csv --report my_report.txt
```

**Outputs** (written to `outputs/`):
- `healthcare_dataset_raw.csv` (or `.parquet` with `--format parquet`) — denormalized, ~46 columns, one row per visit
- `data_quality_report.txt` — summary of all injected data quality issues

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--n-patients` | 340,000 | Number of patients to generate |
| `--seed` | 42 | Random seed for reproducibility |
| `--output` | `outputs/healthcare_dataset_raw.csv` | CSV output path |
| `--report` | `outputs/data_quality_report.txt` | Quality report output path |
| `--cores` | `os.cpu_count()` | Worker processes (1 = serial/reproducible, >1 = parallel; auto-detects CPUs) |
| `--format` | `csv` | Output format: `csv` or `parquet` (faster write, ~5–10x smaller) |
| `--no-verbose` | — | Skip dataset summary and schema validation after generation |

## Cleaning

`clean_healthcare_data.py` reads `outputs/healthcare_dataset_raw.csv`, applies the full cleaning pipeline, and loads the result into SQL Server.

**Before running**, update the connection constants near the top of the file:

```python
SERVER    = "YOUR_SERVER_NAME"    # e.g. localhost\\SQLEXPRESS
DATABASE  = "YOUR_DATABASE_NAME"
```

```bash
# Clean and save the full dataset to CSV
python clean_healthcare_data.py

# Save a 1,000-row sample for quick inspection
python clean_healthcare_data.py --preview
```

**Outputs** (written to `outputs/`):
- Default: `healthcare_cleaned_full.csv` — full cleaned dataset
- `--preview`: `healthcare_cleaned_preview.csv` — 1,000-row sample

To load into SQL Server instead, update the connection constants near the top of the file (`SERVER`, `DATABASE`) and uncomment the `load_to_sql_server(df)` call in `main()`.

### What the cleaner fixes

| Issue | Action |
|-------|--------|
| Exact duplicate rows | Dropped |
| Duplicate patient + admit-date pairs | Deduped (first kept) |
| Empty strings | Converted to `NaN` |
| Categorical typos (department, gender, insurance) | Standardized via lookup maps |
| Negative length of stay | Nulled |
| Implausible age values | Nulled |
| Out-of-range vitals and labs | Nulled |
| Negative charges | Corrected via `abs()` + `charge_sign_corrected` flag |
| Extreme charges (> $10M) | Nulled |
| Invalid satisfaction scores (outside 1–10) | Nulled |
| Malformed zip codes | Nulled |
| `readmitted=1` with no `days_to_readmission` | Flagged in `readmission_days_missing` |
| `days_to_readmission` outside 1–30 day window | Nulled |
| `inpatient_mortality=1` with `readmitted_30day=1` | Readmission corrected to 0 |
| PII columns (`first_name`, `last_name`) | Dropped |

## Dataset Overview

Each patient gets 1–4 visits (70% single-visit, 18% two visits, etc.) spanning 2019–2024, yielding roughly **~500,000 rows** at the default 340,000-patient scale (expected avg 1.46 visits/patient + ~0.9% duplicate injection). The dataset includes:

- **Demographics**: patient ID, name, DOB, age, gender, race/ethnicity, state, ZIP, insurance
- **Encounter**: admit/discharge dates, department, admit type, length of stay
- **Diagnoses & procedures**: ICD-10 primary + secondary codes, CPT procedure codes
- **Vitals**: BP, heart rate, O2 saturation, temperature, BMI
- **Labs**: glucose, creatinine, potassium, sodium, WBC, hemoglobin
- **Outcomes**: 30-day readmission, inpatient mortality, discharge disposition, satisfaction score
- **Social determinants**: PCP status, lives alone, transportation access, recent ED visits

## Intentional Data Quality Issues

The dataset is corrupted at configured rates to simulate real-world data problems:

| Issue | Rate |
|-------|------|
| Missing values (general) | 4% |
| Missing vitals | 6% |
| Missing lab results | 10% |
| Missing satisfaction scores | 20% |
| Typos in categorical fields | 2% |
| Impossible values (e.g. negative charges) | 1% |
| Swapped fields (dates or names) | 0.5% |
| Duplicate rows | 0.9% |
| Charge inflation | 2% |

All injected issues are catalogued in the quality report.

## Package Structure

```
healthcare_gen/
├── config.py         # CONFIG dict + CLI argument parser
├── reference_data.py # ICD-10 codes, CPT codes, medications, demographics, typo variants
├── corruption.py     # DataQualityTracker; missing/typo/impossible-value injection helpers
├── demographics.py   # generate_patient_demographics()
├── clinical.py       # Vitals, labs, charges — clinically correlated to diagnosis/age/dept
├── visits.py         # generate_visit() — orchestrates one encounter
├── pipeline.py       # generate_dataset(), post-processing (dedup, shuffle, swaps), schema validation
└── main.py           # CLI entry point
```

To change what gets generated, start with `config.py` (`CONFIG` dict) and the relevant module above.
