import sqlite3
from contextlib import closing
from pathlib import Path


def query_entitlements(account_id: str | None = None) -> list[dict]:
    """Return business entitlements from the original SQLite artifact."""
    database = Path(__file__).resolve().parent / "original" / "entitlements.sqlite"
    query = "SELECT account_id, plan_tier, offline_token FROM main.license_cache"
    parameters = ()
    if account_id is not None:
        query += " WHERE account_id = ?"
        parameters = (account_id,)
    query += " ORDER BY account_id"

    uri = f"{database.as_uri()}?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]
