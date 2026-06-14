<!-- Golden fixture: uacp.evidence_disposition — assumptions half (VERIFY->RESOLVE) -->
<!-- Minimal VALID instance: per config/artifact-schemas.yaml this is the
     assumptions.md member of the paired_paths pair. The
     evidence_disposition_minimum_content cross-check requires the header to
     contain the case-sensitive substring "Disposition". Author the header
     exactly. A `pending` row would need owner + next_phase_obligation; the
     single row below uses `accepted_risk` (requires owner only) to stay valid. -->

# Assumptions — uacp-fixture-001

| Assumption | Disposition | Owner | Next-phase obligation |
| --- | --- | --- | --- |
| Fixture inputs are well-formed. | accepted_risk | e2e-harness | n/a |
