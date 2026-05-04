import random
from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np

from .config import CONFIG
from .corruption import DataQualityTracker, corrupt, add_typo
from .reference_data import (
    FIRST_NAMES,
    GENDERS,
    INSURANCE_TYPES,
    INSURANCE_WEIGHTS,
    LAST_NAMES,
    RACES,
    RACE_WEIGHTS,
    STATES,
)


def generate_patient_demographics(
    patient_id: str, tracker: DataQualityTracker, row_idx: int
) -> Dict[str, Any]:
    age_pool = (
        list(range(18, 40))
        + list(range(40, 60)) * 2
        + list(range(60, 85)) * 4
        + list(range(85, 100))
    )
    age = random.choice(age_pool)

    base_date = datetime(2025, 1, 1) - timedelta(
        days=age * 365 + random.randint(0, 364)
    )
    dob = base_date.strftime("%Y-%m-%d")

    if random.random() < 0.03:
        dob = random.choice(["", "N/A", "Unknown", "1900-01-01"])
        tracker.record("invalid_dob", f"Patient {patient_id}", row_idx)

    gender = random.choice(GENDERS["valid"])
    if random.random() < CONFIG["corruption"]["typo_rate"]:
        gender = random.choice(GENDERS["typos"])
        tracker.record("gender_format_inconsistency", f"'{gender}'", row_idx)

    race = np.random.choice(RACES, p=RACE_WEIGHTS)
    race = corrupt(
        race, 0.05, tracker=tracker, issue_type="missing_race", row_idx=row_idx
    )

    insurance = np.random.choice(INSURANCE_TYPES, p=INSURANCE_WEIGHTS)
    insurance = add_typo(insurance, tracker=tracker, row_idx=row_idx)

    zip_code = f"{random.randint(27000, 99999):05d}"
    if random.random() < 0.03:
        zip_code = random.choice(["N/A", "", "0000", "99999", "XXXXX"])
        tracker.record("invalid_zip", f"Patient {patient_id}", row_idx)

    return {
        "patient_id": patient_id,
        "first_name": random.choice(FIRST_NAMES),
        "last_name": random.choice(LAST_NAMES),
        "date_of_birth": dob,
        "age": corrupt(
            age, 0.03, tracker=tracker, issue_type="missing_age", row_idx=row_idx
        ),
        "gender": gender,
        "race_ethnicity": race,
        "state": random.choice(STATES),
        "zip_code": zip_code,
        "insurance_type": insurance,
    }


def generate_social_determinants(age: int, insurance: str) -> Dict[str, Any]:
    pcp_probs = {
        "Private": 0.85,
        "Medicare": 0.80,
        "Tricare": 0.75,
        "VA": 0.70,
        "Medicaid": 0.50,
        "Worker's Comp": 0.60,
        "Uninsured": 0.25,
    }
    has_pcp = random.random() < pcp_probs.get(insurance, 0.5)

    if age > 75:
        lives_alone = random.random() < 0.35
    else:
        lives_alone = random.random() < 0.15

    transport_probs = {
        "Private": 0.95,
        "Medicare": 0.70,
        "Medicaid": 0.55,
        "Uninsured": 0.50,
    }
    has_transportation = random.random() < transport_probs.get(insurance, 0.7)

    if insurance in ["Uninsured", "Medicaid"]:
        ed_visits = int(np.random.poisson(1.5))
    else:
        ed_visits = int(np.random.poisson(0.5))

    return {
        "has_pcp": has_pcp,
        "lives_alone": lives_alone,
        "has_transportation": has_transportation,
        "ed_visits_6mo": ed_visits,
    }
