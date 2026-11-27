`package.json` in `original/notion-clipboard.asar` names `main.js` as the entry point. REA's JavaScript analyzer rejected the ASAR because its header exceeded the decode budget; a retry on the extracted entry files timed out. I read the members directly from the archive offsets and checked the exported registrar in a bounded Node VM with mock Electron, store, and fetch. No live requests were made.

`main.js` exports `registerNotionClipboardHandlers` (line 1403). Its two reachable registration calls (lines 867 and 1185) resolve to:

- `notion:clipboard:read-rich`: await fetch of `/api/v1/clipboard/blocks`, ignore the response, then return `store.get("lastBlocks") || []`. A rejected fetch prevents the store read. Empty arrays and objects are truthy in JavaScript and are returned unchanged.
- `notion:clipboard:write-rich`: store the payload unchanged under `lastBlocks`, then return `{ok: true, count: payload.length}`. Null or omitted payloads fail when reading `.length`, after calling `set`.

The port represents JavaScript `undefined` as `None`. Pass `fetch_fn` or provide a module-level `answer.fetch`; the relative URL is passed through unchanged.
