from collections.abc import Mapping
from inspect import isawaitable
from math import isnan


def fetch(url):
    raise TypeError(f"Failed to parse URL from {url}")


def _js_falsy(value):
    if value is None or value is False:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, (int, float)):
        return value == 0 or (isinstance(value, float) and isnan(value))
    return False


def _js_length(value):
    if value is None:
        raise TypeError("Cannot read properties of null or undefined (reading 'length')")
    if isinstance(value, str):
        return len(value.encode("utf-16-le", errors="surrogatepass")) // 2
    if isinstance(value, (list, tuple, bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, Mapping):
        return value.get("length")
    return getattr(value, "length", None)


def register_handlers(store, ipc_main, fetch_fn=None):
    async def read_rich(event, *args):
        request = fetch if fetch_fn is None else fetch_fn
        response = request("/api/v1/clipboard/blocks")
        if isawaitable(response):
            await response
        blocks = store.get("lastBlocks")
        return [] if _js_falsy(blocks) else blocks

    async def write_rich(event, blocks=None, *args):
        store.set("lastBlocks", blocks)
        return {"ok": True, "count": _js_length(blocks)}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
