# Rollback and Recovery

## Rollback path
- Preserve diffs via git/status inspection where available.
- For failed code/config patches, reverse targeted patches or restore from prior content.
- Do not delete historical UACP artifacts; supersede with resolution notes if needed.

## Stop conditions
- Validator cannot distinguish pass/block fixtures.
- Heartgate negative dry-run does not block.
- PLAN package doctrine forces fixed filenames rather than adaptive concerns.
- Guardian policy patch creates overclaim of hard interception without proof.

## Recovery
If stopped, write an EXECUTE checkpoint and route a narrower repair run.
