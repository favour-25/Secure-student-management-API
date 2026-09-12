"""
main.py

Entry point for the Secure Student Management API.

Route summary:
    POST   /auth/login              -> exchange credentials for a JWT
    GET    /students                -> list all students (protected)
    GET    /students/{matric_number}-> fetch one student (protected)
    POST   /students                -> add a new student (protected)
    PUT    /students/{matric_number}-> update a student (protected)
    DELETE /students/{matric_number}-> remove a student (protected)

Run with: uvicorn main:app --reload
Interactive docs will then be available at http://127.0.0.1:8000/docs
"""

import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import auth
import database

# The frontend lives one level up from this file, in a sibling
# "frontend" folder. Building the path from __file__ (rather than
# assuming a working directory) means this works the same whether
# uvicorn is started from backend/ locally or from a hosting
# platform's build system.
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = FastAPI(
    title="Secure Student Management API",
    description=(
        "Backend service for managing student records, built with "
        "FastAPI. Authentication is handled with JWT bearer tokens and "
        "passwords are stored using bcrypt hashing."
    ),
    version="1.0.0",
)

# Allows the vanilla JS frontend (served from a different port/origin)
# to talk to this API during local development and demos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()

VALID_LEVELS = {"100L", "200L", "300L", "400L", "500L"}


# ---------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin123")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StudentIn(BaseModel):
    full_name: str = Field(..., example="Adaeze Okafor")
    matric_number: str = Field(..., example="RUN/CMP/23/1042")
    department: str = Field(..., example="Computer Science")
    faculty: str = Field(..., example="Faculty of Computing")
    level: str = Field(..., example="300L")


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    faculty: Optional[str] = None
    level: Optional[str] = None


class StudentOut(StudentIn):
    id: int


# ---------------------------------------------------------------------
# Startup - seed a default admin account so the demo works immediately
# ---------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    default_hash = auth.hash_password("admin123")
    database.seed_default_admin(default_hash)


# ---------------------------------------------------------------------
# Auth dependency - runs before any protected route
# ---------------------------------------------------------------------

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    payload = auth.decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    user = database.get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return user


# ---------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(credentials: LoginRequest):
    user = database.get_user_by_username(credentials.username)

    if user is None or not auth.verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = auth.create_access_token(data={"sub": user["username"]})
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------
# Student routes (all require a valid bearer token)
# ---------------------------------------------------------------------

@app.get("/students", response_model=list[StudentOut], tags=["Students"])
def list_students(current_user: dict = Depends(get_current_user)):
    return database.get_all_students()


@app.get("/students/{matric_number}", response_model=StudentOut, tags=["Students"])
def get_student(matric_number: str, current_user: dict = Depends(get_current_user)):
    student = database.get_student_by_matric(matric_number)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED, tags=["Students"])
def add_student(student: StudentIn, current_user: dict = Depends(get_current_user)):
    if student.level not in VALID_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Level must be one of {sorted(VALID_LEVELS)}",
        )

    try:
        created = database.create_student(student.dict())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return created


@app.put("/students/{matric_number}", response_model=StudentOut, tags=["Students"])
def edit_student(
    matric_number: str,
    updates: StudentUpdate,
    current_user: dict = Depends(get_current_user),
):
    non_empty_updates = {k: v for k, v in updates.dict().items() if v is not None}

    if "level" in non_empty_updates and non_empty_updates["level"] not in VALID_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Level must be one of {sorted(VALID_LEVELS)}",
        )

    updated = database.update_student(matric_number, non_empty_updates)
    if updated is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated


@app.delete("/students/{matric_number}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def remove_student(matric_number: str, current_user: dict = Depends(get_current_user)):
    deleted = database.delete_student(matric_number)
    if not deleted:
        raise HTTPException(status_code=404, detail="Student not found")
    return None


# ---------------------------------------------------------------------
# Serve the frontend dashboard from the same service
# ---------------------------------------------------------------------
# Mounted last, on the root path, so it only catches requests that
# didn't match one of the API routes above (e.g. "/", "/styles.css").
# This lets the whole project live behind one URL when deployed.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
