import os
import urllib.parse
from typing import Optional

from sqlmodel import create_engine, Session, select
from langchain_community.utilities import SQLDatabase
from db.model import Connection

# App metadata DB (users/connections)
DATABASE_URL = "sqlite:///data/db_llm.sqlite3"
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

def get_dialect_table_names(user_id: str, connection_name: str) -> dict:
    db = get_langchain_db_object(user_id, connection_name)
    return {"dialect": db.dialect, "table_names": db.get_usable_table_names()}

def get_langchain_db_object(user_id: str, connection_name: str) -> SQLDatabase:
    session_gen = get_session()
    session = next(session_gen)
    try:
        stmt = select(Connection).where(
            Connection.user_id == user_id,
            Connection.connection_name == connection_name,
        )
        connection: Optional[Connection] = session.exec(stmt).first()
        if not connection:
            raise Exception(f"No DB connection found for user={user_id}, connection_name={connection_name}")

        if connection.db_type == "sqlite":
            basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            sqlite_path = os.path.normpath(os.path.join(basedir, "data", connection.connection_name))
            if not os.path.isfile(sqlite_path):
                raise FileNotFoundError(f"SQLite DB file not found at: {sqlite_path}")
            db_uri = f"sqlite:///{sqlite_path}?check_same_thread=False"

        elif connection.db_type == "postgresql":
            db_uri = (
                f"postgresql://{connection.db_user}:{urllib.parse.quote_plus(connection.db_password)}"
                f"@{connection.db_host}:{connection.db_port}/{connection.connection_name}"
            )

        elif connection.db_type == "mysql":
            db_uri = (
                f"mysql+pymysql://{connection.db_user}:{urllib.parse.quote_plus(connection.db_password)}"
                f"@{connection.db_host}:{connection.db_port}/{connection.connection_name}"
            )

        else:
            raise ValueError(f"Unsupported DB type: {connection.db_type}")

        return SQLDatabase.from_uri(db_uri)

    finally:
        session.close()
