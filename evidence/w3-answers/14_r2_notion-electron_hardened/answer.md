# Electron clipboard IPC

The archive's `package.json` names `main.js` as its entry point. REA's application analyzer rejected the ASAR because its header exceeds the 16 MiB decode budget; analysis of the extracted entry files timed out. REA opened the exact extracted `main.js` as JavaScript and reported SHA-256 `3e32ee4d4a1284542f8cf59888d3a525feeceb33e548fbf5d1baa1d3e16fd5a6`, matching the ASAR entry's integrity hash.

At `main.js:1403`, `registerNotionClipboardHandlers` exports `mirrorPendingPoolImpl804qt` (`main.js:860`). A Node VM with stubbed Electron, fetch, and store resolved the obfuscated names and confirmed that invoking the export registers these two channels:

- `notion:clipboard:read-rich` awaits `fetch('/api/v1/clipboard/blocks')`, discards the response, then returns `store.get('lastBlocks') || []` (`main.js:1023`, `main.js:1174`). A fetch failure propagates before the store read.
- `notion:clipboard:write-rich` stores the supplied blocks unchanged under `lastBlocks`, then returns `{ok: true, count: blocks.length}` (`main.js:1342`). A two-element input produced `count: 2` in the mock trace.

The Python port uses `fetch_fn` when supplied and otherwise resolves `answer.fetch` at call time. Python has no built-in fetch and the recovered URL is relative, so the port does not guess an origin. The VM made no network requests.
