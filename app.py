from fastapi import Depends, Query, HTTPException, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, SQLModel, update
from typing import Annotated
from cryptography.fernet import Fernet
import httpx

from core.db import get_dialect_table_names, engine, get_session
from core.llm import answer_my_question
from core.api_keys import create_or_update_api_key, delete_api_key
from core.s3_utils import save_query_to_s3, list_saved_queries_from_s3, delete_query_from_s3
from core.auth_utils import get_current_user_id, get_user
from db.model import User, Connection, ConnectionInput, APIKey

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# CORS for your React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # add "http://127.0.0.1:5173" if you use that too
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/", include_in_schema=False)
def home():
    return "Welcome to DB LLM"

# -------- Auth --------

@app.post("/register")
def register(
    user: User,
    session: Session = Depends(get_session),
):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    user = get_user(form_data.username, session)
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": str(user.id), "token_type": "bearer"}

# -------- Fernet --------

@app.post("/generate_fernet_key")
def generate_fernet_key(
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    key = Fernet.generate_key().decode()
    session.exec(update(User).where(User.id == user_id).values(fernet_key=key))
    session.commit()
    return {"fernet_key": key}

# -------- Providers/Models --------

@app.get("/providers")
def list_providers():
    return {"providers": ["openai", "together"]}

@app.get("/models")
def list_models(
    provider: Annotated[str, Query(..., description="LLM provider")],
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    # Find and decrypt the stored API key for this provider
    key_row = session.exec(
        select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)
    ).first()
    if not key_row:
        raise HTTPException(status_code=404, detail=f"No API key for {provider}")

    user = session.get(User, user_id)
    if not user or not user.fernet_key:
        raise HTTPException(status_code=400, detail="Fernet key not set")

    api_key = Fernet(user.fernet_key.encode()).decrypt(
        key_row.encrypted_key.encode()
    ).decode()

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        if provider == "openai":
            url = "https://api.openai.com/v1/models"
            resp = httpx.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("data", []) if isinstance(data, dict) else []
        elif provider == "together":
            # ✅ Correct API path; Together sometimes returns a list directly
            url = "https://api.together.xyz/v1/models"
            resp = httpx.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                raw = data.get("data") or data.get("models", []) or []
            elif isinstance(data, list):
                raw = data
            else:
                raw = []
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

        # Normalize items → model ids
        models = []
        for m in raw:
            if isinstance(m, dict):
                mid = m.get("id") or m.get("name") or m.get("model") or m.get("slug")
                if mid:
                    models.append(mid)
            elif isinstance(m, str):
                models.append(m)

        # dedupe and sort for nicer UX
        models = sorted(set(models))
        return {"provider": provider, "models": models}

    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response is not None else str(e)
        # Common Together gotcha: redirect to /signin
        if e.response is not None and e.response.status_code in (301, 302, 303, 307, 308):
            detail = (
                f"Got redirect ({e.response.status_code}) from {e.request.url}. "
                f"Ensure you call /v1/models and the API key is valid."
            )
        raise HTTPException(status_code=e.response.status_code if e.response else 502, detail=detail)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))

# -------- Connections / DB info --------

@app.get("/db_info")
def get_db_info(
    db_name: str = Query(..., alias="db_name"),
    user_id: int = Depends(get_current_user_id),
):
    return get_dialect_table_names(user_id, db_name)

@app.get("/list_connections")
def list_connections(
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    return session.exec(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

@app.post("/new_connection")
def add_new_connection(
    connection_input: ConnectionInput,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    conn = Connection(**connection_input.dict(), user_id=user_id)
    session.add(conn)
    session.commit()
    session.refresh(conn)
    return {"connection_id": conn.id}

# -------- Answer --------

@app.get("/answer")
def get_answer(
    question: str,
    connection_name: str,
    provider: str = "openai",
    model: str = "gpt-4o",
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1),
    save: bool = Query(False),
    query_key: str | None = Query(None),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = answer_my_question(
            question=question,
            user_id=user_id,
            db_name=connection_name,
            model_name=model,
            provider=provider,
            page=page,
            page_size=page_size,
            session=session,   # ← important: pass the session
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Answer failed: {e.detail} | file_name={connection_name}",
        )

    if save:
        if not query_key:
            raise HTTPException(status_code=400, detail="query_key required when save=true")
        save_query_to_s3(
            user_id=user_id,
            query_key=query_key,
            question=question,
            sql_query=result["last_sql_query"],
            answer=result["answer"],
        )
    return result

# -------- Saved queries --------

@app.post("/save_query")
def save_query(
    query_key: str,
    question: str,
    sql_query: str,
    answer: str,
    user_id: int = Depends(get_current_user_id),
):
    save_query_to_s3(user_id, query_key, question, sql_query, answer)
    return {"message": "Saved"}

@app.get("/list_saved_queries")
def list_saved(user_id: int = Depends(get_current_user_id)):
    return {"saved_queries": list_saved_queries_from_s3(user_id)}

@app.delete("/delete_query")
def delete_query(
    query_key: str,
    user_id: int = Depends(get_current_user_id),
):
    msg = delete_query_from_s3(user_id, query_key)
    return {"message": msg}

# -------- API key storage --------

@app.post("/api_keys")
def upsert_key(
    provider: str = Query(...),
    api_key: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    return {"message": create_or_update_api_key(session, user_id, provider, api_key)}

@app.delete("/api_keys")
def delete_key(
    provider: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    return {"message": delete_api_key(session, user_id, provider)}
