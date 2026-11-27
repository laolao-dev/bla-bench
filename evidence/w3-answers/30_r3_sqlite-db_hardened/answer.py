import sqlite3
from contextlib import closing
from pathlib import Path


def query_entitlements(account_id: str | None = None) -> list[dict]:
    database = Path(__file__).resolve().parent / "original" / "entitlements.sqlite"
    uri = database.as_uri() + "?mode=ro&immutable=1"
    sql = "SELECT account_id, plan_tier, offline_token FROM license_cache"
    parameters = ()
    if account_id is not None:
        sql += " WHERE account_id = ?"
        parameters = (account_id,)
    sql += " ORDER BY account_id"

    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql, parameters)]
