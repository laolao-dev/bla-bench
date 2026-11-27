# Electron main-process IPC

- `notion:clipboard:read-rich` awaits `fetch("/api/v1/clipboard/blocks")` but never reads the response. It then returns `store.get("lastBlocks") || []`. A rejected fetch propagates before the store is read.
- `notion:clipboard:write-rich` stores its first payload unchanged under `lastBlocks`, then returns `{ok: true, count: payload.length}`. There is no clipboard parsing or validation. A null or omitted payload is written before the `.length` access fails. The Python port represents an undefined stored value as `None` and omits an undefined `count` key.

**Evidence.** REA's application analyzer reported that the ASAR header exceeded its 16 MiB decode budget; a retry on the extracted entry files timed out. I checked the ASAR member hashes against the archive's integrity metadata. The shipped `package.json` selects `main.js`, whose line 1403 exports `registerNotionClipboardHandlers`. The reachable handler bodies start at `main.js:1017` and `main.js:1335`; the enclave-themed branch at line 587 is unreachable because unsigned `x | y` cannot be less than `x ^ y`. A controlled replay of the unmodified entry with stubbed Electron, fetch, and storage confirmed the channel names, URL, and key, as well as write counts and fetch failure ordering. No live requests were made.

Pass `fetch_fn` for a fetch implementation that resolves relative URLs, or for a test double. Without it, the port uses a module-global `fetch` if supplied; otherwise it reproduces the standalone Node failure on the relative URL.
