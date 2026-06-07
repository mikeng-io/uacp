# Rollback and Transition

## Rollback Procedure

### Primary Method: Git Revert

```bash
cd /home/norty/.hermes
git status  # verify modified files
git checkout -- <file>  # revert specific file
```

### Reverse-Order Rollback

To minimize risk, rollback in reverse order of changes:

1. **Revert PERSONALITY.md** (last change, RT-6)
2. **Revert SOUL.md, KERNEL.md, IDENTITY.md, SECURITY.md** (doctrinal grant, RT-1)
3. **Revert identity_registry.py and runtime.json** (schema validation, RT-3)
4. **Revert plugin __init__.py** (safe card, health, hook contract)

### Restart Requirements

- **Doctrine file changes:** No restart needed (read at gateway startup)
- **Plugin code changes:** Gateway restart required for plugin to reload
- **Registry engine changes:** Registry recompile needed (`python identity_registry.py compile`)

### Rollback Verification

After rollback:
1. `git status` shows clean working tree
2. Gateway restart (operator boundary)
3. `python -m py_compile` on reverted files passes
4. Plugin import test passes
5. Live test: Nora behavior returns to previous state

## Transition Readiness

### PLAN → EXECUTE Requirements

- [x] Plan artifact exists (`plans/nora-doctrine-remediation-20260605-170000-plan.yaml`)
- [x] Scope artifact exists (`plans/nora-doctrine-remediation-20260605-170000-scope.yaml`)
- [x] Plan selection exists (`plans/nora-doctrine-remediation-20260605-170000-plan-selection.yaml`)
- [x] PIV contract exists (`plans/nora-doctrine-remediation-20260605-170000-piv.yaml`)
- [x] Plan package exists (`plans/nora-doctrine-remediation-20260605-170000/`)
- [ ] PLAN_VALIDATION ledger entry (next step)
- [ ] Human boundary for restart recorded

### PLAN_VALIDATION Checks (pv_1 through pv_6)

- **pv_1:** scope artifact present and parses ✓
- **pv_2:** allowed tools registered (file, terminal, patch, write_file, search_files, read_file)
- **pv_3:** write_paths within proposal side_effects ✓
- **pv_4:** blast_radius=high, human involvement recorded ✓
- **pv_5:** rollback_path declared ✓
- **pv_6:** cluster artifacts referenced (council synthesis, proposal, triage) ✓

### EXECUTE → VERIFY Requirements

- [ ] All 8 work units complete
- [ ] Static verification (V1-V5) passes
- [ ] Council review verdict = PASS or no material concerns
- [ ] No unresolved material findings
- [ ] Operator approves gateway restart

### VERIFY → RESOLVE Requirements

- [ ] VERIFY artifact exists
- [ ] All EXECUTE work verified
- [ ] Lessons extracted
- [ ] Forward-pointers recorded (SYN-M4, SYN-I1-I3)

## Forward Pointers (Out-of-Scope)

| Finding | Forward-Pointer |
|---|---|
| SYN-M4 | Separate UACP run for SECURITY.md §4 expansion |
| SYN-I1 | Deferred (schema validates `kind`) |
| SYN-I2 | Deferred (DM-focused scope) |
| SYN-I3 | Deferred (cosmetic) |
