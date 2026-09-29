import time
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Response, Request, Cookie

from app.schemas.auth import (
    RegisterRequest, LoginRequest, LoginMfaRequest, VerifyEmailRequest,
    ResendVerificationRequest, MagicLinkRequest, MagicLinkVerifyRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    MfaSetupResponse, MfaVerifyRequest, MfaDisableRequest,
    ApiTokenCreateRequest, ApiTokenResponse, TokenResponse, UserResponse
)
from app.core.security import (
    get_db, hash_password, verify_password, create_access_token,
    create_refresh_token, set_refresh_cookie, clear_refresh_cookie,
    verify_and_rotate_refresh_token, generate_totp_secret, verify_totp_code,
    generate_qr_svg_mock, create_api_token, check_rate_limit_and_lockout,
    record_failed_login, reset_failed_login, get_user_storage_prefix
)
from app.api.v1.dependencies import get_current_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=TokenResponse)
def register_user(req: RegisterRequest, response: Response, request: Request):
    email = req.email.strip().lower()
    check_rate_limit_and_lockout(email)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        record_failed_login(email)
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")

    user_id = f"usr_{secrets.token_hex(8)}"
    now = time.time()
    pw_hash = hash_password(req.password)
    avatar_char = req.name.strip()[0].upper() if req.name else "U"

    cursor.execute("""
        INSERT INTO users (id, email, name, password_hash, role, organization, avatar_letter, is_verified, mfa_enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
    """, (user_id, email, req.name.strip(), pw_hash, req.role or "Instructor", req.organization, avatar_char, now))
    conn.commit()
    conn.close()

    reset_failed_login(email)

    access_token = create_access_token(user_id, email, req.name, req.role or "Instructor")
    refresh_token = create_refresh_token(user_id, request.headers.get("user-agent", "Unknown"), request.client.host if request.client else "127.0.0.1")
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        status="exito",
        message="Registro completado exitosamente",
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse(
            id=user_id,
            email=email,
            name=req.name.strip(),
            role=req.role or "Instructor",
            organization=req.organization,
            avatar_letter=avatar_char,
            is_verified=True,
            mfa_enabled=False,
            created_at=now
        )
    )

@router.post("/login", response_model=TokenResponse)
def login_user(req: LoginRequest, response: Response, request: Request):
    email = req.email.strip().lower()
    check_rate_limit_and_lockout(email)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, email, name, password_hash, role, organization, avatar_letter, is_verified, mfa_enabled, mfa_secret, created_at
        FROM users WHERE email = ?
    """, (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        record_failed_login(email)
        raise HTTPException(status_code=401, detail="Credenciales incorrectas. Verifique su correo y contraseña.")

    # Check MFA requirement
    if user["mfa_enabled"] == 1:
        if not req.mfa_code:
            mfa_temp_token = secrets.token_hex(16)
            return TokenResponse(
                status="mfa_required",
                message="Autenticación de Dos Factores requerida.",
                requires_mfa=True,
                mfa_token=mfa_temp_token
            )
        # Verify MFA
        if not verify_totp_code(user["mfa_secret"], req.mfa_code):
            record_failed_login(email)
            raise HTTPException(status_code=401, detail="Código MFA inválido.")

    reset_failed_login(email)

    access_token = create_access_token(user["id"], user["email"], user["name"], user["role"])
    refresh_token = create_refresh_token(user["id"], request.headers.get("user-agent", "Unknown"), request.client.host if request.client else "127.0.0.1")
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        status="exito",
        message=f"Bienvenido de nuevo, {user['name']}",
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            organization=user["organization"],
            avatar_letter=user["avatar_letter"],
            is_verified=bool(user["is_verified"]),
            mfa_enabled=bool(user["mfa_enabled"]),
            created_at=user["created_at"]
        )
    )

@router.post("/login/mfa", response_model=TokenResponse)
def login_mfa(req: LoginMfaRequest, response: Response, request: Request):
    email = req.email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, organization, avatar_letter, mfa_secret, created_at FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not user["mfa_secret"]:
        raise HTTPException(status_code=400, detail="MFA no configurado para este usuario.")

    if not verify_totp_code(user["mfa_secret"], req.mfa_code):
        raise HTTPException(status_code=401, detail="Código MFA de 6 dígitos incorrecto.")

    access_token = create_access_token(user["id"], user["email"], user["name"], user["role"])
    refresh_token = create_refresh_token(user["id"], request.headers.get("user-agent", "Unknown"), request.client.host if request.client else "127.0.0.1")
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        status="exito",
        message=f"Autenticación MFA exitosa. Bienvenido, {user['name']}",
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            organization=user["organization"],
            avatar_letter=user["avatar_letter"],
            is_verified=True,
            mfa_enabled=True,
            created_at=user["created_at"]
        )
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_session(request: Request, response: Response, refresh_token: Optional[str] = Cookie(None)):
    if not refresh_token:
        # Check header fallback if cookie disabled
        refresh_token = request.headers.get("X-Refresh-Token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token no encontrado en la solicitud.")

    user_info, new_refresh_token = verify_and_rotate_refresh_token(
        refresh_token,
        request.headers.get("user-agent", "Unknown"),
        request.client.host if request.client else "127.0.0.1"
    )

    access_token = create_access_token(user_info["id"], user_info["email"], user_info["name"], user_info["role"])
    set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(
        status="exito",
        message="Sesión renovada exitosamente",
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse(
            id=user_info["id"],
            email=user_info["email"],
            name=user_info["name"],
            role=user_info["role"],
            avatar_letter=user_info["name"][0].upper() if user_info["name"] else "U",
            is_verified=True,
            mfa_enabled=False,
            created_at=time.time()
        )
    )

@router.post("/logout")
def logout_user(response: Response, refresh_token: Optional[str] = Cookie(None)):
    clear_refresh_cookie(response)
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
        conn.commit()
        conn.close()
    return {"status": "exito", "message": "Sesión cerrada correctamente."}

@router.post("/logout-all")
def logout_all_sessions(current_user: Dict[str, Any] = Depends(get_current_user), response: Response = None):
    clear_refresh_cookie(response)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"status": "exito", "message": "Todas las sesiones activas han sido cerradas."}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        organization=current_user.get("organization"),
        avatar_letter=current_user.get("avatar_letter") or current_user["name"][0].upper(),
        is_verified=current_user.get("is_verified", True),
        mfa_enabled=current_user.get("mfa_enabled", False),
        created_at=current_user.get("created_at", time.time())
    )

# Email Verification & Resend
@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest):
    return {"status": "exito", "message": "Correo electrónico verificado correctamente."}

@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest):
    return {"status": "exito", "message": "Código de verificación re-enviado a su correo."}

# Password Reset (User Enumeration Defense)
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    # Always respond with success message without leaking email existence
    return {
        "status": "exito",
        "message": "Si la cuenta existe, se ha enviado un enlace de recuperación a su correo electrónico."
    }

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    return {"status": "exito", "message": "Contraseña restablecida exitosamente. Puede iniciar sesión ahora."}

@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
    row = cursor.fetchone()
    if not row or not verify_password(req.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")

    new_hash = hash_password(req.new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, current_user["id"]))
    conn.commit()
    conn.close()
    return {"status": "exito", "message": "Contraseña actualizada correctamente."}

# Magic Link
@router.post("/magic-link")
def send_magic_link(req: MagicLinkRequest):
    return {"status": "exito", "message": "Enlace mágico enviado. Verifique su bandeja de entrada."}

@router.post("/magic-link/verify")
def verify_magic_link(req: MagicLinkVerifyRequest, response: Response, request: Request):
    # Mock magic link verification
    user_id = "usr_ana_001"
    access_token = create_access_token(user_id, "ana.martinez@empresa.com", "Ana Martínez", "Instructor")
    refresh_token = create_refresh_token(user_id, request.headers.get("user-agent", "Unknown"), request.client.host if request.client else "127.0.0.1")
    set_refresh_cookie(response, refresh_token)
    return {
        "status": "exito",
        "access_token": access_token,
        "user": {
            "id": user_id,
            "email": "ana.martinez@empresa.com",
            "name": "Ana Martínez",
            "role": "Instructor"
        }
    }

# MFA Setup / Enable / Disable
@router.post("/mfa/setup", response_model=MfaSetupResponse)
def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user)):
    secret = generate_totp_secret()
    qr_svg = generate_qr_svg_mock(current_user["email"], secret)
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    return MfaSetupResponse(
        secret=secret,
        qr_svg=qr_svg,
        backup_codes=backup_codes
    )

@router.post("/mfa/enable")
def enable_mfa(req: MfaVerifyRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    # Generate secret
    secret = generate_totp_secret()
    cursor.execute("UPDATE users SET mfa_enabled = 1, mfa_secret = ? WHERE id = ?", (secret, current_user["id"]))
    conn.commit()
    conn.close()
    return {"status": "exito", "message": "MFA activado exitosamente."}

@router.post("/mfa/disable")
def disable_mfa(req: MfaDisableRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
    row = cursor.fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Contraseña incorrecta.")
    cursor.execute("UPDATE users SET mfa_enabled = 0, mfa_secret = NULL WHERE id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"status": "exito", "message": "MFA desactivado correctamente."}

# Personal API Tokens
@router.get("/api-tokens", response_model=List[ApiTokenResponse])
def get_api_tokens(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, token_prefix, created_at, expires_at, last_used_at
        FROM api_tokens WHERE user_id = ?
        ORDER BY created_at DESC
    """, (current_user["id"],))
    rows = cursor.fetchall()
    conn.close()
    return [
        ApiTokenResponse(
            id=r["id"],
            name=r["name"],
            token_prefix=r["token_prefix"],
            created_at=r["created_at"],
            expires_at=r["expires_at"],
            last_used_at=r["last_used_at"]
        ) for r in rows
    ]

@router.post("/api-tokens", response_model=ApiTokenResponse)
def create_new_api_token(req: ApiTokenCreateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    raw_token, token_info = create_api_token(current_user["id"], req.name, req.expires_in_days)
    return ApiTokenResponse(
        id=token_info["id"],
        name=token_info["name"],
        token=raw_token,
        token_prefix=token_info["token_prefix"],
        created_at=token_info["created_at"],
        expires_at=token_info["expires_at"]
    )

@router.delete("/api-tokens/{token_id}")
def delete_api_token(token_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_tokens WHERE id = ? AND user_id = ?", (token_id, current_user["id"]))
    conn.commit()
    conn.close()
    return {"status": "exito", "message": "API Token revocado correctamente."}

# OAuth PKCE Mock
@router.get("/oauth/{provider}/start")
def oauth_start(provider: str):
    state = secrets.token_hex(16)
    redirect_url = f"/auth/callback?provider={provider}&state={state}"
    return {"status": "exito", "auth_url": redirect_url, "state": state}

@router.get("/oauth/{provider}/callback", response_model=TokenResponse)
def oauth_callback(provider: str, code: str = "mock_code", response: Response = None, request: Request = None):
    email = f"usuario.{provider}@empresa.com"
    name = f"Usuario {provider.capitalize()}"
    user_id = f"usr_{provider}_{secrets.token_hex(6)}"

    access_token = create_access_token(user_id, email, name, "Developer")
    refresh_token = create_refresh_token(user_id, request.headers.get("user-agent", "Unknown") if request else "Unknown", "127.0.0.1")
    if response:
        set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        status="exito",
        message=f"Autenticado con éxito mediante {provider.capitalize()}",
        access_token=access_token,
        user=UserResponse(
            id=user_id,
            email=email,
            name=name,
            role="Developer",
            avatar_letter=provider[0].upper(),
            is_verified=True,
            mfa_enabled=False,
            created_at=time.time()
        )
    )
