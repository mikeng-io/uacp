# Branch Porting Ground Truthing

Use this workflow when porting doctrine changes from a skills branch, a council-taxonomy refactor, or any other implementation-side change set into UACP.

## Rule

Do not assume the branch is canonical. Ground-truth the live UACP docs/config/state first, then compare the branch against those files.

## Sequence

1. Read the live UACP canon in this order:
   - `docs/index.md`
   - `docs/constitution.md`
   - `docs/lifecycle-reference.md`
   - `docs/runtime-enforcement.md`
   - relevant `config/*.yaml`
   - `state/current.yaml` and relevant run manifests
2. Diff the branch against the live canon.
3. Classify each difference as:
   - already present in UACP
   - missing from UACP
   - conflicting with UACP
   - implementation detail only
4. Port only the missing or approved-conflict items into UACP.
5. Re-check for terminology drift after the port.

## Common mistake

Treating agent-skills wording as doctrine before UACP has absorbed it. Skills are implementation surfaces; UACP is the authority layer.