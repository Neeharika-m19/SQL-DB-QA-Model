# core/auth_utils.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select, or_
from db.model import get_session, User, UserInDBAPI

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_user(username: str, session: Session) -> UserInDBAPI | None:
    """
    Lookup a user by email OR name for login purposes.
    Returns a UserInDBAPI (with password) or None.
    """
    stmt = select(User).where(or_(User.email == username, User.name == username))
    result = session.exec(stmt).first()
    if not result:
        return None
    return UserInDBAPI(**result.dict())

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Treat the bearer token as the user's ID (stringified).
    Fetch the User record by PK.
    """
    try:
        user_id = int(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_user_id(
    current_user: User = Depends(get_current_user)
) -> int:
    return current_user.id
