import os
from pathlib import Path
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(Path(basedir) / ".env")

# Single source of truth: default DB connection string (used when .env is missing or has placeholder)
DEFAULT_DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/ndfa_memory_game"


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ndfa-memory-secret-key-change-in-production"

    # Connection string: from .env only if set and not placeholder; otherwise use DEFAULT_DATABASE_URI from this file.
    _db_url = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://").strip()
    if not _db_url or "YOUR_PASSWORD" in _db_url:
        _db_url = DEFAULT_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT")

    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    FLASK_ENV = "development"


# Log the connection string in use (from this config file) when config is loaded
print("[config] SQLALCHEMY_DATABASE_URI =", Config.SQLALCHEMY_DATABASE_URI)
