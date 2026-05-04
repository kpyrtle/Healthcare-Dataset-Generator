# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **synthetic healthcare dataset generator** — a single Python script (`generate_dataset.py`) that produces realistic, intentionally flawed clinical data for testing data validation and cleaning pipelines.

## Running the Generator

```bash
# Generate the dataset
python generate_dataset.py

# Outputs:
#   /mnt/user-data/outputs/healthcare_dataset_improved.csv
#   /mnt/user-data/outputs/data_quality_report.txt
```

**Dependencies**: `pandas`, `numpy` (plus Python stdlib). No install step or build system.

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

All injected issues are tracked by `DataQualityTracker` and written to the quality report.

### Clinical Correlations

Vitals and labs are correlated to diagnosis, age, and department — e.g., BP elevated for hypertension patients, glucose elevated for diabetes, troponin elevated for MI. ICU encounters have higher variance. Seasonal diagnosis weighting affects flu/RSV (winter), asthma (spring/fall), etc.

## Key Design Decisions

- **Reproducibility**: Controlled by `CONFIG["seed"]` (default 42). Change to get different data.
- **Volume**: `CONFIG["n_patients"]` (default 5000); patients get 1–4 visits each.
- **Date range**: 2019-01-01 to 2024-12-31.
- **Output**: Single denormalized CSV (~60+ columns); no relational tables.
- **No external data sources**: All reference data is hardcoded in the script.
