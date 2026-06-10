import argparse
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUTS = os.path.join(_PROJECT_ROOT, "outputs")

CONFIG = {
    "n_patients": 340000,
    "seed": 42,
    "date_range": ("2019-01-01", "2024-12-31"),
    "corruption": {
        "missing_rate": 0.04,
        "typo_rate": 0.02,
        "impossible_value_rate": 0.01,
        "swapped_field_rate": 0.005,
        "duplicate_patient_rate": 0.009,
        "invalid_icd_code_rate": 0.06,
    },
    "multi_visit": {
        "enabled": True,
        "visit_distribution": [0.70, 0.18, 0.08, 0.04],
    },
    "include_lab_results": True,
    "include_medications": True,
    "include_social_determinants": True,
    "include_procedures": True,
    "output_path": os.path.join(_OUTPUTS, "healthcare_dataset_raw.csv"),
    "report_path": os.path.join(_OUTPUTS, "data_quality_report.txt"),
    "n_cores": 1,
    "output_format": "csv",
    "verbose": True,
}


def build_arg_parser():
    p = argparse.ArgumentParser(description="Generate synthetic healthcare dataset")
    p.add_argument("--n-patients", type=int, default=CONFIG["n_patients"])
    p.add_argument("--seed", type=int, default=CONFIG["seed"])
    p.add_argument("--output", default=CONFIG["output_path"])
    p.add_argument("--report", default=CONFIG["report_path"])
    p.add_argument(
        "--cores",
        type=int,
        default=os.cpu_count() or 1,
        help="Worker processes (1 = serial, >1 = parallel; default: auto-detected CPU count)",
    )
    p.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default=CONFIG["output_format"],
        help="Output format (parquet is faster and smaller)",
    )
    p.add_argument(
        "--no-verbose",
        dest="verbose",
        action="store_false",
        help="Skip dataset summary and schema validation after generation",
    )
    p.set_defaults(verbose=CONFIG["verbose"])
    return p


def apply_cli_overrides(args):
    CONFIG["n_patients"] = args.n_patients
    CONFIG["seed"] = args.seed
    CONFIG["output_path"] = args.output
    CONFIG["report_path"] = args.report
    max_cores = os.cpu_count() or 1
    CONFIG["n_cores"] = max(1, min(args.cores, max_cores))
    CONFIG["output_format"] = args.format
    CONFIG["verbose"] = args.verbose
