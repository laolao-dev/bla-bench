# Main-process IPC

- `notion:clipboard:read-rich` awaits `fetch("/api/v1/clipboard/blocks")`, discards the response, and returns `store.get("lastBlocks") || []`. A fetch rejection propagates before the store is read.
- `notion:clipboard:write-rich` stores the first payload argument unchanged as `lastBlocks`, then returns `{ok: true, count: blocks.length}`. It does not fetch.

The ASAR manifest names `main.js` as the entry point. REA's archive analysis hit its header-size limit, but REA identified the selectively unpacked `main.js` as JavaScript and reported a SHA-256 that matched the ASAR entry's integrity hash. The export at `main.js:1403` points to the registrar at `main.js:860`. Evaluating its seed and decoding its strings, then replaying the registrar and handlers with mocked IPC, storage, and fetch, confirmed the two channels, URL, key, and return values. No Electron app or network request was needed.

In Python, pass `fetch_fn` or supply a module-global `fetch`; Python has no built-in global `fetch`.
