from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

SECRET_KEY = "dev-secret-change-in-real-life"
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(username: str, expires_delta: timedelta = timedelta(minutes=30)) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)