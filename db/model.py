from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine
from datetime import datetime
from typing import Optional
import os


# Define models
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    email: str
    password: str
    fernet_key: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Connection(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    db_user: Optional[str]
    db_password: Optional[str]
    db_host: Optional[str]
    db_port: Optional[int]
    db_type: str
    connection_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class Query(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    connection_id: int = Field(foreign_key="connection.id", nullable=False)
    query_key: str

class APIKey(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    provider: str = Field(nullable=False)
    encrypted_key: str = Field(nullable=False)

# Dynamically resolve the correct path to db_llm.sqlite3
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "..", "data", "db_llm.sqlite3")
db_uri = f"sqlite:///{os.path.abspath(db_path)}"

# SQLite engine
connect_args = {"check_same_thread": False}
engine = create_engine(db_uri, connect_args=connect_args)

def get_session():
    with Session(engine) as session:
        yield session

# Pydantic models
class UserAPI(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserInDBAPI(UserAPI):
    password: str

class ConnectionInput(BaseModel):
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_type: str
    connection_name: str
