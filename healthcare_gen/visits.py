import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .clinical import (
    generate_bmi,
    generate_lab_results,
    generate_secondary_diagnoses,
    generate_vitals,
    get_department_for_diagnosis,
    select_diagnosis_for_date,
)
from .config import CONFIG
from .corruption import DataQualityTracker, add_typo, corrupt
from .demographics import generate_social_determinants
from .reference_data import (
    ADMIT_TYPE_WEIGHTS,
    ADMIT_TYPES,
    DIAGNOSES,
    DISCHARGE_DISPOSITIONS,
    MEDICATIONS,
    PROCEDURES,
)

_START_DATE = datetime.strptime(CONFIG["date_range"][0], "%Y-%m-%d")
_END_DATE = datetime.strptime(CONFIG["date_range"][1], "%Y-%m-%d")


def generate_procedures(dept: str, los: float) -> List[Tuple[str, str, float]]:
    if dept not in PROCEDURES:
        return []

    available = PROCEDURES[dept]
    n_procedures = int(np.random.poisson(1 + los * 0.2))
    n_procedures = min(n_procedures, len(available), 5)

    if n_procedures == 0:
        return []

    return random.sample(available, n_procedures)


def generate_medications(dx_code: str, secondary_dx: List[str]) -> List[str]:
    meds = []

    if dx_code in MEDICATIONS:
        n_meds = random.randint(1, min(3, len(MEDICATIONS[dx_code])))
        meds.extend(random.sample(MEDICATIONS[dx_code], n_meds))

    for sec_dx in secondary_dx:
        if sec_dx in MEDICATIONS and random.random() < 0.6:
            meds.append(random.choice(MEDICATIONS[sec_dx]))

    if random.random() < 0.3:
        meds.append(random.choice(["Acetaminophen", "Ibuprofen", "Ondansetron"]))

    return list(set(meds))[:8]


def generate_charges(
    dept: str, los: float, admit_type: str, procedures: List[Tuple[str, str, float]]
) -> float:
    base_rates = {
        "Emergency": 4500,
        "Cardiology": 8000,
        "Orthopedics": 9000,
        "Oncology": 12000,
        "Neurology": 7000,
        "General Surgery": 10000,
        "Internal Medicine": 5000,
        "Pediatrics": 4000,
        "OB/GYN": 6000,
        "Pulmonology": 6500,
        "Nephrology": 7000,
        "Psychiatry": 4500,
        "ICU": 15000,
        "Radiology": 3000,
    }

    base = base_rates.get(dept, 5000)
    daily_charge = base * (1 + los * 0.3 - los * 0.005)
    procedure_costs = sum(p[2] for p in procedures) if procedures else 0
    total = (daily_charge + procedure_costs) * np.random.lognormal(0, 0.3)

    if admit_type == "Emergency":
        total *= 1.25
    elif admit_type == "Trauma":
        total *= 1.40

    return round(total, 2)


def calculate_readmit_risk(
    age: int, dx_code: str, insurance: str, los: float, has_pcp: bool
) -> float:
    dx_info = DIAGNOSES.get(dx_code, {})
    severity = dx_info.get("severity", "low")

    risk = 0.08

    if age > 65:
        risk += 0.06
    if age > 80:
        risk += 0.05

    severity_adj = {"low": 0, "medium": 0.03, "high": 0.08, "critical": 0.12}
    risk += severity_adj.get(severity, 0)

    if dx_code in ["I50.9", "A41.9", "N18.6", "J44.1"]:
        risk += 0.08

    if insurance == "Uninsured":
        risk += 0.10
    elif insurance == "Medicaid":
        risk += 0.05

    if los < 2:
        risk += 0.04
    elif los > 14:
        risk += 0.06

    if not has_pcp:
        risk += 0.05

    return min(risk, 0.60)


def calculate_mortality_risk(age: int, dx_code: str, dept: str) -> float:
    dx_info = DIAGNOSES.get(dx_code, {})
    severity = dx_info.get("severity", "low")

    risk = 0.01

    if age > 70:
        risk += 0.02
    if age > 85:
        risk += 0.04

    severity_adj = {"low": 0, "medium": 0.01, "high": 0.04, "critical": 0.10}
    risk += severity_adj.get(severity, 0)

    if dept == "ICU":
        risk += 0.05

    return min(risk, 0.25)


def _pick_readmission_dx(primary_dx: str, secondary_dx_str: str) -> str:
    r = random.random()
    if r < 0.60:
        return primary_dx
    elif r < 0.90:
        secondary = [c for c in secondary_dx_str.split("|") if c and c in DIAGNOSES]
        if secondary:
            return random.choice(secondary)
        return primary_dx
    else:
        return random.choice(list(DIAGNOSES.keys()))


def generate_visit(
    patient_id: str,
    demographics: Dict,
    visit_num: int,
    prev_discharge: Optional[datetime],
    tracker: DataQualityTracker,
    row_idx: int,
    force_no_readmit: bool = False,
    admit_date_override: Optional[datetime] = None,
    override_dx: Optional[str] = None,
) -> Optional[Tuple[Dict[str, Any], datetime]]:
    start_date = _START_DATE
    end_date = _END_DATE

    if admit_date_override is not None:
        if admit_date_override >= end_date:
            return None
        admit_date = admit_date_override
    else:
        if prev_discharge:
            start_date = max(
                start_date, prev_discharge + timedelta(days=random.randint(30, 365))
            )

        if start_date >= end_date:
            return None

        admit_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days)
        )

    admit_type = np.random.choice(ADMIT_TYPES, p=ADMIT_TYPE_WEIGHTS)

    if admit_type == "Elective" and admit_date.weekday() >= 5:
        if random.random() < 0.7:
            days_to_monday = (7 - admit_date.weekday()) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            admit_date = admit_date + timedelta(days=random.randint(1, days_to_monday))

    if admit_type in ["Emergency", "Trauma"]:
        admit_hour = int(np.random.normal(18, 5)) % 24
    else:
        admit_hour = random.choice(range(6, 16))

    primary_dx = (
        override_dx
        if override_dx is not None
        else select_diagnosis_for_date(admit_date)
    )
    secondary_dx = generate_secondary_diagnoses(primary_dx)

    dept = get_department_for_diagnosis(primary_dx)
    dept = add_typo(dept, tracker=tracker, row_idx=row_idx)

    dx_info = DIAGNOSES.get(primary_dx, {})
    severity = dx_info.get("severity", "low")

    los_means = {"low": 2.5, "medium": 4.0, "high": 7.0, "critical": 12.0}
    los_base = np.random.exponential(scale=los_means.get(severity, 3.5))
    los = round(max(0.5, min(60.0, los_base)), 1)

    if random.random() < 0.015:
        los = round(random.uniform(30, 120), 1)
        tracker.record("los_outlier", f"{los} days", row_idx)

    discharge_date = admit_date + timedelta(days=los)

    if random.random() < CONFIG["corruption"]["swapped_field_rate"]:
        discharge_date = admit_date - timedelta(days=random.randint(1, 5))
        tracker.record(
            "discharge_before_admit",
            f"Admit: {admit_date.date()}, Discharge: {discharge_date.date()}",
            row_idx,
        )

    age = demographics.get("age")
    if pd.isna(age):
        age = 50
    else:
        age = int(age)

    vitals = generate_vitals(age, primary_dx, dept)
    bmi = generate_bmi(age)

    procedures = generate_procedures(dept, los) if CONFIG["include_procedures"] else []
    medications = (
        generate_medications(primary_dx, secondary_dx)
        if CONFIG["include_medications"]
        else []
    )

    charges = generate_charges(dept, los, admit_type, procedures)

    if random.random() < 0.02:
        charges = round(charges * 100, 2)
        tracker.record("charge_data_entry_error", f"${charges:,.2f}", row_idx)
    if random.random() < 0.015:
        charges = -abs(charges)
        tracker.record("negative_charge", f"${charges:,.2f}", row_idx)

    insurance = demographics.get("insurance_type", "Private")
    social = (
        generate_social_determinants(age, insurance)
        if CONFIG["include_social_determinants"]
        else {}
    )

    has_pcp = social.get("has_pcp", True)

    if force_no_readmit:
        readmitted = 0
        days_to_readmit = np.nan
    else:
        readmit_risk = calculate_readmit_risk(age, primary_dx, insurance, los, has_pcp)
        readmitted = int(random.random() < readmit_risk)
        days_to_readmit = np.nan
        if readmitted:
            days_to_readmit = max(1, round(np.random.exponential(12)))
            days_to_readmit = corrupt(
                days_to_readmit,
                0.08,
                tracker=tracker,
                issue_type="missing_readmit_days",
                row_idx=row_idx,
            )

    mortality_risk = calculate_mortality_risk(age, primary_dx, dept)
    mortality = int(random.random() < mortality_risk)

    if mortality:
        disposition = "Expired"
    else:
        disp_weights = [0.50, 0.15, 0.12, 0.04, 0.0, 0.07, 0.05, 0.03, 0.04]
        disposition = np.random.choice(DISCHARGE_DISPOSITIONS, p=disp_weights)
    disposition = corrupt(
        disposition,
        0.04,
        "",
        tracker=tracker,
        issue_type="missing_disposition",
        row_idx=row_idx,
    )

    sat_score = np.nan
    if random.random() > 0.20:
        sat_score = round(np.random.normal(7.8, 1.8))
        sat_score = max(1, min(10, sat_score))

        if random.random() < 0.02:
            sat_score = random.choice([0, 11, 99, -1])
            tracker.record("invalid_satisfaction_score", f"{sat_score}", row_idx)

    labs = (
        generate_lab_results(primary_dx, age) if CONFIG["include_lab_results"] else {}
    )

    provider_id = f"MD{random.randint(1, 200):04d}"
    provider_id = corrupt(
        provider_id,
        0.05,
        "",
        tracker=tracker,
        issue_type="missing_provider",
        row_idx=row_idx,
    )

    for vital_key in vitals:
        vitals[vital_key] = corrupt(
            vitals[vital_key],
            0.06,
            tracker=tracker,
            issue_type=f"missing_{vital_key}",
            row_idx=row_idx,
        )

    if random.random() < CONFIG["corruption"]["impossible_value_rate"]:
        impossible_vital = random.choice(list(vitals.keys()))
        if impossible_vital == "o2_saturation_pct":
            vitals[impossible_vital] = random.choice([150, -5, 999])
        elif impossible_vital == "heart_rate_bpm":
            vitals[impossible_vital] = random.choice([0, 500, -10])
        elif impossible_vital == "temperature_f":
            vitals[impossible_vital] = random.choice([50, 150, 0])
        tracker.record(
            "impossible_vital_value",
            f"{impossible_vital}={vitals[impossible_vital]}",
            row_idx,
        )

    row = {
        **demographics,
        "visit_number": visit_num,
        "admit_date": admit_date.strftime("%Y-%m-%d"),
        "admit_time": f"{admit_hour:02d}:{random.randint(0,59):02d}",
        "discharge_date": discharge_date.strftime("%Y-%m-%d"),
        "length_of_stay_days": corrupt(
            los, 0.03, tracker=tracker, issue_type="missing_los", row_idx=row_idx
        ),
        "department": dept,
        "admit_type": admit_type,
        "primary_dx_code": primary_dx,
        "primary_dx_description": corrupt(
            DIAGNOSES[primary_dx]["desc"],
            0.03,
            "",
            tracker=tracker,
            issue_type="missing_dx_desc",
            row_idx=row_idx,
        ),
        "secondary_dx_codes": "|".join(secondary_dx) if secondary_dx else "",
        "procedure_codes": "|".join([p[0] for p in procedures]) if procedures else "",
        "procedure_descriptions": (
            "|".join([p[1] for p in procedures]) if procedures else ""
        ),
        "medications": "|".join(medications) if medications else "",
        "attending_provider_id": provider_id,
        **vitals,
        "bmi": corrupt(
            bmi, 0.08, tracker=tracker, issue_type="missing_bmi", row_idx=row_idx
        ),
        "total_charges_usd": corrupt(
            charges,
            0.04,
            tracker=tracker,
            issue_type="missing_charges",
            row_idx=row_idx,
        ),
        "readmitted_30day": readmitted,
        "days_to_readmission": days_to_readmit,
        "discharge_disposition": disposition,
        "patient_satisfaction_score": sat_score,
        "inpatient_mortality": mortality,
    }

    if social:
        row["has_pcp"] = social.get("has_pcp")
        row["lives_alone"] = social.get("lives_alone")
        row["has_transportation"] = social.get("has_transportation")
        row["ed_visits_past_6mo"] = social.get("ed_visits_6mo")

    for lab_key, lab_val in labs.items():
        row[lab_key] = corrupt(
            lab_val,
            0.10,
            tracker=tracker,
            issue_type=f"missing_{lab_key}",
            row_idx=row_idx,
        )

    return row, discharge_date
