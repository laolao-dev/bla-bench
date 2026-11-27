# Entitlement evidence

REA's `open_binary` rejected `original/entitlements.sqlite` as an unsupported format. I verified the artifact with read-only SQLite queries and a direct byte check instead. `PRAGMA integrity_check` returned `ok`.

`sqlite_schema` identifies `license_cache` as a table rooted at page 2, with `account_id` as its text primary key and `plan_tier` and `offline_token` as its other columns. The query returned exactly one row: `acct_prod_01`, `enterprise`, `tok_live_9988776655`. The sole live cell on page 2 (file offset `0x1fd1`) contains the same three values.

The remaining tables store enclave slots, attestation quotes, session leases, canaries, or diagnostics rather than account entitlements. The enclave view only projects slot metadata; the `ENCLAVE_SEALED:` fields are generated string concatenations, not additional entitlement records.
