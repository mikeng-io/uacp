# Decision Log

## Decision
The fixture records execution evidence as a semantic package plus a machine checkpoint.

## Rationale
This decision prevents raw file lists from becoming the only record of EXECUTE. Alternatives rejected include a YAML-only checkpoint and a generic prose summary with no evidence mapping. The rationale is that VERIFY must inspect structured obligations and semantic context together.
