import sqlite3
from contextlib import closing
from pathlib import Path


def query_entitlements(account_id: str | None = None) -> list[dict]:
    database = Path(__file__).with_name("original") / "entitlements.sqlite"
    uri = database.absolute().as_uri() + "?mode=ro&immutable=1"
    query = "SELECT account_id, plan_tier, offline_token FROM license_cache"
    parameters = ()
    if account_id is not None:
        query += " WHERE account_id = ?"
        parameters = (account_id,)
    query += " ORDER BY account_id"

    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]
