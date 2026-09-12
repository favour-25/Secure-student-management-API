"""
database.py

Handles all read/write operations for the project's data store.

For this project we are using a flat JSON file instead of a full
database engine (Postgres, MySQL, etc). This was a deliberate choice
for a project of this scope: it needs zero installation, zero Docker
setup, and can be inspected directly by opening the file. In a
production deployment this module would be swapped for SQLAlchemy
models against a real RDBMS, but the rest of the application (routes,
auth, schemas) would not need to change much because the functions
below act as the boundary between the API and the storage layer.
"""

import json
import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "db.json")


def _load_db() -> dict:
    """Reads the JSON file from disk and returns it as a dict."""
    if not os.path.exists(DB_FILE):
        return {"users": [], "students": []}

    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # File exists but is empty or corrupted - start fresh
            return {"users": [], "students": []}


def _save_db(data: dict) -> None:
    """Writes the given dict back to the JSON file, pretty-printed."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def seed_default_admin(hashed_password: str) -> None:
    """
    Creates a default admin account on first run so the project can be
    demoed immediately without a separate registration step.
    Only runs if no users exist yet.
    """
    data = _load_db()
    if len(data["users"]) == 0:
        data["users"].append({
            "id": 1,
            "username": "admin",
            "hashed_password": hashed_password,
        })
        _save_db(data)


# ---------------------------------------------------------------------
# User queries
# ---------------------------------------------------------------------

def get_user_by_username(username: str) -> Optional[dict]:
    data = _load_db()
    for user in data["users"]:
        if user["username"].lower() == username.lower():
            return user
    return None


# ---------------------------------------------------------------------
# Student CRUD
# ---------------------------------------------------------------------

def get_all_students() -> list:
    data = _load_db()
    return data["students"]


def get_student_by_matric(matric_number: str) -> Optional[dict]:
    data = _load_db()
    for student in data["students"]:
        if student["matric_number"].upper() == matric_number.upper():
            return student
    return None


def create_student(student: dict) -> dict:
    data = _load_db()

    # Matric number is treated like a unique key, similar to a primary key
    for existing in data["students"]:
        if existing["matric_number"].upper() == student["matric_number"].upper():
            raise ValueError("A student with this matric number already exists")

    next_id = (max([s["id"] for s in data["students"]], default=0)) + 1
    student["id"] = next_id

    data["students"].append(student)
    _save_db(data)
    return student


def update_student(matric_number: str, updates: dict) -> Optional[dict]:
    data = _load_db()

    for student in data["students"]:
        if student["matric_number"].upper() == matric_number.upper():
            student.update(updates)
            _save_db(data)
            return student
    return None


def delete_student(matric_number: str) -> bool:
    data = _load_db()
    original_count = len(data["students"])

    data["students"] = [
        s for s in data["students"]
        if s["matric_number"].upper() != matric_number.upper()
    ]

    if len(data["students"]) == original_count:
        return False

    _save_db(data)
    return True
