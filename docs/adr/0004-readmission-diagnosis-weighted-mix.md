# ADR 0004: Readmission Diagnosis Uses Weighted Mix

**Date:** 2026-05-11  
**Status:** Accepted

## Context

When generating the readmission visit row, a primary diagnosis must be assigned. The choice affects how realistic the data looks and what analysts learn.

## Decision

Readmission visit diagnosis is drawn from a weighted distribution:
- **60% same** — same `primary_dx_code` as the index visit (same condition recurred/worsened)
- **30% related** — drawn from the index visit's `secondary_dx_codes` (comorbidity returned)
- **10% random** — any diagnosis (unrelated ED return)

If the index visit has no secondary diagnoses, the 30% related weight falls back to same-dx.

## Consequences

- Analysts cannot assume readmissions are always for the same condition — mirrors real CMS data patterns.
- The 60% same-dx majority still produces a strong signal for diagnosis-based readmission rate analysis.
- The 10% random noise teaches analysts to expect and handle unrelated returns.

## Alternatives Considered

**Always same dx** — too clean, doesn't reflect real readmission patterns. Rejected.  
**Always random** — destroys the learning signal. Rejected.  
**Related only** — misses the "unrelated return" pattern that is common in real data. Rejected.
