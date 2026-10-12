import getpass
import re

from werkzeug.security import generate_password_hash

from database import connect_db, init_db


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+$")


def create_admin():
    init_db()
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()
    department = input("Department: ").strip() or "CampusCanvas"
    password = getpass.getpass("Password (10+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")

    if len(name) < 2:
        raise SystemExit("Name must contain at least 2 characters.")
    if not EMAIL_RE.fullmatch(email):
        raise SystemExit("Enter a valid email address.")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    connection = connect_db()
    try:
        existing = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise SystemExit("That email already has an account. Choose a different administrator email.")
        connection.execute(
            "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, 'admin', ?)",
            (name, email, generate_password_hash(password), department),
        )
        connection.commit()
    finally:
        connection.close()
    print("Administrator account is ready. Sign in through the CampusCanvas website.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2 or sys.argv[1] != "create-admin":
        raise SystemExit("Usage: python3 artifacts/api-server/campuscanvas/manage.py create-admin")
    create_admin()
