# ADR 0001: Readmissions Are Real Visit Rows

**Date:** 2026-05-11  
**Status:** Accepted

## Context

The original generator set `readmitted_30day = 1` and `days_to_readmission = N` on index visits, but never created a corresponding visit row for the readmission. Analysts could train a prediction model on the flag, but could not practice the core encounter-level skill: finding the readmission event, linking it to the index visit, and verifying the 30-day window.

## Decision

When an index visit has `readmitted_30day = 1`, the pipeline generates an additional visit row for that patient with `admit_date = index_discharge_date + days_to_readmission`. This row goes through the full `generate_visit()` pipeline and appears as a normal encounter in the dataset.

## Consequences

- Row count increases ~10–15% due to injected readmission rows.
- `visit_number` on readmission rows continues the patient's sequence (e.g., if the patient had 2 planned visits and visit 1 readmits, the readmission becomes visit 2 and the original visit 2 becomes visit 3).
- Analysts must derive which rows are readmissions — no explicit flag is added (see ADR 0002).
- Ground truth for validation remains on the index visit via `readmitted_30day` and `days_to_readmission`.

## Alternatives Considered

**Flag only, no row** — original approach. Teaches prediction modeling but not encounter linkage. Rejected because encounter linkage is the primary skill this dataset is designed to teach.
