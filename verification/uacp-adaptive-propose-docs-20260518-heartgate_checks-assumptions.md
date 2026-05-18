# Assumptions — Heartgate checks

Disposition: The currently running plugin process may cache old code until reload; direct local kernel import verifies file-level behavior, not hot-reloaded plugin behavior.

Disposition: Full deployment/reload verification is deferred because this run is a bounded local UACP self-patch lane.

Disposition: RESOLVE must preserve a reload/deployment note before future reliance on live Heartgate enforcement.
