# Clipboard IPC reconstruction

The ASAR's `package.json` selects `main.js`. REA rejected the full archive because its header exceeds the 16 MiB decode budget, so I read the entrypoint directly by ASAR offset and checked its SHA-256 against the header. REA's graph of the reduced, decoded entrypoint identified two Electron main handlers and one request. The original `main.js` supplies the control-flow evidence.

In `main.js:1403`, the exported `registerNotionClipboardHandlers` is `mirrorPendingPoolImpl804qt` (line 860). The corpus digest is `1316792008`, giving a seed of `2879612211`. Its low bits make the read-registration and write-persistence guards true and the neighboring helper-call guards false. Ring updates XOR both latch words with the same mask, preserving the XOR used by the string decoders. Evaluating the decoder expressions recovers these operations:

- `notion:clipboard:read-rich` awaits `fetch('/api/v1/clipboard/blocks')`, ignores the response, and returns `store.get('lastBlocks') || []`. A fetch failure propagates before the store is read. With no injected or module-global fetch, the port reproduces the failure of a base-less main-process fetch on that relative URL.
- `notion:clipboard:write-rich` stores the supplied value unchanged under `lastBlocks`, then returns `{ok: true, count: blocks.length}`. It does not parse or validate the blocks before storing them.
