# Entitlement evidence

REA's `open_binary` reported an unsupported format, so I inspected the artifact with a read-only SQLite connection. `PRAGMA integrity_check` returned `ok`.

`license_cache` is the only table keyed by `account_id`. Its other columns are `plan_tier` and `offline_token`. It contains one row: `acct_prod_01` on the `enterprise` tier. The function returns all three stored values unchanged.

The other tables store enclave slots, attestation quotes, session leases, transport canaries, or diagnostics. None has an `account_id` column. The topology view projects enclave slots, not account entitlements.
