import os
import sys
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()

# Database connection URL
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///news_monitor.db")

# Fix postgres:// legacy dialect prefix (Heroku/Neon/Supabase) to postgresql://
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

# Handle Vercel serverless environment:
# If running on Vercel without an external Postgres DB, SQLite in current dir will fail
# because the root filesystem is read-only. We route local SQLite to /tmp on Vercel.
is_vercel = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if is_vercel and raw_db_url.startswith("sqlite:///"):
    sqlite_filename = raw_db_url.replace("sqlite:///", "")
    if not sqlite_filename.startswith("/tmp/"):
        raw_db_url = f"sqlite:////tmp/{os.path.basename(sqlite_filename)}"

# Engine configuration
connect_args = {}
if raw_db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        raw_db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False
    )
except Exception as e:
    # Fallback to local memory SQLite if connection fails
    print(f"[WARN] Failed to connect to {raw_db_url}: {e}. Falling back to in-memory SQLite.", file=sys.stderr)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine))


_initialized = False


def init_db():
    """Create all database tables if they do not exist."""
    global _initialized
    import database.models  # Ensure models are registered with Base
    Base.metadata.create_all(bind=engine)
    _initialized = True


@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations."""
    global _initialized
    if not _initialized:
        try:
            init_db()
        except Exception as e:
            print(f"[WARN] Error in get_db auto init_db: {e}", file=sys.stderr)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
