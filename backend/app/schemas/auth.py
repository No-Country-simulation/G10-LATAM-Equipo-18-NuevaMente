from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: Optional[str] = "Instructor"
    organization: Optional[str] = None
    avatar_letter: Optional[str] = None
    is_verified: bool = True
    mfa_enabled: bool = False

class UserResponse(UserBase):
    id: str
    created_at: float

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: Optional[str] = None
    role: Optional[str] = "Instructor"
    organization: Optional[str] = None
    terms_accepted: bool = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None

class LoginMfaRequest(BaseModel):
    email: EmailStr
    mfa_code: str
    mfa_token: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class MagicLinkRequest(BaseModel):
    email: EmailStr

class MagicLinkVerifyRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class MfaSetupResponse(BaseModel):
    secret: str
    qr_svg: str
    backup_codes: List[str]

class MfaVerifyRequest(BaseModel):
    code: str

class MfaDisableRequest(BaseModel):
    password: str

class ApiTokenCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: int = 30

class ApiTokenResponse(BaseModel):
    id: str
    name: str
    token: Optional[str] = None  # Returned only upon creation
    token_prefix: str
    created_at: float
    expires_at: Optional[float] = None
    last_used_at: Optional[float] = None

class SessionResponse(BaseModel):
    id: str
    device_name: str
    ip_address: str
    created_at: float
    is_current: bool = False

class TokenResponse(BaseModel):
    status: str = "exito"
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 900 # 15 minutes in seconds
    requires_mfa: bool = False
    mfa_token: Optional[str] = None
    user: Optional[UserResponse] = None
