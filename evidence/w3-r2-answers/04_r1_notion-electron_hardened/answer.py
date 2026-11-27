from inspect import isawaitable
from math import isnan


def _js_falsy(value):
    if value is None or value is False:
        return True
    if isinstance(value, str):
        return not value
    if isinstance(value, (int, float)):
        return value == 0 or (isinstance(value, float) and isnan(value))
    return False


def _js_length(value):
    if value is None:
        raise TypeError("Cannot read property 'length' of null or undefined")
    if isinstance(value, str):
        return len(value.encode("utf-16-le", errors="surrogatepass")) // 2
    if isinstance(value, (list, tuple, bytes, bytearray)):
        return len(value)
    if isinstance(value, dict):
        return value.get("length")
    return getattr(value, "length", None)


def register_handlers(store, ipc_main, fetch_fn=None):
    """Register clipboard handlers; a fetch hook receives the original relative URL."""
    async def read_rich(event, *args):
        url = "/api/v1/clipboard/blocks"
        fetcher = fetch_fn if fetch_fn is not None else globals().get("fetch")
        if fetcher is None:
            raise TypeError(f"Failed to parse URL from {url}")
        response = fetcher(url)
        if isawaitable(response):
            await response
        value = store.get("lastBlocks")
        return [] if _js_falsy(value) else value

    async def write_rich(event, blocks=None, *args):
        store.set("lastBlocks", blocks)
        return {"ok": True, "count": _js_length(blocks)}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
