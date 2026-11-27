# Evidence

REA's static ASAR analysis found no integrity contradictions. The packed
`package.json` names `main.js` as the entry point. Reading that member directly
confirmed that its exported `registerNotionClipboardHandlers` installs two
async handlers:

- `notion:clipboard:read-rich` awaits `fetch("/api/v1/clipboard/blocks")`,
  discards the response, then returns `store.get("lastBlocks") || []`.
  A fetch failure propagates before the store is read.
- `notion:clipboard:write-rich` stores the supplied `blocks` unchanged under
  `lastBlocks`, then returns `{ ok: true, count: blocks.length }`.

The `selection-sync` channel appears only as a renderer `send` in `preload.js`;
the main module does not register it. The artifact was not executed. In Python,
provide `fetch_fn` or define `answer.fetch`; Python has no built-in `fetch`.
