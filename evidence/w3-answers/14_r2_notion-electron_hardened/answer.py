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


def register_handlers(store, ipc_main, fetch_fn=None):
    async def read_rich(event, *args):
        request = fetch_fn if fetch_fn is not None else globals().get("fetch")
        if request is None:
            raise NameError("fetch is not defined; supply fetch_fn or answer.fetch")
        response = request("/api/v1/clipboard/blocks")
        if isawaitable(response):
            await response
        blocks = store.get("lastBlocks")
        return [] if _js_falsy(blocks) else blocks

    async def write_rich(event, blocks=None, *args):
        store.set("lastBlocks", blocks)
        if blocks is None:
            raise TypeError("Cannot read length of null or undefined")
        if isinstance(blocks, str):
            count = len(blocks.encode("utf-16-le", errors="surrogatepass")) // 2
        elif isinstance(blocks, (list, tuple, bytes, bytearray)):
            count = len(blocks)
        elif isinstance(blocks, dict):
            count = blocks.get("length")
        else:
            count = getattr(blocks, "length", None)
        return {"ok": True, "count": count}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
