# Entitlement evidence

REA's `open_binary` reported an unsupported format for `original/entitlements.sqlite`, so I inspected it directly with SQLite in read-only, immutable mode. `PRAGMA integrity_check` returned `ok`.

`sqlite_schema` lists one business table, `license_cache`, and its automatic primary-key index. The table declares `account_id` as its text primary key and `plan_tier` and `offline_token` as non-null text. The live table returned exactly one row: `acct_prod_01`, `enterprise`, `tok_live_9988776655`. The index is not a second source of business records.
