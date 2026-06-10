import random
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np

from .reference_data import COMORBIDITIES, DEPARTMENTS, DIAGNOSES


@lru_cache(maxsize=None)
def get_seasonal_weight(month: int, dx_code: str) -> float:
    dx_info = DIAGNOSES.get(dx_code, {})
    if not dx_info.get("seasonal", False):
        return 1.0

    peak_months = dx_info.get("peak_months", [])

    if month in peak_months:
        return 1.8
    elif (month % 12 + 1) in peak_months or (month - 1) % 12 in peak_months:
        return 1.3
    return 0.6


def select_diagnosis_for_date(admit_date: datetime) -> str:
    dx_codes = list(DIAGNOSES.keys())
    month = admit_date.month

    adjusted_weights = [get_seasonal_weight(month, code) for code in dx_codes]

    total = sum(adjusted_weights)
    probs = [w / total for w in adjusted_weights]

    return np.random.choice(dx_codes, p=probs)


def get_department_for_diagnosis(dx_code: str) -> str:
    dx_info = DIAGNOSES.get(dx_code, {})
    valid_depts = dx_info.get("depts", DEPARTMENTS)
    return random.choice(valid_depts)


def generate_secondary_diagnoses(primary_dx: str) -> List[str]:
    secondary = []

    if primary_dx in COMORBIDITIES:
        for dx, prob in COMORBIDITIES[primary_dx]:
            if random.random() < prob:
                secondary.append(dx)

    if random.random() < 0.3:
        other_dx = random.choice(
            [d for d in DIAGNOSES.keys() if d != primary_dx and d not in secondary]
        )
        secondary.append(other_dx)

    return secondary[:3]


def generate_vitals(age: int, dx_code: str, dept: str) -> Dict[str, Optional[float]]:
    bp_sys_base = 120 + (age - 40) * 0.3
    bp_dia_base = 75 + (age - 40) * 0.15
    hr_base = 78 - (age - 50) * 0.1
    o2_base = 97 - (age - 50) * 0.03
    temp_base = 98.4

    if dx_code == "I10":
        bp_sys_base += 25
        bp_dia_base += 15

    if dx_code in ["A41.9", "A41.51"]:
        hr_base += 30
        temp_base += 2.5
        bp_sys_base -= 25
        o2_base -= 4

    if dx_code in ["J44.1", "J18.9", "J18.1", "J44.0"]:
        o2_base -= 5
        hr_base += 10

    if dx_code in ["I21.9", "I21.3"]:
        hr_base += 15
        bp_sys_base += 10

    if dx_code in ["I50.9", "I50.20", "I50.22", "I50.30"]:
        o2_base -= 3
        hr_base += 8

    vm = 1.5 if dept == "ICU" else 1.0

    raw = np.random.normal(
        [bp_sys_base, bp_dia_base, hr_base, o2_base, temp_base],
        [18 * vm, 10 * vm, 14 * vm, 2.5 * vm, 0.9 * vm],
    )

    bp_sys = int(max(60, min(220, raw[0])))
    bp_dia = int(max(40, min(140, raw[1])))

    if bp_dia >= bp_sys:
        bp_dia = bp_sys - random.randint(20, 40)

    hr = int(max(30, min(180, raw[2])))
    o2 = round(float(max(70.0, min(100.0, raw[3]))), 1)
    temp = round(float(max(94.0, min(106.0, raw[4]))), 1)

    return {
        "bp_systolic": bp_sys,
        "bp_diastolic": bp_dia,
        "heart_rate_bpm": hr,
        "o2_saturation_pct": o2,
        "temperature_f": temp,
    }


def generate_bmi(age: int) -> float:
    base = 27 + (age - 40) * 0.05
    val = round(np.random.normal(base, 5.5), 1)
    return max(14.0, min(65.0, val))


def generate_lab_results(dx_code: str, age: int) -> Dict[str, Optional[float]]:
    labs = {}

    raw = np.random.normal(
        [100, 1.0, 4.0, 140, 7.5, 13.5],
        [25, 0.3, 0.4, 3, 2.5, 1.8],
    )
    labs["glucose_mg_dl"] = int(raw[0])
    labs["creatinine_mg_dl"] = round(float(raw[1]), 2)
    labs["potassium_meq_l"] = round(float(raw[2]), 1)
    labs["sodium_meq_l"] = int(raw[3])
    labs["wbc_k_ul"] = round(float(raw[4]), 1)
    labs["hemoglobin_g_dl"] = round(float(raw[5]), 1)

    if dx_code in ["E11.9", "E11.65"]:
        labs["glucose_mg_dl"] = int(np.random.normal(180, 60))
        labs["hba1c_pct"] = round(np.random.normal(8.5, 1.5), 1)

    if dx_code == "N18.6":
        labs["creatinine_mg_dl"] = round(np.random.normal(6.0, 2.0), 2)
        labs["potassium_meq_l"] = round(np.random.normal(5.2, 0.6), 1)
        labs["hemoglobin_g_dl"] = round(np.random.normal(10.0, 1.5), 1)

    if dx_code == "N17.9":
        labs["creatinine_mg_dl"] = round(np.random.normal(3.5, 1.2), 2)
        labs["potassium_meq_l"] = round(np.random.normal(5.0, 0.7), 1)

    if dx_code in ["A41.9", "A41.51"]:
        labs["wbc_k_ul"] = round(np.random.lognormal(2.5, 0.5), 1)
        labs["lactate_mmol_l"] = round(np.random.normal(4.0, 2.0), 1)

    if dx_code in ["K92.1", "D64.9"]:
        labs["hemoglobin_g_dl"] = round(np.random.normal(8.0, 2.0), 1)

    if dx_code in ["I21.9", "I21.3"]:
        mean_log = 0 if dx_code == "I21.3" else -1
        labs["troponin_ng_ml"] = round(np.random.lognormal(mean_log, 1.5), 3)

    if dx_code == "E87.6":
        labs["potassium_meq_l"] = round(np.random.normal(2.8, 0.4), 1)

    labs["glucose_mg_dl"] = max(40, min(600, labs["glucose_mg_dl"]))
    labs["creatinine_mg_dl"] = max(0.3, min(15.0, labs["creatinine_mg_dl"]))
    labs["potassium_meq_l"] = max(2.0, min(7.0, labs["potassium_meq_l"]))
    labs["sodium_meq_l"] = max(120, min(160, labs["sodium_meq_l"]))
    labs["wbc_k_ul"] = max(0.5, min(50.0, labs["wbc_k_ul"]))
    labs["hemoglobin_g_dl"] = max(4.0, min(20.0, labs["hemoglobin_g_dl"]))

    return labs
