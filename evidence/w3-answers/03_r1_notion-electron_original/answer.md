# Electron clipboard IPC

REA's ASAR inventory verified `package.json`, `main.js`, and `preload.js`. Its static JavaScript analysis found two main handlers and one unmatched renderer transmission (evidence `ev_2dd3e9929ffcfedb2643a43f9b4bb1198a06f135bc7bb4955894914f93a8b39a`). I checked the embedded source bytes against the inventory hashes without running the app.

- `package.json` names `main.js` as the entry point. `notion:clipboard:read-rich` awaits `fetch("/api/v1/clipboard/blocks")` but ignores the response. It then returns `store.get("lastBlocks") || []`. A fetch rejection prevents the store read.
- `notion:clipboard:write-rich` stores the supplied blocks under `lastBlocks` and returns `{ok: true, count: blocks.length}`. The store write happens even if reading `length` subsequently throws.
- `preload.js` invokes those two channels and sends `notion:clipboard:selection-sync`, for which this module registers no handler.

The Python port accepts a synchronous or asynchronous fetch replacement. Its default models main-process fetch rejecting a relative URL without a base; it does not invent an origin. Python `None` represents JavaScript `undefined` for a missing `length` property.
