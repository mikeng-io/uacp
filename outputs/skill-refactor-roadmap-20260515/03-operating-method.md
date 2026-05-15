# Operating Method

## Mandatory loop for each skill

Every skill refactor follows exactly:

1. Explore
2. Determine
3. Decision
4. Review
5. Audit
6. Implement

No step is skipped. No implementation starts before the prior five steps are captured.

## Step definitions

### Explore
Read only the current skill and narrowly relevant source material. Capture what exists, what is missing, what is confusing, and what facts are known.

### Determine
Classify findings into possible changes. Identify candidate files, references, templates, scripts, schemas, and boundaries. Do not decide yet.

### Decision
Choose the exact target shape and scope for this skill only. Record what will be changed and what will not.

### Review
Get an independent or explicit review of the decision. Review asks whether the proposed shape solves the structural problem without over-broadening.

### Audit
Define concrete checks before patching: file existence, size, local ownership, no global mega-SOP, no cross-skill drift.

### Implement
Patch only the selected skill directory and any explicitly approved local support files. Stop after implementation.

## Hard sequencing rule

Only one skill is active at a time. Do not enrich another skill while working on the current skill. Do not move shared files unless the active phase is shared-reference cleanup.
