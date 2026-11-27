# Evidence

REA's `open_binary` rejected the SQLite file as unsupported, so I inspected the catalog and rows with a read-only SQLite connection.

`sqlite_schema` shows that `license_cache` is the only table keyed by `account_id` with both a plan tier and an offline token. It contains one row: `acct_prod_01` on the `enterprise` tier, with an offline token returned unchanged by the query. The other objects describe enclave topology, attestation, session leases, transport canaries, or diagnostics rather than account entitlements.
