import random
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from typing import Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import CONFIG
from .corruption import DataQualityTracker
from .demographics import generate_patient_demographics
from .visits import generate_visit

EXPECTED_COLUMNS = {
    "patient_id", "first_name", "last_name", "date_of_birth", "age",
    "gender", "race_ethnicity", "state", "zip_code", "insurance_type",
    "visit_number", "admit_date", "admit_time", "discharge_date",
    "length_of_stay_days", "department", "admit_type",
    "primary_dx_code", "primary_dx_description", "secondary_dx_codes",
    "procedure_codes", "procedure_descriptions", "medications",
    "attending_provider_id", "bp_systolic", "bp_diastolic",
    "heart_rate_bpm", "o2_saturation_pct", "temperature_f", "bmi",
    "total_charges_usd", "readmitted_30day", "days_to_readmission",
    "discharge_disposition", "patient_satisfaction_score",
    "inpatient_mortality", "has_pcp", "lives_alone", "has_transportation",
    "ed_visits_past_6mo", "glucose_mg_dl", "creatinine_mg_dl",
    "potassium_meq_l", "sodium_meq_l", "wbc_k_ul", "hemoglobin_g_dl",
}


def set_seeds(seed: int):
    np.random.seed(seed)
    random.seed(seed)


def rand_date(start: datetime, end: datetime) -> datetime:
    return start + timedelta(days=random.randint(0, (end - start).days))


def _generate_chunk(
    start_idx: int, end_idx: int, seed_offset: int
) -> Tuple[list, DataQualityTracker]:
    set_seeds(CONFIG["seed"] + seed_offset)
    tracker = DataQualityTracker()
    rows = []

    for i in range(start_idx, end_idx):
        patient_id = f"PT{i + 1:06d}"
        demographics = generate_patient_demographics(patient_id, tracker, i)

        if CONFIG["multi_visit"]["enabled"]:
            n_visits = np.random.choice(
                [1, 2, 3, 4], p=CONFIG["multi_visit"]["visit_distribution"]
            )
        else:
            n_visits = 1

        prev_discharge = None
        for visit_num in range(1, n_visits + 1):
            result = generate_visit(
                patient_id, demographics, visit_num, prev_discharge, tracker, i
            )
            if result is None:
                break
            visit_row, prev_discharge = result
            rows.append(visit_row)

    return rows, tracker


def generate_dataset() -> Tuple[pd.DataFrame, DataQualityTracker]:
    set_seeds(CONFIG["seed"])
    tracker = DataQualityTracker()
    n_patients = CONFIG["n_patients"]
    n_cores = CONFIG["n_cores"]

    if n_cores <= 1:
        rows = []
        row_idx = 0

        print(f"Generating data for {n_patients} patients...")

        for i in tqdm(range(n_patients), desc="Patients", unit="pt"):
            patient_id = f"PT{i + 1:06d}"

            demographics = generate_patient_demographics(patient_id, tracker, row_idx)

            if CONFIG["multi_visit"]["enabled"]:
                n_visits = np.random.choice(
                    [1, 2, 3, 4], p=CONFIG["multi_visit"]["visit_distribution"]
                )
            else:
                n_visits = 1

            prev_discharge = None
            for visit_num in range(1, n_visits + 1):
                result = generate_visit(
                    patient_id, demographics, visit_num, prev_discharge, tracker, row_idx
                )

                if result is None:
                    break

                visit_row, prev_discharge = result
                rows.append(visit_row)
                row_idx += 1

    else:
        chunk_size = n_patients // n_cores
        chunks = [
            (
                i * chunk_size,
                (i + 1) * chunk_size if i < n_cores - 1 else n_patients,
                i,
            )
            for i in range(n_cores)
        ]

        print(f"Generating data for {n_patients} patients across {n_cores} workers...")

        rows = []
        with ProcessPoolExecutor(max_workers=n_cores) as ex:
            futures = [ex.submit(_generate_chunk, s, e, off) for s, e, off in chunks]
            for fut in tqdm(futures, desc="Chunks", unit="chunk"):
                chunk_rows, chunk_tracker = fut.result()
                rows.extend(chunk_rows)
                tracker.merge(chunk_tracker)

    print(f"Generated {len(rows)} total visits")

    df = pd.DataFrame(rows)

    n_dups = int(len(df) * CONFIG["corruption"]["duplicate_patient_rate"])
    dup_indices = random.sample(range(len(df)), min(n_dups, len(df)))
    dups = df.iloc[dup_indices].copy()
    df = pd.concat([df, dups], ignore_index=True)

    for idx in dup_indices[:n_dups]:
        tracker.record("duplicate_row", f"Row {idx}", idx)

    print(f"Added {len(dup_indices)} duplicate rows")

    df = df.sample(frac=1, random_state=99).reset_index(drop=True)

    swap_indices = random.sample(
        range(len(df)), int(len(df) * CONFIG["corruption"]["swapped_field_rate"])
    )
    for idx in swap_indices:
        if random.random() < 0.5:
            df.at[idx, "admit_date"], df.at[idx, "discharge_date"] = (
                df.at[idx, "discharge_date"],
                df.at[idx, "admit_date"],
            )
            tracker.record("swapped_dates", f"Row {idx}", idx)
        else:
            df.at[idx, "first_name"], df.at[idx, "last_name"] = (
                df.at[idx, "last_name"],
                df.at[idx, "first_name"],
            )
            tracker.record("swapped_names", f"Row {idx}", idx)

    return df, tracker


def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)

    print(f"\nRows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Unique patients: {df['patient_id'].nunique()}")

    print("\nMissing value counts (top 15):")
    missing = df.isnull().sum().sort_values(ascending=False).head(15)
    for col, count in missing.items():
        if count > 0:
            print(f"  {col}: {count} ({count/len(df)*100:.1f}%)")

    print(f"\nSample readmission rate: {df['readmitted_30day'].mean():.3f}")
    print(f"Sample mortality rate: {df['inpatient_mortality'].mean():.3f}")
    print(f"Duplicate rows: {df.duplicated().sum()}")

    print(f"\nVisits per patient distribution:")
    visits_per_patient = df.groupby("patient_id").size()
    print(f"  Mean: {visits_per_patient.mean():.2f}")
    print(f"  Max: {visits_per_patient.max()}")
    print(visits_per_patient.value_counts().sort_index().to_string())

    print(f"\nDepartment distribution:")
    print(df["department"].value_counts().head(10).to_string())

    print(f"\nInsurance distribution:")
    print(df["insurance_type"].value_counts().to_string())


def validate_schema(df: pd.DataFrame):
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        print(f"FATAL: missing expected columns: {sorted(missing)}")
        sys.exit(1)

    warn_if = [
        ("heart_rate_bpm", 30, 180),
        ("o2_saturation_pct", 70, 100),
        ("temperature_f", 94, 106),
        ("bp_systolic", 60, 220),
    ]
    for col, lo, hi in warn_if:
        s = df[col].dropna()
        bad = ((s < lo) | (s > hi)).sum()
        if bad > 0:
            print(f"  note: {col} has {bad} out-of-range values (expected: corruption layer)")
