import hashlib
import sqlite3
import time
import os
from typing import Optional, Dict, Any
import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# JWT Settings
JWT_SECRET = getattr(settings, "JWT_SECRET", "nuevamente_secret_key_2026_jwt_token_auth_secure")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 days

# Path to SQLite DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()

    # Seed initial demo accounts if table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_users = [
            ("ana.martinez@empresa.com", "Ana Martínez", hashlib.sha256("password123nuevamente_salt".encode()).hexdigest(), time.time()),
            ("fernando.garcia@empresa.com", "Fernando García", hashlib.sha256("securepasswordnuevamente_salt".encode()).hexdigest(), time.time())
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", seed_users)
        conn.commit()
    conn.close()

# Initialize DB on module import
init_db()

def get_user_from_db(email: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, name, password_hash, created_at FROM users WHERE email = ?", (email.lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "email": row[0],
            "name": row[1],
            "password_hash": row[2],
            "created_at": row[3]
        }
    return None

def save_user_to_db(email: str, name: str, password_hash: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = time.time()
    cursor.execute(
        "INSERT OR REPLACE INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (email.lower(), name, password_hash, now)
    )
    conn.commit()
    conn.close()
    return {
        "email": email.lower(),
        "name": name,
        "password_hash": password_hash,
        "created_at": now
    }

class LoginRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

def hash_password(password: str) -> str:
    salt = "nuevamente_salt"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def create_jwt_token(email: str, name: str) -> str:
    now = int(time.time())
    payload = {
        "sub": email,
        "name": name,
        "iat": now,
        "exp": now + JWT_EXPIRE_SECONDS,
        "iss": "nuevamente-auth-api"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    try:
        if token.startswith("Bearer "):
            token = token.split(" ", 1)[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token de autenticación ha expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación inválido.")

def extract_name(email: str, provided_name: Optional[str] = None) -> str:
    if provided_name and provided_name.strip():
        return provided_name.strip()
    if not email:
        return "Usuario Registrado"
    parts = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ')
    return parts.title() if parts else "Usuario Registrado"

@router.post("/auth/register")
def register_user(request: RegisterRequest):
    email = request.email.strip().lower()
    name = request.name.strip()
    password = request.password.strip()

    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Nombre, correo electrónico y contraseña son requeridos.")
    
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres.")

    existing_user = get_user_from_db(email)
    if existing_user:
        # Update user name/password
        hashed = hash_password(password)
        save_user_to_db(email, name, hashed)
    else:
        hashed = hash_password(password)
        save_user_to_db(email, name, hashed)

    token = create_jwt_token(email, name)
    avatar_char = name[0].upper() if name else "U"

    return {
        "status": "exito",
        "message": f"Cuenta registrada exitosamente en la base de datos para {name}",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": name,
            "email": email,
            "avatarLetter": avatar_char,
            "isLoggedIn": True
        }
    }

@router.post("/auth/login")
def login_user(request: LoginRequest):
    email = request.email.strip().lower()
    password = request.password.strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="El correo electrónico y la contraseña son requeridos.")

    user_record = get_user_from_db(email)
    if user_record:
        if user_record["password_hash"] != hash_password(password):
            raise HTTPException(status_code=401, detail="Contraseña incorrecta. Por favor verifica tus credenciales.")
        user_name = user_record["name"]
    else:
        user_name = extract_name(email, request.name)
        save_user_to_db(email, user_name, hash_password(password))

    token = create_jwt_token(email, user_name)
    avatar_char = user_name[0].upper() if user_name else "U"

    return {
        "status": "exito",
        "message": f"Bienvenido de nuevo, {user_name}",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": user_name,
            "email": email,
            "avatarLetter": avatar_char,
            "isLoggedIn": True
        }
    }

@router.post("/auth/google")
def google_auth(request: GoogleAuthRequest):
    email = (request.email.strip().lower()) if request.email else "usuario.google@gmail.com"
    name = request.name.strip() if request.name else extract_name(email)

    user_record = get_user_from_db(email)
    if not user_record:
        save_user_to_db(email, name, hash_password("google_sso_pass"))

    token = create_jwt_token(email, name)
    avatar_char = name[0].upper() if name else "G"

    return {
        "status": "exito",
        "message": f"Autenticado correctamente con Google como {name}",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": name,
            "email": email,
            "avatarLetter": avatar_char,
            "isLoggedIn": True
        }
    }

@router.get("/auth/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Header Authorization con token Bearer es requerido.")
    payload = decode_jwt_token(authorization)
    email = payload.get("sub", "")
    name = payload.get("name", "")
    avatar_char = name[0].upper() if name else "U"

    return {
        "status": "exito",
        "user": {
            "name": name,
            "email": email,
            "avatarLetter": avatar_char,
            "isLoggedIn": True
        }
    }
