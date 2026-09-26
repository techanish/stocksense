import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    generate_otp,
    otp_expires_at,
    is_otp_valid,
)
from models import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.execute("SELECT * FROM users WHERE id = ?", (payload.get("sub"),)).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return dict(user)


@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM users WHERE email = ?", (data.email,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_hash = hash_password(data.password)
    db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (data.name, data.email, pw_hash, data.role),
    )
    db.commit()
    return {"message": "Account created successfully"}


@router.post("/login")
def login(data: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = ?", (data.email,)).fetchone()
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user["id"]), "email": user["email"], "role": user["role"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT id FROM users WHERE email = ?", (data.email,)).fetchone()
    if not user:
        # Don't reveal whether email exists
        return {"message": "If that email exists, an OTP has been sent"}
    otp = generate_otp()
    expires = otp_expires_at()
    db.execute(
        "UPDATE users SET otp = ?, otp_expires_at = ? WHERE email = ?",
        (otp, expires, data.email),
    )
    db.commit()
    # In production: send email. For dev, return OTP directly.
    return {"message": "OTP sent", "otp": otp, "expires_in": "15 minutes"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute(
        "SELECT * FROM users WHERE email = ?", (data.email,)
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if not is_otp_valid(user["otp_expires_at"] or ""):
        raise HTTPException(status_code=400, detail="OTP has expired")
    new_hash = hash_password(data.new_password)
    db.execute(
        "UPDATE users SET password_hash = ?, otp = NULL, otp_expires_at = NULL WHERE email = ?",
        (new_hash, data.email),
    )
    db.commit()
    return {"message": "Password reset successfully"}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {k: v for k, v in current_user.items() if k != "password_hash"}
