# Entitlement evidence

REA's `inspect-artifact` reported that `original/entitlements.sqlite` was an unsupported binary format. The file begins with the SQLite 3 signature, so I verified it directly with SQLite in immutable, read-only mode. `PRAGMA integrity_check` returned `ok`.

The schema defines `license_cache(account_id TEXT PRIMARY KEY, plan_tier TEXT NOT NULL, offline_token TEXT NOT NULL)`. `SELECT * FROM license_cache ORDER BY account_id` returned exactly one row: `acct_prod_01`, `enterprise`, `tok_live_9988776655`. The table's leaf page has one cell, and the separate primary-key index leaf has one cell for the same account. The index entry is not a second business row.
