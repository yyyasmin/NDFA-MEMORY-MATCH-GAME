# Create or recreate DB tables from SQLAlchemy models (NDFA Memory Game).
# Run from backend folder: python db_create.py
# Uses the connection string from config.py (default: postgres:postgres@localhost:5432/ndfa_memory_game).
# Creates the database if it does not exist.

from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Optional: load .env if present (e.g. to override DATABASE_URL)
load_dotenv(Path(__file__).resolve().parent / ".env")

from config import DEFAULT_DATABASE_URI
from app import app, db
from models import Player, Room, RoomPlayer

# Log connection string so we can confirm we're using the correct one from config
_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
print("")
print("[db_create] Connection string in use (from config):")
print("  ", _uri)
print("[db_create] Expected default (config.DEFAULT_DATABASE_URI):")
print("  ", DEFAULT_DATABASE_URI)
print("[db_create] Using correct connection string:", _uri == DEFAULT_DATABASE_URI)
print("")


def ensure_database_exists(uri):
    """Create the database if it does not exist (connects to 'postgres' first)."""
    parsed = urlparse(uri)
    db_name = parsed.path.lstrip("/") or parsed.path
    if not db_name:
        return
    # Build URI for the default 'postgres' database to run CREATE DATABASE
    base = uri.rsplit("/", 1)[0]
    postgres_uri = base + "/postgres"
    try:
        conn = psycopg2.connect(postgres_uri)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"[db_create] Created database: {db_name}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[db_create] Could not ensure database exists: {e}")
        raise


def db_drop_everything(app, db):
    """Drop all tables and recreate from models."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    ensure_database_exists(uri)
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Tables dropped and recreated.")


def db_init_only(app, db):
    """Create database if needed and create tables if they do not exist. Safe for deploy (no drop)."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    ensure_database_exists(uri)
    with app.app_context():
        db.create_all()
        print("Tables ensured (create_all).")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        db_init_only(app, db)
    else:
        db_drop_everything(app, db)
