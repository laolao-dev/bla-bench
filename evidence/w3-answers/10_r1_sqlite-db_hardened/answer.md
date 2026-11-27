# Entitlement evidence

REA's `open_binary` rejected `original/entitlements.sqlite` as an unsupported format. I inspected it directly with SQLite in read-only, immutable mode; `PRAGMA integrity_check` returned `ok`.

`sqlite_schema` identifies `license_cache` as a table keyed by `account_id`, with stored `plan_tier` and `offline_token` values. Its root page (page 2) is a leaf with one cell. The query returned one row: `acct_prod_01`, `enterprise`, `tok_live_9988776655`.

The other schema objects describe enclave keys, attestation, session leases, transport canaries, or diagnostics. The enclave view projects key-hierarchy data, and the `ENCLAVE_SEALED:` fields are virtual string expressions, not stored business entitlements.
