"""UACP runtime-adapter symlink discovery probe."""
LOADED_FROM_UACP_SYMLINK_PROBE = True

def register(ctx):
    def _noop_on_session_start(**kwargs):
        return None
    ctx.register_hook("on_session_start", _noop_on_session_start)
