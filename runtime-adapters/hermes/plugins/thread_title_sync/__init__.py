"""Thread title sync plugin."""

from .policy import handle_pre_thread_title_sync


def register(ctx) -> None:
    ctx.register_hook("pre_thread_title_sync", handle_pre_thread_title_sync)
