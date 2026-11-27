from collections.abc import Mapping
from inspect import isawaitable
from math import isnan


def _js_falsy(value):
    return (
        value is None
        or value is False
        or (isinstance(value, (int, float)) and value == 0)
        or (isinstance(value, float) and isnan(value))
        or (isinstance(value, str) and value == "")
    )


def _js_length(value):
    if value is None:
        raise TypeError("Cannot read length of null or undefined")
    if isinstance(value, str):
        return len(value.encode("utf-16-le", errors="surrogatepass")) // 2
    if isinstance(value, (list, tuple, bytes, bytearray)):
        return len(value)
    if isinstance(value, Mapping):
        return value.get("length")
    return getattr(value, "length", None)


def register_handlers(store, ipc_main, fetch_fn=None):
    """Register the clipboard handlers, using module-global fetch by default."""

    async def read_rich(_event, *_args):
        fetcher = fetch_fn if fetch_fn is not None else fetch
        response = fetcher("/api/v1/clipboard/blocks")
        if isawaitable(response):
            await response
        blocks = store.get("lastBlocks")
        return [] if _js_falsy(blocks) else blocks

    async def write_rich(_event, blocks=None, *_args):
        store.set("lastBlocks", blocks)
        return {"ok": True, "count": _js_length(blocks)}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
