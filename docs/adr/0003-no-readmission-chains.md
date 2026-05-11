# ADR 0003: Readmission Rows Do Not Chain

**Date:** 2026-05-11  
**Status:** Accepted

## Context

Readmission rows are generated via the full `generate_visit()` pipeline, which includes a call to `calculate_readmit_risk()`. Without special handling, a readmission row could itself get `readmitted_30day = 1`, creating a chain: index → readmit-1 → readmit-2.

In real life, high-risk patients do bounce repeatedly. However, detecting chains requires graph traversal, which is an advanced skill beyond the scope of this project.

## Decision

Readmission rows always have `readmitted_30day = 0` and `days_to_readmission = NaN`, regardless of what `calculate_readmit_risk()` returns. Chaining is suppressed at the pipeline level.

## Consequences

- Every `readmitted_30day = 1` row in the dataset is definitively an index visit.
- The index-to-readmission relationship is always 1:1 — one index visit links to exactly one readmission row.
- Analysts practice a simple two-row join, not a chain traversal.
- Clinically: slightly less realistic for very high-risk patients, acceptable for a learning dataset.

## Alternatives Considered

**Allow chains** — realistic but introduces graph complexity out of scope for foundational analysis practice. Rejected. Can be revisited as a harder dataset variant in the future.
