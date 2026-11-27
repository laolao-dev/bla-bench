from collections.abc import Mapping
from inspect import isawaitable
from math import isnan


def fetch(url):
    raise TypeError(f"Failed to parse URL from {url}")


def _js_truthy(value):
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)):
        return value != 0 and not (isinstance(value, float) and isnan(value))
    if isinstance(value, str):
        return value != ""
    return True


def _js_length(value):
    if value is None:
        raise TypeError("Cannot read length of null or undefined")
    if isinstance(value, str):
        return len(value.encode("utf-16-le", "surrogatepass")) // 2
    if isinstance(value, (list, tuple, bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, Mapping):
        return value.get("length")
    return getattr(value, "length", None)


def register_handlers(store, ipc_main, fetch_fn=None):
    async def read_rich(event, *args):
        request = fetch if fetch_fn is None else fetch_fn
        result = request("/api/v1/clipboard/blocks")
        if isawaitable(result):
            await result
        blocks = store.get("lastBlocks")
        return blocks if _js_truthy(blocks) else []

    async def write_rich(event, blocks=None, *args):
        store.set("lastBlocks", blocks)
        return {"ok": True, "count": _js_length(blocks)}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
