# Main-process IPC

REA’s static JavaScript application analysis of `original/notion-clipboard.asar` found no integrity contradictions and identified the fetch endpoint in `main.js`. Reading the archived source in place confirmed that `package.json` selects `main.js` and that its exported registration function installs two handlers:

- `main.js:4` — `notion:clipboard:read-rich` awaits `fetch("/api/v1/clipboard/blocks")`, discards the response, then returns `store.get("lastBlocks") || []`. A rejected fetch prevents the store read.
- `main.js:8` — `notion:clipboard:write-rich` stores the input under `lastBlocks`, then returns `{ok: true, count: blocks.length}`. The store write happens before the length lookup.

`preload.js` invokes both channels and separately sends `notion:clipboard:selection-sync`, which `main.js` does not handle. The Python port uses `fetch_fn` if supplied, or resolves a global `fetch` at call time. Python has no built-in `fetch`. No Electron code was executed.
