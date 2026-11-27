from collections.abc import Mapping
from inspect import isawaitable
from math import isnan


def register_handlers(store, ipc_main, fetch_fn=None):
    async def read_rich(event, *args):
        request = fetch_fn if fetch_fn is not None else globals().get("fetch")
        if request is None:
            raise RuntimeError("No global fetch configured; pass fetch_fn")
        response = request("/api/v1/clipboard/blocks")
        if isawaitable(response):
            await response

        blocks = store.get("lastBlocks")
        if blocks is None or blocks is False:
            return []
        if isinstance(blocks, (int, float)) and (
            blocks == 0 or isinstance(blocks, float) and isnan(blocks)
        ):
            return []
        if isinstance(blocks, str) and not blocks:
            return []
        return blocks

    async def write_rich(event, blocks=None, *args):
        store.set("lastBlocks", blocks)
        if blocks is None:
            raise TypeError("Cannot read length of null or undefined")
        if isinstance(blocks, str):
            count = len(blocks.encode("utf-16-le", errors="surrogatepass")) // 2
        elif isinstance(blocks, (list, tuple, bytes, bytearray)):
            count = len(blocks)
        elif isinstance(blocks, Mapping):
            count = blocks.get("length")
        else:
            count = getattr(blocks, "length", None)
        return {"ok": True, "count": count}

    ipc_main.handle("notion:clipboard:read-rich", read_rich)
    ipc_main.handle("notion:clipboard:write-rich", write_rich)
