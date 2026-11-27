from collections.abc import Mapping
from inspect import isawaitable
from math import isnan


_MISSING = object()


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
        raise TypeError("Cannot read properties of null (reading 'length')")
    if value is _MISSING:
        raise TypeError("Cannot read properties of undefined (reading 'length')")
    if isinstance(value, str):
        return len(value.encode("utf-16-le", errors="surrogatepass")) // 2
    if isinstance(value, (list, tuple, bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, Mapping):
        return value.get("length", _MISSING)
    return getattr(value, "length", _MISSING)


def register_handlers(store, ipc_main, fetch_fn=None):
    async def read_rich(event, *args):
        fetcher = fetch_fn if fetch_fn is not None else globals().get("fetch")
        url = "/api/v1/clipboard/blocks"
        if fetcher is None:
            raise TypeError(f"Failed to parse URL from {url}")
        response = fetcher(url)
        if isawaitable(response):
            await response
        value = store.get("lastBlocks")
        return value if _js_truthy(value) else []

    async def write_rich(event, value=_MISSING, *args):
        store.set("lastBlocks", None if value is _MISSING else value)
        count = _js_length(value)
        result = {"ok": True}
        if count is not _MISSING:
            result["count"] = count
        return result

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
