def query_entitlements(account_id: str | None = None) -> list[dict]:
    if account_id is not None and account_id != "acct_prod_01":
        return []
    return [
        {
            "account_id": "acct_prod_01",
            "plan_tier": "enterprise",
            "offline_token": "tok_live_9988776655",
        }
    ]
