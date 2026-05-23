# Contained shell execution seam notes

Use this when UACP-bound shell/code execution needs a real runtime seam instead of evidence-only proof.

## Verified pattern

- `uacp_sandbox_check` remains *evidence-only*.
- `uacp_contained_shell` is the actual governed execution surface.
- Standard `terminal` / `execute_code` stay fail-closed unless backend-specific containment is proven for those surfaces.
- The implementation used bubblewrap with a read-only host root bind and a writable sandbox workspace bind.
- An internal write probe against `UACP_ROOT` is run before command execution and must confirm that writes are blocked.
- The contained shell returns a short-lived attestation record and rejects stale attestation reuse.

## Practical guardrails

- Keep the shell seam separate from the evidence checker; do not let the checker self-attest standard tool paths.
- Treat `--ro-bind / /` as a deliberate read-exposure tradeoff, not as equivalent to full host isolation.
- Keep output capture bounded if commands can emit large stdout/stderr streams.
- Treat in-memory attestation stores as process-local unless a durable store is intentionally added later.
- If a transition artifact is using Heartgate, make sure the transition file includes the full schema fields expected by the kernel; warnings must be explicitly owned.

## Verification signals that mattered

- Live probe should show the contained shell can execute and the write probe blocks UACP_ROOT.
- Standard shell/code paths should remain blocked without containment evidence.
- Stale attestation reuse should fail.
- The verification artifact should point at durable probe evidence under `verification/`.
