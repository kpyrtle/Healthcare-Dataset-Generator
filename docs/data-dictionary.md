# Data Dictionary — Healthcare Encounters Database

## Overview

This database contains synthetic clinical data for approximately 340,000 patients across roughly
500,000 hospital encounters spanning 2019–2024. It is organized into six tables: one for patient
demographics, one for encounter details, and four for clinical measurements and outcomes. All
patient identifiers have been de-identified in accordance with HIPAA Safe Harbor standards.

---

## How the Tables Relate

```
patients ──────────────────────────────────────── (one patient, many encounters)
    │ research_id
    │
encounters ─────────────────────────────────────── (one encounter per row)
    │ encounter_id
    ├── vitals              (measurements taken at admission)
    ├── lab_results         (lab work drawn during the encounter)
    ├── encounter_outcomes  (readmission and mortality flags)
    └── ed_utilization      (prior ED visit history)
```

**Primary keys:** `patients.research_id`, `encounters.encounter_id`
**Foreign keys:** All clinical tables join to `encounters` on `encounter_id`.
`ed_utilization` also carries `research_id` for patient-level lookups.

---

## dbo.patients

One row per unique patient. Contains static demographic information.

| Column | Description | Values / Format |
|--------|-------------|-----------------|
| `research_id` | De-identified patient ID (SHA-256 hash, 12 characters). Replaces the original patient name and ID. | 12-char hex string |
| `gender` | Patient's reported gender | Male, Female, Non-binary, Unknown |
| `birth_year` | Year of birth only (full date of birth removed for privacy) | e.g. 1965 |
| `zip_code` | First 3 digits of ZIP code only (truncated for privacy per HIPAA Safe Harbor) | e.g. "606" |

---

## dbo.encounters

One row per hospital encounter (admission). The central table — everything else joins here.

| Column | Description | Values / Format |
|--------|-------------|-----------------|
| `encounter_id` | Unique identifier for this encounter | Integer |
| `research_id` | Links to `dbo.patients` | 12-char hex string |
| `admit_date` | Date and time the patient was admitted | datetime |
| `discharge_date` | Date and time the patient was discharged | datetime |
| `length_of_stay_days` | Number of days between admission and discharge. Recomputed from dates during cleaning. | Integer ≥ 0 |
| `age` | Patient's age at the time of admission | Integer, 0–120 |
| `department` | Hospital department where the encounter took place | Emergency, Cardiology, ICU, Medicine, Neurology, Oncology, Orthopedics, Pediatrics, Surgery, Psychiatry |
| `insurance_type` | Primary payer for this encounter | Medicare, Medicaid, Private, Self-pay, Unknown |
| `total_charges_usd` | Total billed charges for the encounter in US dollars | Float; NULL if > $10M (considered erroneous) |
| `charge_sign_corrected` | Flag indicating the original charge was negative and was corrected by taking the absolute value | 0 = no correction, 1 = corrected |
| `discharge_disposition` | Where the patient went after leaving the hospital | Home, Skilled Nursing Facility, Home Health, AMA (left against medical advice), Expired, Rehab, Transfer, Hospice, Long-term Acute Care |
| `patient_satisfaction_score` | Patient-reported satisfaction with their care | 1–10 scale; NULL if missing or invalid |

---

## dbo.vitals

One row per encounter. Clinical measurements typically taken at or near the time of admission.
All values are NULLed if they fall outside physiologically plausible ranges.

| Column | Description | Plausible Range |
|--------|-------------|-----------------|
| `encounter_id` | Links to `dbo.encounters` | |
| `bp_systolic` | Systolic blood pressure — the top number in a blood pressure reading, representing pressure when the heart beats | 50–300 mmHg |
| `bp_diastolic` | Diastolic blood pressure — the bottom number, representing pressure when the heart rests between beats | 20–200 mmHg |
| `heart_rate_bpm` | Heart rate in beats per minute | 20–300 bpm |
| `o2_saturation_pct` | Oxygen saturation — the percentage of hemoglobin carrying oxygen; below 90% is generally considered clinically concerning | 50–100% |
| `temperature_f` | Body temperature in Fahrenheit | 90–108°F |
| `bmi` | Body Mass Index — a weight-to-height ratio used as a general measure of body composition | 10–80 |

> **Note:** Vitals are missing for approximately 6% of encounters by design, reflecting real-world
> data gaps in EHR systems.

---

## dbo.lab_results

One row per encounter. Laboratory tests ordered during the hospital stay.
All values are NULLed if they fall outside physiologically plausible ranges.
Several of these (HbA1c, lactate, troponin) are condition-specific and will be NULL for most
encounters.

| Column | Description | Plausible Range |
|--------|-------------|-----------------|
| `encounter_id` | Links to `dbo.encounters` | |
| `glucose_mg_dl` | Blood sugar level — elevated values are associated with diabetes and critical illness | 20–800 mg/dL |
| `creatinine_mg_dl` | Waste product filtered by the kidneys — elevated values suggest reduced kidney function | 0.1–20 mg/dL |
| `potassium_meq_l` | Electrolyte critical for heart and muscle function — both high and low values can be dangerous | 1.5–9.0 mEq/L |
| `sodium_meq_l` | Electrolyte that regulates fluid balance — abnormal levels can indicate dehydration or kidney issues | 100–180 mEq/L |
| `wbc_k_ul` | White blood cell count — elevated in infection and inflammation; very low values may indicate immune compromise | 0.5–100 K/µL |
| `hemoglobin_g_dl` | Protein in red blood cells that carries oxygen — low values indicate anemia | 3.0–22 g/dL |
| `hba1c_pct` | Hemoglobin A1c — reflects average blood sugar over the past 2–3 months; used to diagnose and monitor diabetes. Sparse — only populated for relevant patients. | 3.0–20% |
| `lactate_mmol_l` | Lactate — a byproduct of metabolism that accumulates when tissues aren't getting enough oxygen; elevated in sepsis and shock. Sparse. | 0.2–30 mmol/L |
| `troponin_ng_ml` | Protein released into the blood when the heart muscle is damaged; elevated values are a key marker for heart attack. Sparse. | 0.0–50 ng/mL |

---

## dbo.encounter_outcomes

One row per encounter. Tracks what happened after discharge — whether the patient returned
and whether they survived.

| Column | Description | Values |
|--------|-------------|--------|
| `encounter_id` | Links to `dbo.encounters` | |
| `readmitted_30day` | Whether this encounter was followed by a hospital readmission within 30 days of discharge. This flag lives on the **index encounter** (the one that came first), not the readmission itself. | 0 = not readmitted, 1 = readmitted |
| `days_to_readmission` | How many days elapsed between discharge and the next admission. Only populated when `readmitted_30day = 1`. | Integer, 1–30; NULL otherwise |
| `readmission_days_missing` | Flag for encounters where `readmitted_30day = 1` but `days_to_readmission` could not be determined | 0 = days known, 1 = days missing |
| `inpatient_mortality` | Whether the patient died during this encounter | 0 = survived, 1 = died |

> **Note:** A patient recorded as `inpatient_mortality = 1` will always have `readmitted_30day = 0`
> — a patient who died cannot have been readmitted.

---

## dbo.ed_utilization

One row per encounter. Captures how frequently the patient had visited the emergency department
in the six months before this admission — a known risk factor for readmission.

| Column | Description | Values |
|--------|-------------|--------|
| `encounter_id` | Links to `dbo.encounters` | |
| `research_id` | Links to `dbo.patients` — included here to support patient-level lookups without joining through `encounters` | |
| `ed_visits_past_6mo` | Number of ED visits in the 6 months prior to this admission. Values > 20 are treated as implausible and NULLed. | Integer, 0–20; sparse (NULL for many rows) |
