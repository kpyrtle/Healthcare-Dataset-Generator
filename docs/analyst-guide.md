# Analyst Guide — 30-Day Readmissions Project

## What Is This Dataset?

A synthetic clinical dataset (~500,000+ encounter rows across ~340,000 patients) designed to practice real healthcare data analysis skills. Data is intentionally imperfect — it contains missing values, typos, impossible values, duplicates, and other issues you must find and fix before analyzing.

## The Project

**Goal:** Identify patients who were readmitted to the hospital within 30 days of discharge and analyze the factors associated with readmission.

This mirrors a real-world healthcare analytics task used by hospitals to reduce preventable readmissions.

---

## Step 1 — Clean the Data

Run the cleaning script first:

```bash
python clean_healthcare_data.py
# outputs/healthcare_cleaned_full.csv

# or for a quick 1,000-row sample:
python clean_healthcare_data.py --preview
```

The cleaning script fixes known issues, but it doesn't catch everything. Part of the exercise is finding remaining problems.

Known injected issues to look for:
- Missing values in vitals, labs, satisfaction scores
- Typos in categorical fields (department, gender, insurance)
- Negative charges
- Dates out of order (admit after discharge)
- Duplicate rows
- Satisfaction scores outside 1–10

---

## Step 2 — Find the Readmissions

The dataset does **not** have an `is_readmission` column. You must find readmissions yourself.

### What you know:
- Each row is one encounter (one hospital admission)
- Encounters are linked by `patient_id`
- `admit_date` and `discharge_date` tell you when each stay happened

### How to find readmissions:
For each patient, sort their encounters by `admit_date`. A readmission is an encounter where the patient was admitted within 30 days of a prior discharge.

```python
# Pseudocode
df = df.sort_values(['patient_id', 'admit_date'])
df['prev_discharge'] = df.groupby('patient_id')['discharge_date'].shift(1)
df['days_since_discharge'] = (df['admit_date'] - df['prev_discharge']).dt.days
df['is_readmission_derived'] = (df['days_since_discharge'] <= 30) & (df['days_since_discharge'] >= 1)
```

### How to validate your work:
Compare your derived result against the ground truth columns on index visits:
- `readmitted_30day` — `1` if that encounter was followed by a return within 30 days
- `days_to_readmission` — how many days until the return

If your derivation is correct, the encounter *after* every `readmitted_30day = 1` row (for the same patient) should have `is_readmission_derived = True`, and the gap should match `days_to_readmission`.

**Important:** `readmitted_30day` lives on the *index visit* (the visit that preceded the readmission), not on the readmission itself.

---

## Step 3 — Analyze

Once you have readmissions identified, explore:

### Readmission rate by diagnosis
Which conditions have the highest 30-day readmission rates? (Heart failure, COPD, sepsis are typically high in real data.)

Key column: `primary_dx_description` or `primary_dx_code`

### Readmission rate by insurance type
Uninsured and Medicaid patients have higher readmission rates. Does your data show this?

Key column: `insurance_type`

### Effect of social determinants
Does lack of PCP access, living alone, or no transportation correlate with readmission?

Key columns: `has_pcp`, `lives_alone`, `has_transportation`

### Length of stay
Is there a relationship between how long the index stay was and whether the patient came back?

Key column: `length_of_stay_days`

### Readmission timing
When within the 30-day window do most readmissions happen? (Real data typically shows a spike in days 3–10.)

Key column: `days_to_readmission` on index visits

---

## Step 4 — Visualize

Suggested charts:
- Bar chart: readmission rate by diagnosis (top 10 conditions)
- Grouped bar: readmission rate by insurance type
- Histogram: distribution of `days_to_readmission`
- Heatmap: readmission rate by department × age group
- Line chart: readmission rate by month (is there seasonality?)

---

## Column Reference

See `CONTEXT.md` for definitions of all domain terms.

| Column | Type | Notes |
|--------|------|-------|
| `patient_id` | string | Replaced by `research_id` (SHA-256 hash) after de-identification |
| `admit_date` | date | Start of encounter |
| `discharge_date` | date | End of encounter |
| `length_of_stay_days` | int | Recomputed during cleaning |
| `primary_dx_code` | string | ICD-10 code |
| `readmitted_30day` | int (0/1) | 1 = this encounter was an index visit; a readmission row exists for this patient |
| `days_to_readmission` | float | Days from discharge to readmission admit; only populated when `readmitted_30day = 1` |
| `discharge_disposition` | string | Where patient went after discharge |
| `has_pcp` | bool | Whether patient has a primary care provider |
| `lives_alone` | bool | Social determinant |
| `has_transportation` | bool | Social determinant |
| `ed_visits_past_6mo` | int | Prior ED utilization — a readmission risk factor |
| `procedure_codes` | string | Pipe-separated ICD-10 procedure codes (e.g. `99213|71046`) |
| `procedure_descriptions` | string | Pipe-separated descriptions matching `procedure_codes` order |
| `medications` | string | Pipe-separated medication names |
| `secondary_dx_codes` | string | Pipe-separated ICD-10 codes for comorbidities |

### Querying pipe-separated columns in SQL Server

These columns are stored as single strings. Use `STRING_SPLIT()` (SQL Server 2016+) to expand them into rows:

```sql
-- Example: find all patients who received a specific medication
SELECT patient_id, value AS medication
FROM healthcare_cleaned_full
CROSS APPLY STRING_SPLIT(medications, '|')
WHERE medications IS NOT NULL
  AND value = 'Metformin';
```

---

## What Makes This Realistic

- Diagnoses have seasonal weighting (flu peaks in winter, asthma in spring/fall)
- Vitals and labs are correlated to diagnosis (e.g., diabetic patients have elevated glucose)
- Readmission risk is driven by age, diagnosis severity, insurance, LOS, and PCP access — matching real clinical risk factors
- Readmission visit diagnoses are not always the same as the index — 60% same condition, 30% related comorbidity, 10% unrelated

## What Is Simplified

- No physician notes or free text
- No medication reconciliation (medications are listed but not cross-checked)
- Readmissions do not chain (a readmission row will never itself have `readmitted_30day = 1`)
- All data is for a single hypothetical hospital system
