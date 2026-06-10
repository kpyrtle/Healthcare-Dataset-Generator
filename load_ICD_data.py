"""
load_data.py
============
Loads healthcare_trimmed.csv into the ICD10_DRG_Analysis SQL Server database.

What this script does:
  1. Reads healthcare_trimmed.csv
  2. Generates surrogate patient IDs (de-identified)
  3. Inserts dim_patients
  4. Inserts fact_encounters
  5. Unpacks pipe-delimited secondary_dx_codes → dim_diagnoses
  6. Unpacks pipe-delimited procedure_codes   → dim_procedures
  7. Inserts dim_vitals

Run from the folder containing healthcare_trimmed.csv:
  python load_data.py

Requirements:
  pip install pyodbc pandas
"""

import pyodbc
import pandas as pd
import math
import re
from pathlib import Path

# ------------------------------------------------------------
# CONFIG — update CSV_PATH if your file is in a different folder
# ------------------------------------------------------------
SERVER   = "DOODELY"
DATABASE = "ICD10_DRG_Analysis"
CSV_PATH = Path("healthcare_trimmed.csv")

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def none_if_nan(val):
    """Convert float NaN / empty string to None (SQL NULL)."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, str) and val.strip() == "":
        return None
    return val

def clean_int(val):
    """Convert float like 65.0 → 65, NaN → None."""
    v = none_if_nan(val)
    if v is None:
        return None
    return int(float(v))

def clean_zip(val):
    """
    Zip codes came in as floats (845.0, 393.0).
    Convert to zero-padded 5-char string: 845 → '00845'.
    NaN → None.
    """
    v = none_if_nan(val)
    if v is None:
        return None
    return str(int(float(v))).zfill(5)

def split_pipe(val):
    """
    Split a pipe-delimited string into a list of stripped codes.
    Returns [] if val is None / NaN.
    """
    v = none_if_nan(val)
    if v is None:
        return []
    return [c.strip() for c in str(v).split("|") if c.strip()]


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    print("=" * 60)
    print("ICD-10 / MS-DRG — Database Load Script")
    print("=" * 60)

    # ----------------------------------------------------------
    # 1. Load CSV
    # ----------------------------------------------------------
    print(f"\n[1/6] Reading {CSV_PATH} ...")
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. "
            "Make sure load_data.py is in the same folder as healthcare_trimmed.csv."
        )
    df = pd.read_csv(CSV_PATH)
    print(f"      {len(df):,} rows, {len(df.columns)} columns loaded.")

    # ----------------------------------------------------------
    # 2. Connect to SQL Server
    # ----------------------------------------------------------
    print(f"\n[2/6] Connecting to {SERVER} / {DATABASE} ...")
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        print("      Connected.")
    except pyodbc.Error as e:
        print(f"\n  ERROR: Could not connect to SQL Server.\n  {e}")
        print(
            "\n  Check that:\n"
            "  - SSMS is open and the DOODELY instance is running\n"
            "  - The database ICD10_DRG_Analysis exists\n"
            "  - The schema script has been run\n"
        )
        raise

    # ----------------------------------------------------------
    # 3. dim_patients
    #    Build a unique patient lookup from the flat CSV.
    #    The CSV has no true patient ID — we group by a
    #    demographic fingerprint and assign a surrogate key.
    # ----------------------------------------------------------
    print("\n[3/6] Inserting dim_patients ...")

    # Build one representative row per unique patient fingerprint
    patient_cols = ["age", "gender", "race_ethnicity", "state",
                    "zip_code", "insurance_type", "visit_number"]
    pat_df = df[patient_cols].drop_duplicates().reset_index(drop=True)
    pat_df["surrogate_patient_id"] = range(1, len(pat_df) + 1)

    # Merge surrogate IDs back onto main df for FK use in encounters
    df = df.merge(pat_df, on=patient_cols, how="left")

    insert_patient = """
        INSERT INTO dim_patients
            (age, gender, race_ethnicity, state, zip_code,
             insurance_type, visits_in_dataset)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    patient_rows = []
    for _, row in pat_df.iterrows():
        patient_rows.append((
            clean_int(row["age"]),
            none_if_nan(row["gender"]),
            none_if_nan(row["race_ethnicity"]),
            none_if_nan(row["state"]),
            clean_zip(row["zip_code"]),
            none_if_nan(row["insurance_type"]),
            clean_int(row["visit_number"]),
        ))

    cursor.executemany(insert_patient, patient_rows)
    conn.commit()
    print(f"      {len(patient_rows):,} patients inserted.")

    # Fetch back the generated patient_id IDENTITY values
    cursor.execute("SELECT patient_id, age, gender, insurance_type, zip_code FROM dim_patients")
    db_patients = cursor.fetchall()

    # Build a lookup: surrogate_patient_id → database patient_id
    # Match on age + gender + insurance_type + zip (enough to be unique per fingerprint)
    pat_lookup = {}
    for db_pid, db_age, db_gender, db_ins, db_zip in db_patients:
        key = (db_age, db_gender, db_ins, db_zip)
        pat_lookup[key] = db_pid

    def get_patient_id(row):
        key = (
            clean_int(row["age"]),
            none_if_nan(row["gender"]),
            none_if_nan(row["insurance_type"]),
            clean_zip(row["zip_code"]),
        )
        return pat_lookup.get(key)

    # ----------------------------------------------------------
    # 4. fact_encounters
    # ----------------------------------------------------------
    print("\n[4/6] Inserting fact_encounters ...")

    insert_encounter = """
        INSERT INTO fact_encounters
            (patient_id, admit_date, discharge_date, length_of_stay_days,
             department, admit_type, primary_dx_code, primary_dx_description,
             total_charges_usd, discharge_disposition, readmitted_30day,
             days_to_readmission, inpatient_mortality)
        OUTPUT INSERTED.encounter_id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # We need the generated encounter_id back for child table FKs
    encounter_ids = []
    enc_rows_for_children = []  # store (encounter_id, row) for later

    for _, row in df.iterrows():
        pid = get_patient_id(row)
        params = (
            pid,
            none_if_nan(row["admit_date"]),
            none_if_nan(row["discharge_date"]),
            none_if_nan(row["length_of_stay_days"]),
            none_if_nan(row["department"]),
            none_if_nan(row["admit_type"]),
            none_if_nan(row["primary_dx_code"]),
            none_if_nan(row["primary_dx_description"]),
            none_if_nan(row["total_charges_usd"]),
            none_if_nan(row["discharge_disposition"]),
            int(row["readmitted_30day"]) if none_if_nan(row["readmitted_30day"]) is not None else 0,
            clean_int(row["days_to_readmission"]),
            int(row["inpatient_mortality"]) if none_if_nan(row["inpatient_mortality"]) is not None else 0,
        )
        cursor.execute(insert_encounter, params)
        enc_id = cursor.fetchone()[0]
        encounter_ids.append(enc_id)
        enc_rows_for_children.append((enc_id, row))

    conn.commit()
    print(f"      {len(encounter_ids):,} encounters inserted.")

    # ----------------------------------------------------------
    # 5. dim_diagnoses
    #    Principal dx from primary_dx_code (sequence 1)
    #    Secondary dx unpacked from pipe-delimited secondary_dx_codes
    # ----------------------------------------------------------
    print("\n[5/6] Inserting dim_diagnoses ...")

    insert_dx = """
        INSERT INTO dim_diagnoses
            (encounter_id, dx_sequence, dx_type, icd10_cm_code, dx_description)
        VALUES (?, ?, ?, ?, ?)
    """
    dx_rows = []
    for enc_id, row in enc_rows_for_children:
        # Principal diagnosis
        pdx = none_if_nan(row["primary_dx_code"])
        if pdx:
            dx_rows.append((
                enc_id, 1, "Principal", pdx,
                none_if_nan(row["primary_dx_description"])
            ))
        # Secondary diagnoses
        secondary = split_pipe(row["secondary_dx_codes"])
        for seq, code in enumerate(secondary, start=2):
            dx_rows.append((enc_id, seq, "Secondary", code, None))

    cursor.executemany(insert_dx, dx_rows)
    conn.commit()
    print(f"      {len(dx_rows):,} diagnosis rows inserted.")

    # ----------------------------------------------------------
    # 6. dim_procedures
    #    Unpacked from pipe-delimited procedure_codes
    # ----------------------------------------------------------
    print("\n[6/6] Inserting dim_procedures ...")

    insert_proc = """
        INSERT INTO dim_procedures
            (encounter_id, proc_sequence, proc_type, cpt_code, proc_description)
        VALUES (?, ?, ?, ?, ?)
    """
    proc_rows = []
    for enc_id, row in enc_rows_for_children:
        codes = split_pipe(row["procedure_codes"])
        for seq, code in enumerate(codes, start=1):
            ptype = "Principal" if seq == 1 else "Secondary"
            proc_rows.append((enc_id, seq, ptype, code, None))

    if proc_rows:
        cursor.executemany(insert_proc, proc_rows)
        conn.commit()
    print(f"      {len(proc_rows):,} procedure rows inserted.")

    # ----------------------------------------------------------
    # 7. dim_vitals
    # ----------------------------------------------------------
    print("\n[7/7] Inserting dim_vitals ...")

    insert_vitals = """
        INSERT INTO dim_vitals
            (encounter_id, bp_systolic, bp_diastolic, o2_saturation_pct,
             bmi, creatinine_mg_dl, hba1c_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    vitals_rows = []
    for enc_id, row in enc_rows_for_children:
        vitals_rows.append((
            enc_id,
            clean_int(row["bp_systolic"]),
            clean_int(row["bp_diastolic"]),
            none_if_nan(row["o2_saturation_pct"]),
            none_if_nan(row["bmi"]),
            none_if_nan(row["creatinine_mg_dl"]),
            none_if_nan(row["hba1c_pct"]),
        ))

    cursor.executemany(insert_vitals, vitals_rows)
    conn.commit()
    print(f"      {len(vitals_rows):,} vitals rows inserted.")

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    cursor.execute("""
        SELECT 'dim_patients'    AS tbl, COUNT(*) AS rows FROM dim_patients
        UNION ALL SELECT 'fact_encounters',  COUNT(*) FROM fact_encounters
        UNION ALL SELECT 'dim_diagnoses',    COUNT(*) FROM dim_diagnoses
        UNION ALL SELECT 'dim_procedures',   COUNT(*) FROM dim_procedures
        UNION ALL SELECT 'dim_vitals',       COUNT(*) FROM dim_vitals
    """)
    print("\n--- Row count verification ---")
    for tbl, cnt in cursor.fetchall():
        print(f"  {tbl:<22} {cnt:>6,} rows")

    cursor.close()
    conn.close()
    print("\nDone. Database loaded successfully.")


if __name__ == "__main__":
    main()
