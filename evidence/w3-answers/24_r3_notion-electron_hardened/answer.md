# Electron clipboard IPC

The archive's `package.json` names `main.js` as the entry point. I verified the extracted entry-point bytes against the ASAR's SHA-256 metadata. REA rejected the original archive because its header exceeded the decode budget, and analysis of the extracted bundles timed out. On a focused, decoded projection, REA identified two literal main-process handlers and one fetch request (graph `ev_c8b77c48995b0dab69b25072a91acbef6b8b782c367bb25d3f0c78688d3d1716`).

The shipped `main.js:1403` exports `mirrorPendingPoolImpl804qt` as `registerNotionClipboardHandlers`. Evaluating the seed and replaying the registration slice with stubbed Electron, store, and fetch confirmed the decoded strings and the live paths. The store and event cannot change the low bits used by the guards, and the latch updates XOR both words with the same mask, preserving the decoder's XOR key. No real request was sent.

- `notion:clipboard:read-rich` (`main.js:867`) awaits `fetch('/api/v1/clipboard/blocks')`, discards the response, and returns `store.get('lastBlocks') || []`. A rejected fetch prevents the store read. The default Python fetch mirrors the failure of a relative URL without a base URL; pass `fetch_fn` to provide a resolver or stub.
- `notion:clipboard:write-rich` (`main.js:1185`) stores the first argument after the event at `lastBlocks`, then returns `{ok: true, count: blocks.length}`. The write precedes the length lookup, even if that lookup throws. The Python port uses `None` for an undefined length and counts strings in UTF-16 code units.
