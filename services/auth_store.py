# services/auth_store.py
"""Persistent user store for authentication.

Backend is chosen from the environment:
  • SUPABASE_URL + SUPABASE_SERVICE_KEY  -> Supabase (Postgres, via the REST API).
    Persistent and shared across deploys.
  • otherwise                            -> a local SQLite file (dev fallback,
    non-persistent on an ephemeral host).

No Streamlit imports — pure data layer.
"""
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("auth_store")

TABLE = "devpulse_users"


# ══════════════════════════════════════════════════════════════════════
# Supabase backend (preferred)
# ══════════════════════════════════════════════════════════════════════
_sb_client = None
_sb_checked = False


def _supabase():
    """Return a cached Supabase client, or None when not configured."""
    global _sb_client, _sb_checked
    if _sb_checked:
        return _sb_client
    _sb_checked = True
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if url and key:
        try:
            from supabase import create_client
            _sb_client = create_client(url, key)
            logger.info("Auth store: Supabase backend ready")
        except Exception as e:  # noqa: BLE001
            logger.error("Supabase client init failed, falling back to SQLite: %s", e)
            _sb_client = None
    return _sb_client


def backend_name() -> str:
    return "Supabase" if _supabase() is not None else "SQLite (local)"


# ══════════════════════════════════════════════════════════════════════
# SQLite fallback (SQLAlchemy)
# ══════════════════════════════════════════════════════════════════════
def _sqlite_engine():
    from sqlalchemy import (Column, DateTime, MetaData, String, Table,
                            create_engine)
    global _sqlite_meta, _sqlite_users, _sqlite_eng
    if getattr(_sqlite_engine, "_ready", False):
        return _sqlite_eng, _sqlite_users
    meta = MetaData()
    users = Table(
        "users", meta,
        Column("username", String(64), primary_key=True),
        Column("email", String(255)),
        Column("name", String(255)),
        Column("password_hash", String(255), nullable=False),
        Column("created_at", DateTime),
    )
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth.db")
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    meta.create_all(eng)
    _sqlite_eng, _sqlite_users = eng, users
    _sqlite_engine._ready = True
    return eng, users


# ══════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════
def load_credentials() -> dict:
    """All users in streamlit-authenticator's credentials shape."""
    creds = {"usernames": {}}
    sb = _supabase()
    try:
        if sb is not None:
            rows = sb.table(TABLE).select(
                "username,email,name,password_hash").execute().data or []
        else:
            from sqlalchemy import select
            eng, users = _sqlite_engine()
            with eng.connect() as conn:
                rows = [dict(r) for r in conn.execute(select(users)).mappings()]
        for r in rows:
            creds["usernames"][r["username"]] = {
                "email": r.get("email") or "",
                "name": r.get("name") or r["username"],
                "password": r["password_hash"],
                "failed_login_attempts": 0,
                "logged_in": False,
            }
    except Exception as e:  # noqa: BLE001 - never crash the login screen on a DB hiccup
        logger.error("load_credentials failed: %s", e)
    return creds


def user_exists(username: str) -> bool:
    sb = _supabase()
    try:
        if sb is not None:
            r = sb.table(TABLE).select("username").eq(
                "username", username).limit(1).execute()
            return bool(r.data)
        from sqlalchemy import select
        eng, users = _sqlite_engine()
        with eng.connect() as conn:
            return conn.execute(
                select(users.c.username).where(users.c.username == username)
            ).first() is not None
    except Exception as e:  # noqa: BLE001
        logger.error("user_exists failed: %s", e)
        return False


def upsert_user(username: str, name: str, email: str, password_hash: str) -> bool:
    """Insert a new user or update an existing one (keyed on username)."""
    sb = _supabase()
    try:
        if sb is not None:
            sb.table(TABLE).upsert({
                "username": username, "name": name,
                "email": email, "password_hash": password_hash,
            }).execute()
            return True
        from sqlalchemy import insert, update
        eng, users = _sqlite_engine()
        now = datetime.now(timezone.utc)
        with eng.begin() as conn:
            if user_exists(username):
                conn.execute(update(users).where(users.c.username == username).values(
                    name=name, email=email, password_hash=password_hash))
            else:
                conn.execute(insert(users).values(
                    username=username, name=name, email=email,
                    password_hash=password_hash, created_at=now))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("upsert_user failed: %s", e)
        return False
