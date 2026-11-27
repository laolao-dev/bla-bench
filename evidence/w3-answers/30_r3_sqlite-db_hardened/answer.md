# Evidence

REA's `open_binary` rejected the artifact as an unsupported format, so I inspected it directly with SQLite in read-only mode. `PRAGMA integrity_check` returned `ok`.

`sqlite_schema` identifies `license_cache` as the account entitlement table: `account_id` is its primary key, and the remaining columns are `plan_tier` and `offline_token`. Its table B-tree (root page 2) contains one live row, for `acct_prod_01` on the `enterprise` plan.

The other objects hold enclave keys, attestation records, session leases, redaction canaries, or diagnostics. The session lease table has a tier field but is keyed by `lease_token` and has no account column. The enclave topology view projects the enclave key table and adds no entitlement records.
