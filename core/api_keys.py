# core/api_keys.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from db.model import get_session, APIKey, User
from core.encryption_util import encrypt_api_key, decrypt_api_key
from core.auth_utils import get_current_user_id

router = APIRouter(prefix="/api_keys", tags=["API Keys"])


@router.post("/add")
def add_api_key(
    provider: str = Query(...),
    api_key: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    return _create_or_update_api_key(session, user_id, provider, api_key, create_only=True)


@router.put("/update")
def update_api_key(
    provider: str = Query(...),
    api_key: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    return _create_or_update_api_key(session, user_id, provider, api_key, update_only=True)


@router.get("/get")
def get_api_key(
    provider: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    key_entry = session.exec(select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)).first()
    if not key_entry:
        raise HTTPException(status_code=404, detail="API key not found.")

    user = session.get(User, user_id)
    if not user or not user.fernet_key:
        raise HTTPException(status_code=400, detail="Fernet key not set for user.")

    decrypted = decrypt_api_key(key_entry.encrypted_key, user.fernet_key)
    return {"provider": provider, "api_key": decrypted}


@router.delete("/delete")
def delete_api_key_route(
    provider: str = Query(...),
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    return {"message": delete_api_key(session, user_id, provider)}


@router.get("/list")
def list_api_providers(
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    entries = session.exec(select(APIKey).where(APIKey.user_id == user_id)).all()
    return {"providers": [entry.provider for entry in entries]}


# === Reusable utility functions ===

def create_or_update_api_key(session: Session, user_id: int, provider: str, api_key: str) -> str:
    return _create_or_update_api_key(session, user_id, provider, api_key)["message"]


def delete_api_key(session: Session, user_id: int, provider: str) -> str:
    key = session.exec(select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)).first()
    if not key:
        raise Exception(f"No API key found for provider: {provider}")
    session.delete(key)
    session.commit()
    return f"API key for {provider} deleted successfully."


def _create_or_update_api_key(session: Session, user_id: int, provider: str, api_key: str,
                              create_only=False, update_only=False) -> dict:
    user = session.get(User, user_id)
    if not user or not user.fernet_key:
        raise HTTPException(status_code=400, detail="Fernet key not set for user.")

    encrypted = encrypt_api_key(api_key, user.fernet_key)

    existing = session.exec(select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)).first()

    if create_only:
        if existing:
            raise HTTPException(status_code=400, detail="API key already exists. Use update instead.")
        session.add(APIKey(user_id=user_id, provider=provider, encrypted_key=encrypted))
        session.commit()
        return {"message": f"API key for {provider} added successfully."}

    if update_only:
        if not existing:
            raise HTTPException(status_code=404, detail="API key not found. Use add instead.")
        # Re-fetch to ensure it's managed in this session
        existing = session.get(APIKey, existing.id)
        if existing is None:
            raise HTTPException(status_code=500, detail="API key entry vanished during update.")

        existing.encrypted_key = encrypted
        session.add(existing)
        session.commit()
        return {"message": f"API key for {provider} updated successfully."}

    # If neither create_only nor update_only
    if existing:
        existing = session.get(APIKey, existing.id)
        if existing is None:
            raise HTTPException(status_code=500, detail="API key entry vanished during update.")

        existing.encrypted_key = encrypted
        session.add(existing)
        message = f"API key for {provider} updated successfully."
    else:
        session.add(APIKey(user_id=user_id, provider=provider, encrypted_key=encrypted))
        message = f"API key for {provider} added successfully."

    session.commit()
    return {"message": message}


# ✅ NEW: For provider modules like openai_provider.py
def get_api_key_for_user(session: Session, user_id: int, provider: str) -> str:
    key_entry = session.exec(select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == provider)).first()
    if not key_entry:
        return None
    return key_entry.encrypted_key
