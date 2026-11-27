# Entitlement evidence

REA's `open_binary` rejected `original/entitlements.sqlite` as an unsupported format, so I verified the artifact with read-only SQLite queries and raw-byte inspection.

SQLite's schema identifies `license_cache` (root page 2) as the only table, with `account_id TEXT PRIMARY KEY`, `plan_tier TEXT NOT NULL`, and `offline_token TEXT NOT NULL`. `PRAGMA integrity_check` returned `ok`. The live table contains exactly one row: `acct_prod_01`, `enterprise`, `tok_live_9988776655`. The raw bytes show these values together on page 2; the second appearance of `acct_prod_01` is on page 3, the primary-key autoindex, not another business row.
