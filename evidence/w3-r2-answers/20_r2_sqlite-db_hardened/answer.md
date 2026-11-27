# Entitlement evidence

REA process capture queried `sqlite_schema` in `original/entitlements.sqlite` read-only. `license_cache` is keyed by `account_id` and stores `plan_tier` and `offline_token`. The other objects describe enclave keys, attestation, session leases, canaries, or diagnostics rather than account entitlements. The `ENCLAVE_SEALED:` previews are generated SQL expressions, not a separate entitlement store.

A second REA capture returned `ok` from `PRAGMA integrity_check` and found exactly one row in `license_cache`: `acct_prod_01`, tier `enterprise`, with a text `offline_token`. The function returns the stored token without reproducing it here. It orders by primary key and binds any supplied account ID as a SQL parameter.
