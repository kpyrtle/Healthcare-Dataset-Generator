# ADR 0002: No Explicit Readmission Marker on Readmission Rows

**Date:** 2026-05-11  
**Status:** Accepted

## Context

Readmission rows are real visit rows (ADR 0001). The question is whether to add an `is_readmission` column (or similar) to mark them explicitly.

## Decision

No explicit marker is added to readmission rows. They appear as ordinary encounters. Analysts must identify them by:
1. Finding all encounters per patient sorted by `admit_date`
2. Checking whether `admit_date` of visit N falls within `discharge_date + 30 days` of visit N-1
3. Validating their derived linkage against `readmitted_30day` and `days_to_readmission` on the preceding index visit

## Consequences

- Analysts practice the actual linkage skill used in real healthcare analytics.
- `readmitted_30day` and `days_to_readmission` on the index visit serve as ground truth for validation.
- The exercise has a verifiable answer — analysts know if they got it right.

## Alternatives Considered

**`is_readmission = True` column** — makes the exercise trivial. Rejected because finding readmissions is the skill being practiced, not consuming a pre-labeled column.

**`admit_type = "Emergency"` bias only** — too subtle and unreliable as a signal. Readmissions do not always arrive through the ED. Rejected.
