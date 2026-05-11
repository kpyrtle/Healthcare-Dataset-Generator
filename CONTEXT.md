# Domain Context — Healthcare Readmissions Dataset

This document defines the canonical terms for this project. When writing code, documentation, or analysis, use these terms exactly.

---

## Core Terms

### Patient
A single person in the dataset, identified by `patient_id`. One patient can have multiple encounters.

### Encounter (Visit)
A single hospital admission for a patient — one row in the dataset. Identified by the combination of `patient_id` + `admit_date`. Each encounter has one primary diagnosis, vitals, labs, charges, and an outcome.

### Index Visit
An encounter where `readmitted_30day = 1`. This is the admission that *preceded* a return visit. The index visit is the starting point for readmission analysis.

### Readmission
An encounter that occurred within 30 days of a prior discharge for the same patient. There is no explicit column marking a row as a readmission — analysts must derive it by finding encounters where `admit_date` falls within `prior_discharge_date + days_to_readmission` for the same patient.

### 30-Day Readmission Window
The 30-calendar-day period following a discharge date. A return visit within this window counts as a readmission. This follows the CMS Hospital Readmissions Reduction Program (HRRP) definition.

### Days to Readmission
`days_to_readmission` — populated only when `readmitted_30day = 1`. The number of days between the index visit discharge and the readmission admit date. Range: 1–30. Drawn from an exponential distribution (mean ~12 days).

### Length of Stay (LOS)
`length_of_stay_days` — number of days between `admit_date` and `discharge_date`. Recomputed during cleaning; not trusted from raw generation directly.

### Primary Diagnosis
`primary_dx_code` — ICD-10 code for the main reason for admission. Drives clinical correlations (vitals, labs, readmission risk).

### Secondary Diagnoses
`secondary_dx_codes` — comma-separated ICD-10 codes for comorbidities present during the encounter. Used as the "related" pool when generating readmission visit diagnoses.

### Readmission Risk Score
Internal float (0.0–0.60) computed by `calculate_readmit_risk()` from age, diagnosis severity, insurance type, LOS, and PCP status. Not exposed as a column — it is used only to generate the `readmitted_30day` flag.

### Social Determinants of Health (SDOH)
Non-clinical factors that affect health outcomes: `has_pcp`, `lives_alone`, `has_transportation`, `ed_visits_past_6mo`. These influence readmission risk.

### Data Quality Injection
Intentional corruption applied during generation: missing values, typos, impossible values, swapped fields, duplicate rows, charge inflation. Controlled by rates in `CONFIG`. Tracked by `DataQualityTracker` and written to `data_quality_report.txt`.

### Ground Truth
The `readmitted_30day` and `days_to_readmission` columns on index visits. Analysts use these to validate whether their derived readmission linkage is correct.

---

## What This Dataset Is For

Practicing data analysis skills on realistic healthcare data:
1. **Cleaning** — fix injected quality issues (nulls, typos, out-of-range values, duplicates)
2. **Analysis** — identify index visits, link to readmission rows, compute readmission rates by diagnosis/insurance/age/SDOH
3. **Visualization** — trends over time, risk factor breakdowns, LOS vs readmission relationships

The dataset is synthetic. It is not real patient data. Clinical correlations are approximations designed to produce realistic-looking patterns, not medically precise simulations.
