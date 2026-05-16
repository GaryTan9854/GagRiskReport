import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
PBKDF2_ITERATIONS = 260000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}:{salt}:{dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        _, algo, iterations, salt, stored_key = stored.split(":")
        dk = hashlib.pbkdf2_hmac(algo, plain.encode(), salt.encode(), int(iterations))
        return secrets.compare_digest(dk.hex(), stored_key)
    except Exception:
        return False


def _get_stored_hash() -> Optional[str]:
    val = os.getenv("APP_PASSWORD_HASH")
    if val:
        return val
    try:
        with open(_ENV_PATH) as f:
            for line in f:
                if line.startswith("APP_PASSWORD_HASH="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
    return None


def create_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class LoginRequest(BaseModel):
    password: str


class SetupRequest(BaseModel):
    password: str


@router.post("/login")
def login(req: LoginRequest):
    stored = _get_stored_hash()
    if not stored:
        raise HTTPException(status_code=400, detail="Password not configured. Use /api/auth/setup first.")
    if not verify_password(req.password, stored):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_token({"sub": "gaglobal"})
    return {"token": token}


@router.post("/setup")
def setup(req: SetupRequest):
    if _get_stored_hash():
        raise HTTPException(status_code=400, detail="Password already configured")
    hashed = hash_password(req.password)
    with open(_ENV_PATH, "a") as f:
        f.write(f"\nAPP_PASSWORD_HASH={hashed}\n")
    os.environ["APP_PASSWORD_HASH"] = hashed
    return {"message": "Password set successfully"}


@router.get("/verify")
def verify(claims: dict = Depends(verify_token)):
    return {"valid": True}
