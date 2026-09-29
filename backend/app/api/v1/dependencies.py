from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from app.core.security import decode_access_token, verify_api_token, get_db

def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    # 1. Try API Key if provided
    if x_api_key:
        user = verify_api_token(x_api_key)
        if user:
            return user
        raise HTTPException(status_code=401, detail="API Token inválido o expirado.")

    # 2. Try Authorization Bearer JWT Token
    if authorization:
        payload = decode_access_token(authorization)
        user_id = payload.get("sub")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, role, organization, avatar_letter, is_verified, mfa_enabled, created_at FROM users WHERE id = ? OR email = ?", (user_id, payload.get("email")))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "organization": row["organization"],
                "avatar_letter": row["avatar_letter"],
                "is_verified": bool(row["is_verified"]),
                "mfa_enabled": bool(row["mfa_enabled"]),
                "created_at": row["created_at"]
            }
        
        # Fallback if DB user was seeded without DB lookup
        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "name": payload.get("name", "Usuario"),
            "role": payload.get("role", "Instructor"),
            "avatar_letter": payload.get("name", "U")[0].upper() if payload.get("name") else "U",
            "is_verified": True,
            "mfa_enabled": False,
            "created_at": payload.get("iat", 0)
        }

    raise HTTPException(status_code=401, detail="Se requiere autenticación. Proporcione un Header Authorization Bearer o X-API-Key.")
