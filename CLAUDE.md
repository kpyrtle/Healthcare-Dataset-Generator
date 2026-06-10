# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project has two main scripts:
- **`generate_dataset.py`** — produces a large synthetic clinical dataset with realistic, intentionally flawed data
- **`clean_healthcare_data.py`** — cleans the raw output and writes a cleaned CSV (or loads to SQL Server)

## Running the Scripts

```bash
# First-time setup
pip install -r requirements.txt
make env                                  # creates .env — fill in DB_SERVER and DB_DATABASE

# Generate the raw dataset (outputs to outputs/)
python generate_dataset.py               # or: make generate

# Clean the raw dataset -> outputs/healthcare_cleaned_full.csv
python clean_healthcare_data.py          # or: make clean-data

# Quick 1,000-row sample for inspection
python clean_healthcare_data.py --preview  # or: make preview

# Clean + normalize + bulk-load into SQL Server
python clean_healthcare_data.py --load-sql # or: make load-sql

# Format all Python files before committing
make format                               # runs Black on all .py files
```

All outputs land in `outputs/`:
- `healthcare_dataset_raw.csv` — raw generated data
- `data_quality_report.txt` — injected issue summary
- `healthcare_cleaned_full.csv` — full cleaned dataset
- `healthcare_cleaned_preview.csv` — 1,000-row sample (--preview only)

**Dependencies**: `pandas`, `numpy`, `sqlalchemy`, `tqdm`, `pyarrow`, `python-dotenv`, `black` (plus Python stdlib). Install: `pip install -r requirements.txt`.

## Architecture

The generator lives in the `healthcare_gen/` package. `generate_dataset.py` is a thin entry point.

| Module | Purpose |
|--------|---------|
| `config.py` | `CONFIG` dict (seed, n_patients, corruption rates, output paths) + CLI arg parser |
| `reference_data.py` | Static lookup tables: ICD-10 codes, CPT codes, meds, demographics, typo variants |
| `corruption.py` | `DataQualityTracker`; `corrupt()` and `add_typo()` helpers used throughout |
| `demographics.py` | `generate_patient_demographics()`, `generate_social_determinants()` |
| `clinical.py` | Vitals, labs, diagnosis selection (seasonal weighting via `@lru_cache`) |
| `visits.py` | `generate_visit()` — orchestrates one encounter; `_START_DATE`/`_END_DATE` parsed once at module level |
| `pipeline.py` | `_generate_chunk()` (worker unit); `generate_dataset()` with serial (`--cores 1`) and parallel (`--cores N`) branches; post-processing; schema validation |
| `main.py` | CLI entry point |

### Generation Pipeline

```
generate_dataset()
└── per patient: generate_patient_demographics()
    └── per visit: generate_visit()
        ├── select_diagnosis_for_date()       # seasonal weighting via lru_cache
        ├── generate_secondary_diagnoses()    # comorbidity relationships
        ├── generate_vitals()                 # batched np.random.normal draw
        ├── generate_bmi()
        ├── generate_lab_results()            # batched base draw + dx-specific overrides
        ├── generate_procedures()
        ├── generate_medications()
        ├── generate_charges()
        ├── generate_social_determinants()
        ├── calculate_readmit_risk()
        └── calculate_mortality_risk()
    └── post-processing: add_duplicates(), shuffle, swap_fields()
```

### Data Quality Injection

Corruption is injected intentionally throughout generation, controlled by `CONFIG` rates:

- **Missing values** — 4% general rate, 6% vitals, 10% labs, 20% satisfaction scores
- **Typos** — 2% rate using variant dictionaries in reference data
- **Impossible values** — 1% rate (e.g., negative charges)
- **Swapped fields** — 0.5% rate (admit/discharge dates, first/last names)
- **Duplicate rows** — 0.9% rate
- **Charge inflation** — 2% rate
- **Invalid ICD-10 codes** — 6% rate (truncation, character substitution, or extra digit appended to `primary_dx_code` / `secondary_dx_codes`; clinical fields use the clean code)

All injected issues are tracked by `DataQualityTracker` and written to the quality report.

### Clinical Correlations

Vitals and labs are correlated to diagnosis, age, and department — e.g., BP elevated for hypertension patients, glucose elevated for diabetes, troponin elevated for MI. ICU encounters have higher variance. Seasonal diagnosis weighting affects flu/RSV (winter), asthma (spring/fall), etc.

## Cleaning Pipeline (`clean_healthcare_data.py`)

A standalone script — no package structure. SQL Server credentials are loaded from `.env` via `python-dotenv` (never hardcoded). Run `make env` to scaffold `.env` from `.env.example`. Default output is `outputs/healthcare_cleaned_full.csv`; pass `--load-sql` to also normalize and bulk-load into SQL Server.

Cleaning steps in order:
1. Empty strings → `NaN`
2. Exact duplicates and duplicate patient/admit-date pairs removed
3. Categorical typos standardized (department, gender, insurance)
4. Dates parsed; length of stay recomputed; age derived from DOB
5. Vitals and labs clamped to physiologically plausible ranges
6. Negative charges corrected via `abs()` + `charge_sign_corrected` flag; extreme charges (> $10M) nulled
7. Invalid satisfaction scores (outside 1–10) nulled
8. Malformed zip codes nulled; valid zips truncated to 3-digit prefix (HIPAA Safe Harbor)
9. Logical flag consistency: `readmitted=1` with no `days_to_readmission` flagged
10. Invalid discharge disposition values nulled
11. Mortality/readmission contradictions corrected
12. `days_to_readmission` clamped to 1–30 day window; `readmission_days_missing` flag recomputed
13. `ed_visits_past_6mo` validated as non-negative integer
14. Safe Harbor de-identification: `date_of_birth` → `birth_year` (year only); `patient_id` → `research_id` (SHA-256 12-char hex); `first_name`, `last_name` dropped

## Key Design Decisions

- **Reproducibility**: Controlled by `CONFIG["seed"]` (default 42). Change to get different data.
- **Volume**: `CONFIG["n_patients"]` (default 340,000); patients get 1–4 visits each, yielding ~500,000 rows.
- **Date range**: 2019-01-01 to 2024-12-31.
- **Output**: Denormalized CSV by default; `--load-sql` normalizes into `patients`, `encounters`, `vitals`, `lab_results`, `encounter_outcomes`, and `ed_utilization` tables in SQL Server.
- **Credentials**: SQL Server connection values (`DB_SERVER`, `DB_DATABASE`, `DB_DRIVER`) are read from `.env` — see `.env.example` for the template.
- **No external data sources**: All reference data is hardcoded in the script.
