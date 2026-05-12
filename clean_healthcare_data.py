"""
Healthcare Dataset Cleaning Script
====================================
Cleans healthcare_dataset_raw.csv and loads the result into SQL Server.

Issues addressed:
  1.  Duplicate rows
  2.  Categorical typos  (department, gender, insurance_type)
  3.  Negative / impossible vitals & charges
  4.  Impossible vital sign values (heart rate, O2 sat, temperature)
  5.  Invalid satisfaction scores
  6.  Age / DOB mismatches  -> derive age from DOB where possible
  7.  Malformed zip codes
  8.  Logical flag inconsistency (readmitted=1 but no days_to_readmission)
  9.  Date parsing & length-of-stay recomputation
  10. Sparse lab columns retained but flagged
  11. Empty strings converted to NaN across all columns
  12. Invalid discharge disposition values nulled
  13. Mortality / readmission contradiction corrected
  14. days_to_readmission clamped to 1-30 day window
  15. ed_visits_past_6mo validated as non-negative integer

Output: SQL Server table  dbo.healthcare_visits_clean
        (swap connection string for your environment)
"""

import argparse
import hashlib
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIG  –  credentials are loaded from .env (run 'make env' to create it)
# ---------------------------------------------------------------------------
INPUT_FILE = os.path.join("outputs", "healthcare_dataset_raw.csv")
SERVER = os.getenv("DB_SERVER", "")
DATABASE = os.getenv("DB_DATABASE", "")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
# ---------------------------------------------------------------------------


def load_raw(path: str) -> pd.DataFrame:
    log.info("Loading raw file: %s", path)
    df = pd.read_csv(path, dtype={"zip_code": str})
    log.info("Loaded %d rows x %d columns", *df.shape)
    return df


# ---------------------------------------------------------------------------
# 0. EMPTY STRINGS → NaN
# ---------------------------------------------------------------------------
def replace_empty_strings(df: pd.DataFrame) -> pd.DataFrame:
    """The corrupt() helper replaces values with "" instead of NaN in some fields.
    Normalise these to NaN so downstream steps treat them as missing."""
    str_cols = df.select_dtypes(include=["object", "str"]).columns
    before = {col: (df[col] == "").sum() for col in str_cols}
    df[str_cols] = df[str_cols].replace("", np.nan)
    total = sum(before.values())
    log.info(
        "Converted %d empty strings to NaN across %d columns", total, len(str_cols)
    )
    return df


# ---------------------------------------------------------------------------
# 1. DUPLICATES
# ---------------------------------------------------------------------------
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    log.info("Removed %d exact duplicate rows", before - len(df))

    # Keep first visit record where patient_id + admit_date are identical
    before = len(df)
    df = df.drop_duplicates(subset=["patient_id", "admit_date"], keep="first")
    log.info("Removed %d duplicate patient/admit-date pairs", before - len(df))
    return df


# ---------------------------------------------------------------------------
# 2. STANDARDISE CATEGORICAL COLUMNS
# ---------------------------------------------------------------------------
DEPARTMENT_MAP = {
    # Emergency variants — includes both generator-cased and all-lower forms
    "Emergancy": "Emergency",
    "emergancy": "Emergency",
    "Emrgency": "Emergency",
    "emrgency": "Emergency",
    "emergency": "Emergency",
    "EMERGENCY": "Emergency",
    "ER": "Emergency",
    # Cardiology variants
    "Cardio": "Cardiology",
    "cardio": "Cardiology",
    "Cardiolgy": "Cardiology",
    "cardiolgy": "Cardiology",
    "CARDIOLOGY": "Cardiology",
    "cardiology": "Cardiology",
}

GENDER_MAP = {
    "male": "Male",
    "MALE": "Male",
    "M": "Male",
    "male ": "Male",
    " Male": "Male",
    "female": "Female",
    "FEMALE": "Female",
    "F": "Female",
    "female ": "Female",
    " Female": "Female",
    "unknown": "Unknown",
}

INSURANCE_MAP = {
    # All variants from TYPO_VARIANTS — proper-case and all-caps forms
    "Medcare": "Medicare",
    "medcare": "Medicare",
    "Medicre": "Medicare",
    "medicre": "Medicare",
    "Medicar": "Medicare",
    "medicar": "Medicare",
    "medicare": "Medicare",
    "MEDICARE": "Medicare",
}


def standardise_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    # Department
    df["department"] = df["department"].str.strip().replace(DEPARTMENT_MAP)
    log.info(
        "Department unique values after clean: %s",
        sorted(df["department"].dropna().unique()),
    )

    # Gender
    df["gender"] = df["gender"].str.strip().replace(GENDER_MAP)
    # Anything left that isn't a known value -> Unknown
    known_genders = {"Male", "Female", "Non-binary", "Unknown"}
    df.loc[~df["gender"].isin(known_genders) & df["gender"].notna(), "gender"] = (
        "Unknown"
    )
    df["gender"] = df["gender"].fillna("Unknown")

    # Insurance type
    df["insurance_type"] = df["insurance_type"].str.strip().replace(INSURANCE_MAP)
    log.info(
        "Insurance unique values after clean: %s",
        sorted(df["insurance_type"].dropna().unique()),
    )

    return df


# ---------------------------------------------------------------------------
# 3. DATES  &  AGE / DOB RECONCILIATION
# ---------------------------------------------------------------------------
def clean_dates_and_age(df: pd.DataFrame) -> pd.DataFrame:
    df["admit_date"] = pd.to_datetime(df["admit_date"], errors="coerce")
    df["discharge_date"] = pd.to_datetime(df["discharge_date"], errors="coerce")
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce")

    # Recompute length of stay from dates (more reliable than the raw column)
    df["length_of_stay_days"] = (df["discharge_date"] - df["admit_date"]).dt.days
    # Negative LOS is impossible – null it out
    neg_los = df["length_of_stay_days"] < 0
    log.info("Nulled %d rows with negative length_of_stay_days", neg_los.sum())
    df.loc[neg_los, "length_of_stay_days"] = np.nan

    # Derive age from DOB where available; fill gaps with existing age column
    computed_age = ((df["admit_date"] - df["date_of_birth"]).dt.days / 365.25).round(0)
    df["age"] = np.where(computed_age.notna(), computed_age, df["age"])

    # Clamp age to plausible adult range (dataset is adult patients)
    implausible_age = df["age"].notna() & ((df["age"] < 0) | (df["age"] > 120))
    log.info("Nulled %d implausible age values", implausible_age.sum())
    df.loc[implausible_age, "age"] = np.nan

    # Safe Harbor: retain birth year only, drop full DOB
    df["birth_year"] = df["date_of_birth"].dt.year
    df = df.drop(columns=["date_of_birth"], errors="ignore")
    log.info("Replaced date_of_birth with birth_year")

    df["length_of_stay_days"] = df["length_of_stay_days"].astype("Int16")
    df["age"] = df["age"].astype("Int16")
    df["birth_year"] = df["birth_year"].astype("Int16")

    return df


# ---------------------------------------------------------------------------
# 4. VITALS – clamp to physiologically plausible ranges
# ---------------------------------------------------------------------------
VITALS_BOUNDS = {
    "bp_systolic": (50, 300),
    "bp_diastolic": (20, 200),
    "heart_rate_bpm": (20, 300),
    "o2_saturation_pct": (50, 100),
    "temperature_f": (90, 108),
    "bmi": (10, 80),
    "glucose_mg_dl": (20, 800),
    "creatinine_mg_dl": (0.1, 20),
    "potassium_meq_l": (1.5, 9.0),
    "sodium_meq_l": (100, 180),
    "wbc_k_ul": (0.5, 100),
    "hemoglobin_g_dl": (3.0, 22),
    "hba1c_pct": (3.0, 20),
    "lactate_mmol_l": (0.2, 30),
    "troponin_ng_ml": (0.0, 50),
}


def clean_vitals(df: pd.DataFrame) -> pd.DataFrame:
    for col, (lo, hi) in VITALS_BOUNDS.items():
        if col not in df.columns:
            continue
        out_of_range = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        log.info("%-25s  nulled %d out-of-range values", col, out_of_range.sum())
        df.loc[out_of_range, col] = np.nan
    return df


# ---------------------------------------------------------------------------
# 5. CHARGES
# ---------------------------------------------------------------------------
def clean_charges(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the gross charge field.

    Negative values are sign-flip errors, not real credits or contractual
    adjustments (those would live in separate fields in a real billing system).
    total_charges_usd is a gross-charge column that is always intended to be
    positive; negatives are produced by flipping the sign of an otherwise valid
    amount. We take abs() to recover the correct magnitude and add a boolean
    flag so downstream consumers know a correction occurred.

    Extreme outliers (> $10M) are a ×100 data-entry error — the magnitude
    itself is wrong and unrecoverable, so those are nulled.
    """
    # Sign-flip correction
    negative = df["total_charges_usd"] < 0
    df["charge_sign_corrected"] = negative.astype(int)
    df.loc[negative, "total_charges_usd"] = df.loc[negative, "total_charges_usd"].abs()
    log.info(
        "Corrected %d negative total_charges_usd values via abs() "
        "(sign-flip error; magnitude preserved); flag in 'charge_sign_corrected'",
        int(negative.sum()),
    )

    # Extreme outlier guard — ×100 inflation, magnitude unrecoverable
    extreme = df["total_charges_usd"] > 10_000_000
    log.info("Nulled %d extreme total_charges_usd values (> $10M)", extreme.sum())
    df.loc[extreme, "total_charges_usd"] = np.nan

    return df


# ---------------------------------------------------------------------------
# 6. PATIENT SATISFACTION SCORE  (valid range 1-10)
# ---------------------------------------------------------------------------
def clean_satisfaction(df: pd.DataFrame) -> pd.DataFrame:
    invalid = df["patient_satisfaction_score"].notna() & (
        (df["patient_satisfaction_score"] < 1) | (df["patient_satisfaction_score"] > 10)
    )
    log.info("Nulled %d invalid patient_satisfaction_score values", invalid.sum())
    df.loc[invalid, "patient_satisfaction_score"] = np.nan
    return df


# ---------------------------------------------------------------------------
# 7. ZIP CODES
# ---------------------------------------------------------------------------
def clean_zipcodes(df: pd.DataFrame) -> pd.DataFrame:
    # Zero-pad to 5 digits; null anything that can't form a valid 5-digit zip
    df["zip_code"] = df["zip_code"].astype(str).str.strip().str.zfill(5)
    invalid_zip = ~df["zip_code"].str.match(r"^\d{5}$")
    log.info("Nulled %d invalid zip_code values", invalid_zip.sum())
    df.loc[invalid_zip, "zip_code"] = np.nan
    # Safe Harbor: truncate to 3-digit prefix
    df["zip_code"] = df["zip_code"].str[:3]
    return df


# ---------------------------------------------------------------------------
# 8. LOGICAL FLAGS
# ---------------------------------------------------------------------------
def clean_logical_flags(df: pd.DataFrame) -> pd.DataFrame:
    # days_to_readmission should only be present when readmitted=1
    spurious = (df["readmitted_30day"] == 0) & df["days_to_readmission"].notna()
    log.info("Nulled %d spurious days_to_readmission (readmitted=0)", spurious.sum())
    df.loc[spurious, "days_to_readmission"] = np.nan

    return df


# ---------------------------------------------------------------------------
# 9. DISCHARGE DISPOSITION
# ---------------------------------------------------------------------------
VALID_DISPOSITIONS = {
    "Home",
    "Skilled Nursing Facility",
    "Home Health",
    "AMA",
    "Expired",
    "Rehab",
    "Transfer",
    "Hospice",
    "Long-term Acute Care",
}


def clean_discharge_disposition(df: pd.DataFrame) -> pd.DataFrame:
    if "discharge_disposition" not in df.columns:
        return df
    invalid = df["discharge_disposition"].notna() & ~df["discharge_disposition"].isin(
        VALID_DISPOSITIONS
    )
    log.info("Nulled %d invalid discharge_disposition values", invalid.sum())
    df.loc[invalid, "discharge_disposition"] = np.nan
    return df


# ---------------------------------------------------------------------------
# 10. MORTALITY / READMISSION CROSS-CHECKS
# ---------------------------------------------------------------------------
def clean_mortality_flags(df: pd.DataFrame) -> pd.DataFrame:
    # Dead patients cannot be readmitted within 30 days
    dead_readmitted = (df["inpatient_mortality"] == 1) & (df["readmitted_30day"] == 1)
    log.info(
        "Corrected %d rows: inpatient_mortality=1 but readmitted_30day=1",
        dead_readmitted.sum(),
    )
    df.loc[dead_readmitted, "readmitted_30day"] = 0
    df.loc[dead_readmitted, "days_to_readmission"] = np.nan
    df.loc[dead_readmitted, "readmission_days_missing"] = 0

    # Disposition must be 'Expired' when inpatient_mortality=1
    wrong_disp = (
        (df["inpatient_mortality"] == 1)
        & df["discharge_disposition"].notna()
        & (df["discharge_disposition"] != "Expired")
    )
    log.info(
        "Corrected %d discharge_disposition values: mortality=1 but not 'Expired'",
        wrong_disp.sum(),
    )
    df.loc[wrong_disp, "discharge_disposition"] = "Expired"

    return df


# ---------------------------------------------------------------------------
# 11. DAYS TO READMISSION  (30-day window)
# ---------------------------------------------------------------------------
def clean_days_to_readmission(df: pd.DataFrame) -> pd.DataFrame:
    # Values > 30 are outside the 30-day readmission window
    out_of_window = (
        (df["readmitted_30day"] == 1)
        & df["days_to_readmission"].notna()
        & (df["days_to_readmission"] > 30)
    )
    log.info("Nulled %d days_to_readmission values > 30 days", out_of_window.sum())
    df.loc[out_of_window, "days_to_readmission"] = np.nan

    # Values < 1 are also impossible (same-day readmission is not counted)
    below_min = (
        (df["readmitted_30day"] == 1)
        & df["days_to_readmission"].notna()
        & (df["days_to_readmission"] < 1)
    )
    log.info("Nulled %d days_to_readmission values < 1", below_min.sum())
    df.loc[below_min, "days_to_readmission"] = np.nan

    # Recompute flag here so it captures all nulls from every cleaning step
    flag = (df["readmitted_30day"] == 1) & df["days_to_readmission"].isna()
    df["readmission_days_missing"] = flag.astype(int)
    log.info(
        "Flagged %d rows: readmitted=1 but days_to_readmission is null", flag.sum()
    )

    df["days_to_readmission"] = df["days_to_readmission"].astype("Int8")

    return df


# ---------------------------------------------------------------------------
# 12. SOCIAL DETERMINANTS
# ---------------------------------------------------------------------------
def clean_social_determinants(df: pd.DataFrame) -> pd.DataFrame:
    if "ed_visits_past_6mo" not in df.columns:
        return df

    negative_ed = df["ed_visits_past_6mo"].notna() & (df["ed_visits_past_6mo"] < 0)
    log.info("Nulled %d negative ed_visits_past_6mo values", negative_ed.sum())
    df.loc[negative_ed, "ed_visits_past_6mo"] = np.nan

    # Poisson-generated; >20 visits in 6 months is implausible and likely an artefact
    excessive_ed = df["ed_visits_past_6mo"].notna() & (df["ed_visits_past_6mo"] > 20)
    log.info("Nulled %d excessive ed_visits_past_6mo values (>20)", excessive_ed.sum())
    df.loc[excessive_ed, "ed_visits_past_6mo"] = np.nan

    # Ensure stored as integer where non-null
    df["ed_visits_past_6mo"] = df["ed_visits_past_6mo"].astype("Int64")

    return df


# ---------------------------------------------------------------------------
# 13. COLUMN ORDERING  &  FINAL TIDY-UP
# ---------------------------------------------------------------------------
def final_tidy(df: pd.DataFrame) -> pd.DataFrame:
    # Safe Harbor: replace patient_id with a non-reversible research ID
    if "patient_id" in df.columns:
        df["research_id"] = (
            df["patient_id"]
            .astype(str)
            .apply(lambda x: hashlib.sha256(x.encode()).hexdigest()[:12])
        )
        log.info("Replaced patient_id with hashed research_id")

    pii_cols = ["first_name", "last_name", "patient_id"]
    df = df.drop(columns=pii_cols, errors="ignore")
    log.info(
        "Dropped PII columns: %s",
        [c for c in pii_cols if c in df.columns or c == "patient_id"],
    )

    # Reset index
    df = df.reset_index(drop=True)
    log.info("Final shape: %d rows x %d columns", *df.shape)
    return df


# ---------------------------------------------------------------------------
# 10. NORMALIZE AND LOAD TO SQL SERVER
# ---------------------------------------------------------------------------
def normalize_and_load(df: pd.DataFrame) -> None:
    if not SERVER or not DATABASE:
        raise EnvironmentError(
            "DB_SERVER and DB_DATABASE must be set in your .env file. "
            "Run 'make env' to create one from .env.example."
        )
    conn_str = (
        f"mssql+pyodbc://{SERVER}/{DATABASE}"
        f"?driver={DRIVER.replace(' ', '+')}"
        "&trusted_connection=yes"  # Windows auth – remove if using SQL auth
        # For SQL auth uncomment and fill:
        # f"&uid=YOUR_USERNAME&pwd=YOUR_PASSWORD"
    )
    log.info("Connecting to SQL Server: %s / %s", SERVER, DATABASE)
    engine = create_engine(conn_str, fast_executemany=True)

    # Surrogate encounter key – row order is stable after dedup + reset_index
    df = df.copy()
    df.insert(0, "encounter_id", range(1, len(df) + 1))

    tables = {
        "patients": df[
            [
                "research_id",
                "gender",
                "birth_year",
                "zip_code",
            ]
        ].drop_duplicates("research_id"),
        "encounters": df[
            [
                "encounter_id",
                "research_id",
                "admit_date",
                "discharge_date",
                "length_of_stay_days",
                "age",
                "department",
                "insurance_type",
                "total_charges_usd",
                "charge_sign_corrected",
                "discharge_disposition",
                "patient_satisfaction_score",
            ]
        ],
        "vitals": df[
            [
                "encounter_id",
                "bp_systolic",
                "bp_diastolic",
                "heart_rate_bpm",
                "o2_saturation_pct",
                "temperature_f",
                "bmi",
            ]
        ],
        "lab_results": df[
            [
                "encounter_id",
                "glucose_mg_dl",
                "creatinine_mg_dl",
                "potassium_meq_l",
                "sodium_meq_l",
                "wbc_k_ul",
                "hemoglobin_g_dl",
                "hba1c_pct",
                "lactate_mmol_l",
                "troponin_ng_ml",
            ]
        ],
        "encounter_outcomes": df[
            [
                "encounter_id",
                "readmitted_30day",
                "days_to_readmission",
                "readmission_days_missing",
                "inpatient_mortality",
            ]
        ],
        "ed_utilization": df[
            [
                "encounter_id",
                "research_id",
                "ed_visits_past_6mo",
            ]
        ],
    }

    for table_name, table_df in tables.items():
        log.info("Loading %d rows into dbo.%s ...", len(table_df), table_name)
        table_df.to_sql(
            table_name,
            engine,
            schema="dbo",
            if_exists="replace",
            index=False,
            chunksize=5000,
        )
        log.info("  dbo.%s done.", table_name)

    log.info("All tables loaded successfully.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Clean the raw healthcare dataset")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--preview",
        action="store_true",
        help="Save a 1,000-row CSV sample for inspection",
    )
    group.add_argument(
        "--load-sql",
        action="store_true",
        dest="load_sql",
        help=(
            "Write full CSV then normalize and bulk-load into SQL Server "
            "(requires SERVER and DATABASE to be set at the top of this file)"
        ),
    )
    args = parser.parse_args()

    df = load_raw(INPUT_FILE)

    df = replace_empty_strings(df)
    df = remove_duplicates(df)
    df = standardise_categoricals(df)
    df = clean_dates_and_age(df)
    df = clean_vitals(df)
    df = clean_charges(df)
    df = clean_satisfaction(df)
    df = clean_zipcodes(df)
    df = clean_logical_flags(df)
    df = clean_discharge_disposition(df)
    df = clean_mortality_flags(df)
    df = clean_days_to_readmission(df)
    df = clean_social_determinants(df)
    df = final_tidy(df)

    if args.preview:
        preview_path = os.path.join("outputs", "healthcare_cleaned_preview.csv")
        df.head(1000).to_csv(preview_path, index=False)
        log.info("Saved 1,000-row preview to %s", preview_path)
    elif args.load_sql:
        full_path = os.path.join("outputs", "healthcare_cleaned_full.csv")
        df.to_csv(full_path, index=False)
        log.info("Saved full cleaned CSV to %s", full_path)
        normalize_and_load(df)
    else:
        full_path = os.path.join("outputs", "healthcare_cleaned_full.csv")
        df.to_csv(full_path, index=False)
        log.info("Saved full cleaned CSV to %s", full_path)


if __name__ == "__main__":
    main()
