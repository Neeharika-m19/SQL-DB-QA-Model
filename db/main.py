from collections import defaultdict
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from db.model import Connection

load_dotenv()


def get_connection_string(user_id: int, db_name: str, session: Session) -> str:
    """
    Dynamically builds the connection string based on a user's saved DB config.
    """
    conn = session.query(Connection).filter_by(
        user_id=user_id,
        connection_name=db_name
    ).first()

    if not conn:
        raise ValueError(f"No connection for user_id={user_id}, db_name={db_name}")

    db_type = conn.db_type.lower()
    if db_type == "sqlite":
        # expect your files in ./data/
        return f"sqlite:///./data/{db_name}"

    if not all([conn.db_user, conn.db_password, conn.db_host, conn.db_port]):
        raise ValueError("Incomplete DB params")

    pw = quote_plus(conn.db_password)
    return f"{db_type}://{conn.db_user}:{pw}@{conn.db_host}:{conn.db_port}/{db_name}"


def get_tables_and_schemas(user_id: int, db_name: str, session: Session):
    out = defaultdict(list)
    conn_str = get_connection_string(user_id, db_name, session)
    eng = create_engine(conn_str)
    insp = inspect(eng)
    for tbl in insp.get_table_names():
        for col in insp.get_columns(tbl):
            out[tbl].append(col["name"])
    return dict(out)


if __name__ == "__main__":
    from db.model import get_session
    with next(get_session()) as sess:
        print(get_tables_and_schemas(1, "northwind_small.sqlite", sess))
