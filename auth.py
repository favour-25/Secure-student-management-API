"""
auth.py

Everything related to keeping user credentials safe and issuing
access tokens lives here, separate from the route handlers in main.py.

Two cryptographic building blocks are used:

1. bcrypt (via passlib) - a one-way, salted hashing algorithm for
   passwords. Plain-text passwords are never written to the database;
   only the bcrypt hash is stored, so even if db.json were leaked, the
   original passwords could not be recovered directly from it.

2. JWT (JSON Web Token, via python-jose) - used for stateless
   authentication. Once a user logs in successfully, the server signs
   a token containing their username and an expiry time. The client
   sends this token on every subsequent request instead of the
   username/password, and the server verifies the signature to confirm
   the request is legitimate.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# In a real deployment this would be pulled from an environment
# variable and never committed to source control. It is hardcoded
# here only because this is a student demo project.
SECRET_KEY = "run-cmp-2024-secure-student-api-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Returns the decoded payload if the token is valid and not expired,
    otherwise returns None. jose raises JWTError for both a bad
    signature and an expired 'exp' claim, so both cases are caught here.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
