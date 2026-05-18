# Verified facts — validator fixtures

Fact: `scripts/validate_uacp_artifacts.py` recognizes `kind: uacp.proposal_package_selection`.

Fact: Passing fixture validates with `RESULT PASS`.

Fact: Blocking fixture validates with `RESULT BLOCK` and reports missing universal core concerns, missing selected module artifact, and weak not-applicable rationale.

Fact: Current run proposal and package-selection artifacts validate with `RESULT PASS`.
