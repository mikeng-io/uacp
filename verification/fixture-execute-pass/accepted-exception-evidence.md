# Accepted warning exception evidence

Intent: this fixture proves that warning exceptions are bound to the same run and cluster that raised the warning.

Rationale: the evidence exists under `verification/fixture-execute-pass/`, so it cannot launder an unrelated repository file such as config or another run artifact.

Decision: Heartgate and the offline validator may accept cluster `c1` only when the accepted exception cites this run-bound evidence path with matching `cluster_id`.
