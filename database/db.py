import os
import sys
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# Database connection URL
raw_db_url = os.getenv("DATABASE_URL", "")

# Detect Vercel serverless environment
is_vercel = bool(
    os.getenv("VERCEL") or 
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") or 
    os.getenv("NOW_REGION")
)

# Fix postgres:// legacy dialect prefix (Heroku/Neon/Supabase) to postgresql://
if raw_db_url and raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

# Default to SQLite if no external DB provided
if not raw_db_url:
    if is_vercel:
        raw_db_url = "sqlite:////tmp/news_monitor.db"
    else:
        raw_db_url = "sqlite:///news_monitor.db"
elif is_vercel and raw_db_url.startswith("sqlite:///"):
    sqlite_filename = raw_db_url.replace("sqlite:///", "")
    if not sqlite_filename.startswith("/tmp/"):
        raw_db_url = f"sqlite:////tmp/{os.path.basename(sqlite_filename)}"

# Engine configuration
engine_kwargs = {
    "echo": False
}

if raw_db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in raw_db_url or raw_db_url == "sqlite://":
        engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_pre_ping"] = True

try:
    engine = create_engine(raw_db_url, **engine_kwargs)
except Exception as e:
    print(f"[WARN] Failed to connect to {raw_db_url}: {e}. Falling back to in-memory StaticPool SQLite.", file=sys.stderr)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine))


def init_db():
    """Create all database tables if they do not exist."""
    import database.models  # Ensure models are registered with Base
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations with idempotent schema creation."""
    # Guarantees tables exist even on fresh ephemeral serverless containers
    import database.models
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
