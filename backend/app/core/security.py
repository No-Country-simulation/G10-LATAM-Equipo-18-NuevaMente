import os
import time
import hmac
import hashlib
import base64
import secrets
import sqlite3
import jwt
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, Response, Request
from app.core.config import settings

# Secret Keys
JWT_SECRET = getattr(settings, "JWT_SECRET", "nuevamente_secret_key_2026_jwt_token_auth_secure")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Password Hashing with PBKDF2-HMAC-SHA256
def hash_password(password: str) -> str:
    salt = b"nuevamente_pbkdf2_salt_2026"
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex()

def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed)

def init_auth_tables():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Instructor',
            organization TEXT,
            avatar_letter TEXT,
            is_verified INTEGER DEFAULT 1,
            mfa_enabled INTEGER DEFAULT 0,
            mfa_secret TEXT,
            mfa_backup_codes TEXT,
            created_at REAL NOT NULL
        )
    """)

    # Refresh Tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            device_info TEXT,
            ip_address TEXT,
            expires_at REAL NOT NULL,
            revoked INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Personal API Tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            token_prefix TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL,
            last_used_at REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Verification / Reset tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_tokens (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            token_type TEXT NOT NULL,
            token_code TEXT NOT NULL,
            expires_at REAL NOT NULL,
            created_at REAL NOT NULL
        )
    """)

    # Lockout / Rate limit tracker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            ip_or_email TEXT PRIMARY KEY,
            failed_count INTEGER DEFAULT 0,
            locked_until REAL DEFAULT 0
        )
    """)

    conn.commit()

    # Seed initial demo users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        demo_users = [
            ("usr_ana_001", "ana.martinez@empresa.com", "Ana Martinez", hash_password("password123"), "Instructor", "Educacion Corp", "A", 1, 0, None, None, time.time()),
            ("usr_fer_002", "fernando.garcia@empresa.com", "Fernando Garcia", hash_password("securepassword"), "Dev", "Tech Solutions", "F", 1, 0, None, None, time.time())
        ]
        cursor.executemany("""
            INSERT INTO users (id, email, name, password_hash, role, organization, avatar_letter, is_verified, mfa_enabled, mfa_secret, mfa_backup_codes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, demo_users)
        conn.commit()

    conn.close()

# Run DB migration init
init_auth_tables()

# JWT Access Token
def create_access_token(user_id: str, email: str, name: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
        "iss": "nuevamente-auth-api"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        if token.startswith("Bearer "):
            token = token.split(" ", 1)[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipo de token inválido.")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token de acceso ha expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token de acceso inválido.")

# Refresh Tokens & HttpOnly Cookies
def create_refresh_token(user_id: str, device_info: str = "Navegador Web", ip_address: str = "127.0.0.1") -> str:
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    token_id = f"ref_{secrets.token_hex(8)}"
    now = time.time()
    expires_at = now + REFRESH_TOKEN_EXPIRE_SECONDS

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO refresh_tokens (id, user_id, token_hash, device_info, ip_address, expires_at, revoked, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    """, (token_id, user_id, token_hash, device_info, ip_address, expires_at, now))
    conn.commit()
    conn.close()
    return raw_token

def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_SECONDS,
        path="/api/v1/auth"
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

def verify_and_rotate_refresh_token(raw_token: str, device_info: str = "Navegador Web", ip_address: str = "127.0.0.1") -> Tuple[Dict[str, Any], str]:
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.user_id, r.expires_at, r.revoked, u.email, u.name, u.role
        FROM refresh_tokens r
        JOIN users u ON r.user_id = u.id
        WHERE r.token_hash = ?
    """, (token_hash,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Refresh token inválido.")

    if row["revoked"] == 1:
        cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (row["user_id"],))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=401, detail="Detección de seguridad: Refresh token revocado.")

    if row["expires_at"] < time.time():
        conn.close()
        raise HTTPException(status_code=401, detail="El refresh token ha expirado.")

    cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()

    user_info = {
        "id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"]
    }
    new_raw_token = create_refresh_token(row["user_id"], device_info, ip_address)
    return user_info, new_raw_token

# TOTP MFA (RFC 6238)
def generate_totp_secret() -> str:
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode('utf-8')

def generate_totp_code(secret: str, time_step: int = 30) -> str:
    key = base64.b32decode(secret, casefold=True)
    t = int(time.time() // time_step)
    msg = t.to_bytes(8, byteorder='big')
    hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code = ((hmac_hash[offset] & 0x7F) << 24 |
            (hmac_hash[offset+1] & 0xFF) << 16 |
            (hmac_hash[offset+2] & 0xFF) << 8 |
            (hmac_hash[offset+3] & 0xFF)) % 1000000
    return f"{code:06d}"

def verify_totp_code(secret: str, code: str) -> bool:
    code = code.strip()
    current_time = int(time.time() // 30)
    for delta in [-1, 0, 1]:
        key = base64.b32decode(secret, casefold=True)
        t = (current_time + delta).to_bytes(8, byteorder='big')
        hmac_hash = hmac.new(key, t, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        expected = ((hmac_hash[offset] & 0x7F) << 24 |
                    (hmac_hash[offset+1] & 0xFF) << 16 |
                    (hmac_hash[offset+2] & 0xFF) << 8 |
                    (hmac_hash[offset+3] & 0xFF)) % 1000000
        if f"{expected:06d}" == code:
            return True
    return False

def generate_qr_svg_mock(email: str, secret: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="180" height="180" style="background:#fff; border-radius:12px; padding:12px;">
      <rect width="200" height="200" fill="#ffffff" />
      <g fill="#0f172a">
        <rect x="20" y="20" width="50" height="50" rx="6" fill="#0f172a"/>
        <rect x="30" y="30" width="30" height="30" rx="4" fill="#ffffff"/>
        <rect x="38" y="38" width="14" height="14" rx="2" fill="#6366f1"/>
        <rect x="130" y="20" width="50" height="50" rx="6" fill="#0f172a"/>
        <rect x="140" y="30" width="30" height="30" rx="4" fill="#ffffff"/>
        <rect x="148" y="38" width="14" height="14" rx="2" fill="#6366f1"/>
        <rect x="20" y="130" width="50" height="50" rx="6" fill="#0f172a"/>
        <rect x="30" y="140" width="30" height="30" rx="4" fill="#ffffff"/>
        <rect x="38" y="148" width="14" height="14" rx="2" fill="#6366f1"/>
        <rect x="80" y="20" width="15" height="15" fill="#0f172a"/>
        <rect x="100" y="35" width="20" height="15" fill="#6366f1"/>
        <rect x="80" y="60" width="30" height="15" fill="#0f172a"/>
        <rect x="80" y="90" width="40" height="20" fill="#6366f1"/>
        <rect x="130" y="90" width="25" height="25" fill="#0f172a"/>
        <rect x="160" y="120" width="20" height="20" fill="#6366f1"/>
        <rect x="80" y="130" width="35" height="15" fill="#0f172a"/>
        <rect x="125" y="145" width="30" height="35" fill="#0f172a"/>
      </g>
    </svg>'''

# API Tokens (`npm_` style)
def create_api_token(user_id: str, name: str, expires_in_days: int = 30) -> Tuple[str, Dict[str, Any]]:
    raw_token = f"npm_{secrets.token_hex(24)}"
    token_prefix = raw_token[:8]
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    token_id = f"tok_{secrets.token_hex(8)}"
    now = time.time()
    expires_at = now + (expires_in_days * 86400) if expires_in_days > 0 else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_tokens (id, user_id, name, token_hash, token_prefix, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (token_id, user_id, name, token_hash, token_prefix, now, expires_at))
    conn.commit()
    conn.close()

    token_info = {
        "id": token_id,
        "name": name,
        "token_prefix": token_prefix,
        "created_at": now,
        "expires_at": expires_at,
        "last_used_at": None
    }
    return raw_token, token_info

def verify_api_token(raw_token: str) -> Optional[Dict[str, Any]]:
    if not raw_token.startswith("npm_"):
        return None
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.user_id, t.expires_at, u.email, u.name, u.role
        FROM api_tokens t
        JOIN users u ON t.user_id = u.id
        WHERE t.token_hash = ?
    """, (token_hash,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    if row["expires_at"] and row["expires_at"] < time.time():
        conn.close()
        return None

    cursor.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (time.time(), row["id"]))
    conn.commit()
    conn.close()

    return {
        "id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"]
    }

# Brute force rate limit & lockout check
def check_rate_limit_and_lockout(key: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count, locked_until FROM login_attempts WHERE ip_or_email = ?", (key,))
    row = cursor.fetchone()

    if row:
        failed_count, locked_until = row["failed_count"], row["locked_until"]
        if locked_until > time.time():
            conn.close()
            remaining = int(locked_until - time.time())
            raise HTTPException(
                status_code=429,
                detail=f"Cuenta temporalmente bloqueada por demasiados intentos fallidos. Intente de nuevo en {remaining} segundos."
            )
    conn.close()

def record_failed_login(key: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count FROM login_attempts WHERE ip_or_email = ?", (key,))
    row = cursor.fetchone()
    now = time.time()

    if row:
        new_count = row["failed_count"] + 1
        locked_until = now + (15 * 60) if new_count >= 5 else 0
        cursor.execute("UPDATE login_attempts SET failed_count = ?, locked_until = ? WHERE ip_or_email = ?", (new_count, locked_until, key))
    else:
        cursor.execute("INSERT INTO login_attempts (ip_or_email, failed_count, locked_until) VALUES (?, 1, 0)", (key,))

    conn.commit()
    conn.close()

def reset_failed_login(key: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_attempts WHERE ip_or_email = ?", (key,))
    conn.commit()
    conn.close()

# User isolation helper for OCI Storage
def get_user_storage_prefix(user_id: str) -> str:
    return f"usuarios/{user_id}/"
