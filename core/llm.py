import os
from fastapi import HTTPException
from pathlib import Path
from dotenv import load_dotenv
from typing_extensions import TypedDict
from sqlmodel import Session, select
from cryptography.fernet import Fernet
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_openai import ChatOpenAI
from sqlalchemy import text
import pandas as pd
import re

from db.model import APIKey, User
from db.main import get_connection_string
from core.db import get_session as core_get_session  # to open a session if caller didn't

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

def _resolve_api_key(provider: str, session: Session, user_id: int) -> str:
    record = session.exec(
        select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)
    ).first()
    if not record:
        raise HTTPException(404, f"No API key for {provider}")

    user = session.get(User, user_id)
    if not user or not user.fernet_key:
        raise HTTPException(404, "Fernet key missing")

    return Fernet(user.fernet_key.encode()).decrypt(record.encrypted_key.encode()).decode()

def _get_llm(provider: str, model_name: str, session: Session, user_id: int):
    api_key = _resolve_api_key(provider, session, user_id)

    # Use env vars to satisfy various client libs
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
        return ChatOpenAI(model=model_name, temperature=0)
    elif provider == "together":
        from langchain_together import ChatTogether
        os.environ["TOGETHER_API_KEY"] = api_key
        return ChatTogether(model=model_name)
    else:
        raise HTTPException(400, f"Unsupported provider: {provider}")

def _extract_sql(raw) -> str:
    """
    Make sure we only return the actual SQL statement, even if the LLM returned
    prefixed text like 'Question:' / 'SQLQuery:' or fenced ```sql blocks.
    """
    # If the chain returned a dict, try common fields
    if isinstance(raw, dict):
        for k in ("sql", "query", "text"):
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                raw = v
                break

    if not isinstance(raw, str):
        raw = str(raw or "")

    s = raw.strip()

    # Grab fenced code block first if present
    fence = re.search(r"```(?:sql)?\s*(.*?)```", s, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    # If there's a "SQLQuery:" label, take everything after it
    if "SQLQuery:" in s:
        s = s.split("SQLQuery:", 1)[1].strip()

    # Remove leading lines until we hit an SQL verb
    verbs = ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP")
    lines = s.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        L = line.strip().upper()
        if any(L.startswith(v) for v in verbs):
            start_idx = i
            break
    s = "\n".join(lines[start_idx:]).strip()

    # Trim trailing explanations like "Answer:" or "Final:"
    for marker in ("Answer:", "Final:", "Explanation:", "Result:"):
        if marker in s:
            s = s.split(marker, 1)[0].strip()

    # Final sanity
    if not s or not any(s.upper().startswith(v) for v in verbs):
        raise HTTPException(500, f"Generated text did not contain a valid SQL statement:\n{raw}")

    return s

def answer_my_question(
    question: str,
    user_id: int,
    db_name: str,
    model_name: str,
    provider: str,
    page: int = 1,
    page_size: int = 5,
    session: Session | None = None,
):
    # open a session if none provided
    created_session = False
    if session is None:
        session = next(core_get_session())
        created_session = True

    try:
        # Build DB URL using your saved connection row
        try:
            db_url = get_connection_string(user_id, db_name, session)
        except Exception as e:
            raise HTTPException(400, f"DB connection error: {e}")

        db = SQLDatabase.from_uri(db_url)
        llm = _get_llm(provider, model_name, session, user_id)
        chain = create_sql_query_chain(llm, db)

        # 1) generate SQL from NL question
        try:
            raw_out = chain.invoke({"question": question})
            generated_sql = _extract_sql(raw_out)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Error generating SQL: {e}")

        # 2) run SQL
        try:
            with db._engine.connect() as conn:
                rp = conn.execute(text(generated_sql))
                df = pd.DataFrame(rp.fetchall(), columns=rp.keys())
        except Exception as e:
            raise HTTPException(500, f"Error executing SQL: {e}\nSQL:\n{generated_sql}")

        # 3) paginate
        total = len(df)
        pages = max(1, (total + page_size - 1) // page_size)
        if page < 1 or page > pages:
            raise HTTPException(400, f"Page {page} out of range (1–{pages})")
        start = (page - 1) * page_size
        end = start + page_size
        slice_ = df.iloc[start:end].to_dict(orient="records")

        answer = (
            f"The SQL query returned {total} record(s). "
            f"Showing page {page} of {pages}:\n\n{slice_}"
        )

        return {
            "answer": answer,
            "last_sql_query": generated_sql,
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": pages,
            "preview": slice_,
            "raw_result": df.to_dict(orient="records"),
        }

    finally:
        if created_session:
            session.close()
