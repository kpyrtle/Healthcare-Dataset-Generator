# Healthcare Dataset Generator

Generates a large synthetic clinical dataset with realistic, intentionally flawed data for testing validation and cleaning pipelines.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic run (340,000 patients, serial, CSV output)
python generate_dataset.py

# Parallel run using 8 cores, Parquet output (faster write, smaller file)
python generate_dataset.py --cores 8 --format parquet

# Skip summary (e.g. when scripting / timing runs)
python generate_dataset.py --no-verbose

# Override defaults
python generate_dataset.py --n-patients 5000 --seed 99 --output my_data.csv --report my_report.txt
```

**Outputs:**
- `healthcare_dataset_improved.csv` (or `.parquet` with `--format parquet`) — denormalized, ~46 columns, one row per visit
- `data_quality_report.txt` — summary of all injected data quality issues

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--n-patients` | 340,000 | Number of patients to generate |
| `--seed` | 42 | Random seed for reproducibility |
| `--output` | `healthcare_dataset_improved.csv` | CSV output path |
| `--report` | `data_quality_report.txt` | Quality report output path |
| `--cores` | 1 | Worker processes (1 = serial/reproducible, >1 = parallel) |
| `--format` | `csv` | Output format: `csv` or `parquet` (faster write, ~5–10x smaller) |
| `--no-verbose` | — | Skip dataset summary and schema validation after generation |

## Dataset Overview

Each patient gets 1–4 visits (70% single-visit, 18% two visits, etc.) spanning 2019–2024. The dataset includes:

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
