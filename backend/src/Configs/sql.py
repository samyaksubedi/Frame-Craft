from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session
from Configs.env import DATABASE_URL, SQL_ECHO


SRC_DIR = Path(__file__).resolve().parents[1]


def _database_url() -> str:
    url = DATABASE_URL or "sqlite:///./thumbnailbuilder.db"
    sqlite_prefix = "sqlite:///"
    if not url.startswith(sqlite_prefix):
        return url

    raw_path = url.removeprefix(sqlite_prefix)
    if raw_path == ":memory:":
        return url
    database_path = Path(raw_path)
    if not database_path.is_absolute():
        database_path = (SRC_DIR / database_path).resolve()
    return f"{sqlite_prefix}{database_path.as_posix()}"


database_url = _database_url()
connect_args = (
    {"check_same_thread": False, "timeout": 30}
    if database_url.startswith("sqlite:")
    else {}
)
engine = create_engine(
    database_url, echo=SQL_ECHO, connect_args=connect_args
)


def create_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
