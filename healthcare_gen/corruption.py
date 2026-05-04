import random
from collections import defaultdict
from typing import Any, Optional

import numpy as np

from .reference_data import TYPO_VARIANTS


class DataQualityTracker:
    """Tracks all introduced data quality issues for reporting."""

    def __init__(self):
        self.issues = defaultdict(list)
        self.counts = defaultdict(int)

    def record(self, issue_type: str, details: str = "", row_idx: int = None):
        self.counts[issue_type] += 1
        if row_idx is not None:
            self.issues[issue_type].append({"row": row_idx, "details": details})

    def merge(self, other: "DataQualityTracker") -> None:
        for issue_type, count in other.counts.items():
            self.counts[issue_type] += count
        for issue_type, examples in other.issues.items():
            self.issues[issue_type].extend(examples)

    def generate_report(self) -> str:
        lines = [
            "=" * 70,
            "DATA QUALITY REPORT - Introduced Issues for Testing",
            "=" * 70,
            "",
            "SUMMARY OF INTRODUCED DATA QUALITY ISSUES",
            "-" * 40,
        ]

        for issue_type, count in sorted(self.counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {issue_type}: {count}")

        lines.extend(["", "DETAILED EXAMPLES (first 5 of each type)", "-" * 40])

        for issue_type, examples in self.issues.items():
            lines.append(f"\n{issue_type}:")
            for ex in examples[:5]:
                lines.append(f"  Row {ex['row']}: {ex['details']}")

        lines.extend(
            [
                "",
                "=" * 70,
                "Use this report to validate data cleaning pipelines.",
                "=" * 70,
            ]
        )

        return "\n".join(lines)


def corrupt(
    val: Any,
    rate: float = 0.04,
    replacement: Any = None,
    tracker: DataQualityTracker = None,
    issue_type: str = "missing_value",
    row_idx: int = None,
) -> Any:
    if random.random() < rate:
        if tracker:
            tracker.record(issue_type, f"Original: {val}", row_idx)
        return replacement if replacement is not None else np.nan
    return val


def add_typo(
    val: str,
    rate: float = 0.02,
    tracker: DataQualityTracker = None,
    row_idx: int = None,
) -> str:
    if random.random() < rate and val in TYPO_VARIANTS:
        typo = random.choice(TYPO_VARIANTS[val])
        if tracker:
            tracker.record("typo", f"'{val}' -> '{typo}'", row_idx)
        return typo
    return val
