from __future__ import annotations

import hmac
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import connect_db, init_db


ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_CATEGORIES = {
    "Drawing & Painting",
    "Photography",
    "Writing",
    "Poetry",
    "Music & Audio",
    "Film & Video",
    "Graphic Design",
    "College Life & Events",
}
MEDIA_TYPES = {
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
    "mp4": "video",
    "webm": "video",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "pdf": "document",
    "docx": "document",
    "txt": "text",
}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+$")

app = Flask(__name__)
secret_key = os.environ.get("SESSION_SECRET")
if not secret_key:
    raise RuntimeError("SESSION_SECRET must be configured before starting CampusCanvas.")

app.secret_key = secret_key
app.config.update(
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES + 256 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.environ.get("NODE_ENV") == "production",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
init_db()


def api_error(message: str, status: int):
    return jsonify({"error": message}), status


def get_user(user_id: int):
    connection = connect_db()
    try:
        return connection.execute(
            """
            SELECT u.*,
              (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.status = 'approved') AS post_count,
              (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id) AS follower_count
            FROM users u WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        connection.close()


def current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    user_id = session.get("user_id")
    g.current_user = get_user(user_id) if isinstance(user_id, int) else None
    if g.current_user is not None and not g.current_user["is_active"]:
        session.clear()
        g.current_user = None
    return g.current_user


def user_json(user, include_email: bool = False):
    user_id = user["id"]
    current = current_user()
    following = False
    if current and current["id"] != user_id:
        connection = connect_db()
        try:
            following = connection.execute(
                "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
                (current["id"], user_id),
            ).fetchone() is not None
        finally:
            connection.close()
    return {
        "id": user_id,
        "name": user["name"],
        "email": user["email"] if include_email else None,
        "role": user["role"],
        "department": user["department"],
        "bio": user["bio"],
        "profile_pic": f"/api/uploads/{user['profile_pic']}" if user["profile_pic"] else None,
        "skills": user["skills"],
        "is_active": bool(user["is_active"]),
        "created_at": user["created_at"],
        "post_count": int(user["post_count"] or 0),
        "follower_count": int(user["follower_count"] or 0),
        "following": following,
    }


POST_SELECT = """
SELECT p.*, u.name AS creator_name, u.department AS creator_department,
       u.profile_pic AS creator_pic, u.is_active AS creator_active,
       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
FROM posts p
JOIN users u ON u.id = p.user_id
"""


def post_json(row):
    user = current_user()
    user_id = user["id"] if user else None
    connection = connect_db()
    try:
        liked = bool(
            user_id
            and connection.execute(
                "SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?",
                (row["id"], user_id),
            ).fetchone()
        )
        bookmarked = bool(
            user_id
            and connection.execute(
                "SELECT 1 FROM bookmarks WHERE post_id = ? AND user_id = ?",
                (row["id"], user_id),
            ).fetchone()
        )
    finally:
        connection.close()
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "media_path": f"/api/uploads/{row['media_path']}" if row["media_path"] else None,
        "media_type": row["media_type"],
        "tags": row["tags"],
        "status": row["status"],
        "views": row["views"],
        "created_at": row["created_at"],
        "creator_name": row["creator_name"],
        "creator_department": row["creator_department"],
        "creator_pic": f"/api/uploads/{row['creator_pic']}" if row["creator_pic"] else None,
        "like_count": int(row["like_count"] or 0),
        "comment_count": int(row["comment_count"] or 0),
        "share_count": int(row["shares"] or 0),
        "liked": liked,
        "bookmarked": bookmarked,
        "featured": bool(row["featured"]),
    }


def get_post(post_id: int):
    connection = connect_db()
    try:
        return connection.execute(POST_SELECT + " WHERE p.id = ?", (post_id,)).fetchone()
    finally:
        connection.close()


def get_visible_post(post_id: int):
    post = get_post(post_id)
    if not post:
        return None
    user = current_user()
    if post["status"] == "approved" and post["creator_active"]:
        return post
    if user and (user["id"] == post["user_id"] or user["role"] == "admin"):
        return post
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return api_error("Sign in to continue.", 401)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user()["role"] != "admin":
            return api_error("Administrator access is required.", 403)
        return view(*args, **kwargs)

    return wrapped


def request_data():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def trim_text(value, limit: int, required: bool = False):
    text = value.strip() if isinstance(value, str) else ""
    if required and not text:
        return None
    return text[:limit]


def validate_csrf():
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return api_error("Your session has expired. Refresh the page and try again.", 403)
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        return api_error("Cross-site requests are not allowed.", 403)
    origin = request.headers.get("Origin")
    if origin:
        try:
            if urlparse(origin).netloc != request.host:
                return api_error("Cross-origin requests are not allowed.", 403)
        except ValueError:
            return api_error("Invalid request origin.", 403)
    return None


@app.before_request
def protect_mutations():
    return validate_csrf()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.errorhandler(413)
def upload_too_large(_error):
    return api_error("Files must be 20 MB or smaller.", 413)


@app.errorhandler(404)
def not_found(_error):
    return api_error("The requested item was not found.", 404)


@app.errorhandler(Exception)
def unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Unhandled CampusCanvas API error", exc_info=error)
    return api_error("Something went wrong. Please try again.", 500)


@app.get("/api/healthz")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/auth/session")
def get_session():
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_urlsafe(32)
    user = current_user()
    include_email = bool(user)
    return jsonify(
        {
            "user": user_json(user, include_email=True) if user else None,
            "csrf_token": session["csrf_token"],
        }
    )


def create_login_session(user):
    session.clear()
    session["user_id"] = user["id"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify({"user": user_json(get_user(user["id"]), include_email=True), "csrf_token": session["csrf_token"]})


@app.post("/api/auth/register")
def register():
    data = request_data()
    name = trim_text(data.get("name"), 80, required=True)
    email = trim_text(data.get("email"), 254, required=True)
    department = trim_text(data.get("department"), 120, required=True)
    password = data.get("password")
    role = data.get("role")
    if not name or len(name) < 2 or not department or len(department) < 2:
        return api_error("Enter your name and department.", 400)
    if not email or not EMAIL_RE.fullmatch(email):
        return api_error("Enter a valid email address.", 400)
    if not isinstance(password, str) or len(password) < 10 or len(password) > 128:
        return api_error("Use a password with at least 10 characters.", 400)
    if role not in {"student", "faculty"}:
        return api_error("Choose student or faculty. Administrator accounts are created separately.", 400)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
            (name, email.lower(), generate_password_hash(password), role, department),
        )
        connection.commit()
        user = get_user(cursor.lastrowid)
    except Exception as error:
        connection.rollback()
        if "UNIQUE constraint failed" in str(error):
            return api_error("An account with that email already exists.", 409)
        raise
    finally:
        connection.close()
    return create_login_session(user), 201


def reserve_login_attempt(key: str):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=15)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    retention_cutoff = (now - timedelta(days=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    connection = connect_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM login_attempts WHERE created_at < ?", (retention_cutoff,))
        count = connection.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE remote_key = ? AND created_at >= ?",
            (key, cutoff),
        ).fetchone()[0]
        if count >= 8:
            connection.commit()
            return False
        connection.execute("INSERT INTO login_attempts (remote_key) VALUES (?)", (key,))
        connection.commit()
        return True
    finally:
        connection.close()


def clear_login_attempts(key: str):
    connection = connect_db()
    try:
        connection.execute("DELETE FROM login_attempts WHERE remote_key = ?", (key,))
        connection.commit()
    finally:
        connection.close()


@app.post("/api/auth/login")
def login():
    key = request.remote_addr or "unknown"
    if not reserve_login_attempt(key):
        return api_error("Too many attempts. Wait 15 minutes before trying again.", 429)
    data = request_data()
    email = trim_text(data.get("email"), 254)
    password = data.get("password")
    connection = connect_db()
    try:
        user = connection.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email or "",)).fetchone()
    finally:
        connection.close()
    if not user or not user["is_active"] or not isinstance(password, str) or not check_password_hash(user["password_hash"], password):
        return api_error("Email or password is incorrect.", 401)
    clear_login_attempts(key)
    return create_login_session(user)


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return "", 204


@app.get("/api/users/me")
@login_required
def my_profile():
    user = current_user()
    return jsonify(user_json(user, include_email=True))


@app.patch("/api/users/me")
@login_required
def update_my_profile():
    data = request_data()
    name = trim_text(data.get("name", current_user()["name"]), 80, required=True)
    department = trim_text(data.get("department", current_user()["department"]), 120, required=True)
    bio = trim_text(data.get("bio", current_user()["bio"]), 500)
    skills = trim_text(data.get("skills", current_user()["skills"]), 300)
    if not name or len(name) < 2 or not department:
        return api_error("Enter a valid name and department.", 400)
    connection = connect_db()
    try:
        connection.execute(
            "UPDATE users SET name = ?, department = ?, bio = ?, skills = ? WHERE id = ?",
            (name, department, bio, skills, current_user()["id"]),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify(user_json(get_user(current_user()["id"]), include_email=True))


def save_upload(file_storage, allowed_extensions: set[str] | None = None):
    if not file_storage or not file_storage.filename:
        return None, "Choose a file to upload."
    safe_name = secure_filename(file_storage.filename)
    if not safe_name or "." not in safe_name:
        return None, "That file name is not supported."
    extension = safe_name.rsplit(".", 1)[-1].lower()
    allowed = allowed_extensions or set(MEDIA_TYPES)
    if extension not in allowed:
        return None, "That file type is not supported."
    prefix = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    valid_signatures = {
        "jpg": prefix.startswith(b"\xff\xd8\xff"),
        "jpeg": prefix.startswith(b"\xff\xd8\xff"),
        "png": prefix.startswith(b"\x89PNG\r\n\x1a\n"),
        "gif": prefix.startswith((b"GIF87a", b"GIF89a")),
        "webp": prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP",
        "pdf": prefix.startswith(b"%PDF-"),
        "wav": prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE",
        "mp4": len(prefix) >= 8 and prefix[4:8] == b"ftyp",
        "webm": prefix.startswith(b"\x1aE\xdf\xa3"),
        "ogg": prefix.startswith(b"OggS"),
        "mp3": prefix.startswith(b"ID3") or (
            len(prefix) >= 2 and prefix[0] == 0xFF and prefix[1] & 0xE0 == 0xE0
        ),
        "docx": prefix.startswith(b"PK\x03\x04"),
        "txt": True,
    }
    if extension == "txt":
        try:
            file_storage.stream.read(4096).decode("utf-8")
        except UnicodeDecodeError:
            file_storage.stream.seek(0)
            return None, "Text files must use UTF-8 encoding."
        finally:
            file_storage.stream.seek(0)
    elif not valid_signatures.get(extension, False):
        return None, "The file contents do not match the selected file type."
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    destination = UPLOAD_DIR / stored_name
    file_storage.save(destination)
    if destination.stat().st_size > MAX_UPLOAD_BYTES:
        destination.unlink(missing_ok=True)
        return None, "Files must be 20 MB or smaller."
    return (stored_name, extension), None


@app.post("/api/users/me/avatar")
@login_required
def upload_avatar():
    saved, error = save_upload(request.files.get("media"), IMAGE_EXTENSIONS)
    if error:
        return api_error(error, 400)
    filename, _extension = saved
    old_name = current_user()["profile_pic"]
    connection = connect_db()
    try:
        connection.execute("UPDATE users SET profile_pic = ? WHERE id = ?", (filename, current_user()["id"]))
        connection.commit()
    finally:
        connection.close()
    if old_name:
        (UPLOAD_DIR / Path(old_name).name).unlink(missing_ok=True)
    return jsonify(user_json(get_user(current_user()["id"]), include_email=True))


@app.get("/api/users")
def creators():
    query = trim_text(request.args.get("q"), 100)
    connection = connect_db()
    try:
        sql = """
        SELECT u.*,
          (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.status = 'approved') AS post_count,
          (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id) AS follower_count
        FROM users u WHERE u.is_active = 1 AND u.role <> 'admin'
        """
        params: list[object] = []
        if query:
            sql += " AND (u.name LIKE ? OR u.department LIKE ? OR u.skills LIKE ?)"
            term = f"%{query}%"
            params.extend([term, term, term])
        sql += " ORDER BY follower_count DESC, post_count DESC, u.created_at DESC LIMIT 50"
        rows = connection.execute(sql, params).fetchall()
    finally:
        connection.close()
    return jsonify([user_json(row) for row in rows])


@app.get("/api/users/<int:user_id>")
def user_profile(user_id):
    user = get_user(user_id)
    if not user or not user["is_active"]:
        return api_error("Creator not found.", 404)
    viewer = current_user()
    connection = connect_db()
    try:
        posts = connection.execute(
            POST_SELECT + " WHERE p.user_id = ? AND (p.status = 'approved' OR ? = p.user_id) ORDER BY p.created_at DESC",
            (user_id, viewer["id"] if viewer else -1),
        ).fetchall()
        following_count = connection.execute(
            "SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        connection.close()
    return jsonify(
        {
            "user": user_json(user, include_email=bool(viewer and viewer["id"] == user_id)),
            "posts": [post_json(row) for row in posts],
            "follower_count": int(user["follower_count"] or 0),
            "following_count": int(following_count),
        }
    )


@app.post("/api/users/<int:user_id>/follow")
@login_required
def toggle_follow(user_id):
    user = get_user(user_id)
    current = current_user()
    if not user or not user["is_active"]:
        return api_error("Creator not found.", 404)
    if current["id"] == user_id:
        return api_error("You cannot follow your own profile.", 400)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "DELETE FROM follows WHERE follower_id = ? AND following_id = ?",
            (current["id"], user_id),
        )
        active = cursor.rowcount == 0
        if active:
            connection.execute(
                "INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)",
                (current["id"], user_id),
            )
        connection.commit()
        count = connection.execute(
            "SELECT COUNT(*) FROM follows WHERE following_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        connection.close()
    return jsonify({"active": active, "count": int(count)})


def fetch_posts(query: str | None, category: str | None, sort: str, limit: int, offset: int, user_id: int | None):
    sql = POST_SELECT + " WHERE p.status = 'approved' AND u.is_active = 1"
    values: list[object] = []
    if category:
        sql += " AND p.category = ?"
        values.append(category)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        term = f"%{escaped}%"
        sql += " AND (p.title LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\' OR p.tags LIKE ? ESCAPE '\\' OR p.category LIKE ? ESCAPE '\\' OR u.name LIKE ? ESCAPE '\\')"
        values.extend([term] * 5)
    if sort == "trending":
        sql += " ORDER BY CASE WHEN p.created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END DESC, (like_count * 3 + comment_count * 2 + p.views + p.shares) DESC, p.created_at DESC"
    elif sort == "featured":
        sql += " ORDER BY p.featured DESC, p.created_at DESC"
    else:
        sql += " ORDER BY p.created_at DESC"
    sql += " LIMIT ? OFFSET ?"
    values.extend([limit, offset])
    connection = connect_db()
    try:
        rows = connection.execute(sql, values).fetchall()
    finally:
        connection.close()
    return [post_json(row) for row in rows]


@app.get("/api/posts")
def posts():
    query = trim_text(request.args.get("q"), 100)
    category = trim_text(request.args.get("category"), 60)
    if category and category not in ALLOWED_CATEGORIES:
        return api_error("Choose a valid category.", 400)
    sort = request.args.get("sort", "latest")
    if sort not in {"latest", "trending", "featured"}:
        return api_error("Choose latest, trending, or featured sorting.", 400)
    try:
        limit = max(1, min(50, int(request.args.get("limit", 24))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return api_error("Invalid page size.", 400)
    viewer = current_user()
    return jsonify(fetch_posts(query, category, sort, limit, offset, viewer["id"] if viewer else None))


@app.get("/api/bookmarks")
@login_required
def bookmarks():
    connection = connect_db()
    try:
        rows = connection.execute(
            POST_SELECT
            + " JOIN bookmarks b ON b.post_id = p.id WHERE b.user_id = ? AND p.status = 'approved' ORDER BY b.created_at DESC",
            (current_user()["id"],),
        ).fetchall()
    finally:
        connection.close()
    return jsonify([post_json(row) for row in rows])


@app.post("/api/posts")
@login_required
def create_post():
    title = trim_text(request.form.get("title"), 120, required=True)
    description = trim_text(request.form.get("description"), 5000)
    text_body = trim_text(request.form.get("text_body"), 20000)
    category = trim_text(request.form.get("category"), 60, required=True)
    tags = trim_text(request.form.get("tags"), 300)
    if not title or not category or category not in ALLOWED_CATEGORIES:
        return api_error("Add a title and choose one of the listed categories.", 400)
    if text_body:
        description = "\n\n".join(part for part in (description, text_body) if part)
    uploaded = request.files.get("media")
    media_path = None
    media_type = "text"
    if uploaded and uploaded.filename:
        saved, error = save_upload(uploaded)
        if error:
            return api_error(error, 400)
        media_path, extension = saved
        media_type = MEDIA_TYPES[extension]
    elif not description:
        return api_error("Add a description or choose a media file.", 400)
    normalized_tags = ", ".join(
        dict.fromkeys(tag.strip().lstrip("#")[:32] for tag in (tags or "").split(",") if tag.strip())
    )[:300]
    connection = connect_db()
    try:
        cursor = connection.execute(
            """
            INSERT INTO posts (user_id, title, description, category, media_path, media_type, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (current_user()["id"], title, description, category, media_path, media_type, normalized_tags),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        if media_path:
            (UPLOAD_DIR / media_path).unlink(missing_ok=True)
        raise
    finally:
        connection.close()
    return jsonify(post_json(get_post(cursor.lastrowid))), 201


@app.get("/api/posts/<int:post_id>")
def post_detail(post_id):
    post = get_visible_post(post_id)
    if not post:
        return api_error("Post not found.", 404)
    if post["status"] == "approved":
        connection = connect_db()
        try:
            connection.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
            connection.commit()
        finally:
            connection.close()
    comments_connection = connect_db()
    try:
        comments = comments_connection.execute(
            """
            SELECT c.*, u.name AS user_name, u.profile_pic AS user_pic
            FROM comments c JOIN users u ON u.id = c.user_id
            WHERE c.post_id = ? ORDER BY c.created_at ASC
            """,
            (post_id,),
        ).fetchall()
    finally:
        comments_connection.close()
    result = get_post(post_id)
    return jsonify(
        {
            "post": post_json(result),
            "comments": [
                {
                    "id": comment["id"],
                    "post_id": comment["post_id"],
                    "user_id": comment["user_id"],
                    "text": comment["text"],
                    "created_at": comment["created_at"],
                    "user_name": comment["user_name"],
                    "user_pic": f"/api/uploads/{comment['user_pic']}" if comment["user_pic"] else None,
                }
                for comment in comments
            ],
        }
    )


@app.delete("/api/posts/<int:post_id>")
@login_required
def delete_post(post_id):
    connection = connect_db()
    try:
        row = connection.execute("SELECT user_id, media_path FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return api_error("Post not found.", 404)
        if row["user_id"] != current_user()["id"] and current_user()["role"] != "admin":
            return api_error("You can only remove your own posts.", 403)
        connection.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        connection.commit()
    finally:
        connection.close()
    if row["media_path"]:
        (UPLOAD_DIR / Path(row["media_path"]).name).unlink(missing_ok=True)
    return "", 204


@app.post("/api/posts/<int:post_id>/like")
@login_required
def toggle_like(post_id):
    post = get_post(post_id)
    if not post or post["status"] != "approved":
        return api_error("Post not found.", 404)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "DELETE FROM likes WHERE post_id = ? AND user_id = ?",
            (post_id, current_user()["id"]),
        )
        active = cursor.rowcount == 0
        if active:
            connection.execute(
                "INSERT OR IGNORE INTO likes (post_id, user_id) VALUES (?, ?)",
                (post_id, current_user()["id"]),
            )
        connection.commit()
        count = connection.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
    finally:
        connection.close()
    return jsonify({"active": active, "count": int(count)})


@app.post("/api/posts/<int:post_id>/comments")
@login_required
def add_comment(post_id):
    data = request_data()
    text = trim_text(data.get("text"), 1000, required=True)
    post = get_post(post_id)
    if not post or post["status"] != "approved":
        return api_error("Post not found.", 404)
    if not text:
        return api_error("Write a comment first.", 400)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "INSERT INTO comments (post_id, user_id, text) VALUES (?, ?, ?)",
            (post_id, current_user()["id"], text),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT c.*, u.name AS user_name, u.profile_pic AS user_pic
            FROM comments c JOIN users u ON u.id = c.user_id WHERE c.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        connection.close()
    return jsonify(
        {
            "id": row["id"],
            "post_id": row["post_id"],
            "user_id": row["user_id"],
            "text": row["text"],
            "created_at": row["created_at"],
            "user_name": row["user_name"],
            "user_pic": f"/api/uploads/{row['user_pic']}" if row["user_pic"] else None,
        }
    ), 201


@app.post("/api/posts/<int:post_id>/bookmark")
@login_required
def toggle_bookmark(post_id):
    post = get_post(post_id)
    if not post or post["status"] != "approved":
        return api_error("Post not found.", 404)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "DELETE FROM bookmarks WHERE post_id = ? AND user_id = ?",
            (post_id, current_user()["id"]),
        )
        active = cursor.rowcount == 0
        if active:
            connection.execute(
                "INSERT OR IGNORE INTO bookmarks (post_id, user_id) VALUES (?, ?)",
                (post_id, current_user()["id"]),
            )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"active": active})


@app.post("/api/posts/<int:post_id>/share")
def share_post(post_id):
    connection = connect_db()
    try:
        cursor = connection.execute(
            "UPDATE posts SET shares = shares + 1 WHERE id = ? AND status = 'approved'",
            (post_id,),
        )
        if cursor.rowcount == 0:
            return api_error("Post not found.", 404)
        connection.commit()
        count = connection.execute("SELECT shares FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
    finally:
        connection.close()
    return jsonify({"active": True, "count": int(count)})


@app.post("/api/posts/<int:post_id>/report")
@login_required
def report_post(post_id):
    data = request_data()
    reason = trim_text(data.get("reason"), 500, required=True)
    post = get_post(post_id)
    if not post or post["status"] != "approved":
        return api_error("Post not found.", 404)
    if not reason or len(reason) < 3:
        return api_error("Please explain why you are reporting this post.", 400)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO reports (post_id, reported_by, reason) VALUES (?, ?, ?)",
            (post_id, current_user()["id"], reason),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT r.*, p.title AS post_title, u.name AS reporter_name
            FROM reports r JOIN posts p ON p.id = r.post_id
            JOIN users u ON u.id = r.reported_by WHERE r.post_id = ? AND r.reported_by = ?
            """,
            (post_id, current_user()["id"]),
        ).fetchone()
    finally:
        connection.close()
    return jsonify(report_json(row)), 201 if cursor.rowcount else 200


def report_json(row):
    return {
        "id": row["id"],
        "post_id": row["post_id"],
        "post_title": row["post_title"],
        "reported_by": row["reported_by"],
        "reporter_name": row["reporter_name"],
        "reason": row["reason"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def event_json(row, current_id: int | None):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "type": row["type"],
        "event_date": row["event_date"],
        "location": row["location"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "entry_count": int(row["entry_count"] or 0),
        "entered": bool(current_id and row["entered"]),
    }


@app.get("/api/events")
def events():
    user = current_user()
    current_id = user["id"] if user else None
    connection = connect_db()
    try:
        rows = connection.execute(
            """
            SELECT e.*,
              (SELECT COUNT(*) FROM event_entries ee WHERE ee.event_id = e.id) AS entry_count,
              EXISTS(SELECT 1 FROM event_entries ee WHERE ee.event_id = e.id AND ee.user_id = ?) AS entered
            FROM events e
            ORDER BY CASE WHEN e.event_date IS NULL THEN 1 ELSE 0 END, e.event_date ASC, e.created_at DESC
            """,
            (current_id or -1,),
        ).fetchall()
    finally:
        connection.close()
    return jsonify([event_json(row, current_id) for row in rows])


def parse_event_date(value):
    if not value:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid event date.")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@app.post("/api/events")
@admin_required
def create_event():
    data = request_data()
    title = trim_text(data.get("title"), 120, required=True)
    description = trim_text(data.get("description"), 3000, required=True)
    event_type = data.get("type")
    location = trim_text(data.get("location"), 200)
    if not title or len(title) < 3 or not description or len(description) < 3:
        return api_error("Add an event title and description.", 400)
    if event_type not in {"event", "competition", "announcement"}:
        return api_error("Choose an event, competition, or announcement.", 400)
    try:
        event_date = parse_event_date(data.get("event_date"))
    except ValueError:
        return api_error("Enter a valid event date.", 400)
    connection = connect_db()
    try:
        cursor = connection.execute(
            "INSERT INTO events (title, description, type, event_date, location, created_by) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, event_type, event_date, location, current_user()["id"]),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT e.*, 0 AS entry_count, 0 AS entered FROM events e WHERE e.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        connection.close()
    return jsonify(event_json(row, current_user()["id"])), 201


@app.post("/api/events/<int:event_id>/entries")
@login_required
def enter_event(event_id):
    data = request_data()
    note = trim_text(data.get("note"), 1000)
    connection = connect_db()
    try:
        event = connection.execute("SELECT id, type FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            return api_error("Event not found.", 404)
        if event["type"] != "competition":
            return api_error("Entries are only available for competitions.", 400)
        cursor = connection.execute(
            "INSERT OR IGNORE INTO event_entries (event_id, user_id, note) VALUES (?, ?, ?)",
            (event_id, current_user()["id"], note),
        )
        connection.commit()
        count = connection.execute("SELECT COUNT(*) FROM event_entries WHERE event_id = ?", (event_id,)).fetchone()[0]
    finally:
        connection.close()
    return jsonify({"active": True, "count": int(count)}), 201 if cursor.rowcount else 200


@app.get("/api/admin/summary")
@admin_required
def admin_summary():
    connection = connect_db()
    try:
        result = {
            "pending_posts": connection.execute("SELECT COUNT(*) FROM posts WHERE status = 'pending'").fetchone()[0],
            "open_reports": connection.execute("SELECT COUNT(*) FROM reports WHERE status = 'open'").fetchone()[0],
            "active_users": connection.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND role <> 'admin'").fetchone()[0],
            "approved_posts": connection.execute("SELECT COUNT(*) FROM posts WHERE status = 'approved'").fetchone()[0],
            "events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        }
    finally:
        connection.close()
    return jsonify({key: int(value) for key, value in result.items()})


@app.get("/api/admin/posts")
@admin_required
def admin_posts():
    status = request.args.get("status", "pending")
    if status not in {"pending", "approved", "rejected"}:
        return api_error("Choose a valid moderation status.", 400)
    connection = connect_db()
    try:
        rows = connection.execute(
            POST_SELECT + " WHERE p.status = ? ORDER BY p.created_at ASC LIMIT 100",
            (status,),
        ).fetchall()
    finally:
        connection.close()
    return jsonify([post_json(row) for row in rows])


@app.post("/api/admin/posts/<int:post_id>/moderation")
@admin_required
def moderate_post(post_id):
    data = request_data()
    status = data.get("status")
    note = trim_text(data.get("note"), 500)
    featured = data.get("featured")
    if status not in {"approved", "rejected"}:
        return api_error("Choose approve or reject.", 400)
    if featured is not None and not isinstance(featured, bool):
        return api_error("Featured must be true or false.", 400)
    connection = connect_db()
    try:
        row = connection.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return api_error("Post not found.", 404)
        connection.execute(
            """
            UPDATE posts SET status = ?, moderation_note = ?,
              featured = CASE WHEN ? = 'approved' THEN COALESCE(?, featured) ELSE 0 END
            WHERE id = ?
            """,
            (status, note, status, int(featured) if featured is not None else None, post_id),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify(post_json(get_post(post_id)))


@app.get("/api/admin/reports")
@admin_required
def admin_reports():
    connection = connect_db()
    try:
        rows = connection.execute(
            """
            SELECT r.*, p.title AS post_title, u.name AS reporter_name
            FROM reports r JOIN posts p ON p.id = r.post_id
            JOIN users u ON u.id = r.reported_by
            WHERE r.status = 'open' ORDER BY r.created_at DESC
            """
        ).fetchall()
    finally:
        connection.close()
    return jsonify([report_json(row) for row in rows])


@app.post("/api/admin/reports/<int:report_id>/resolve")
@admin_required
def resolve_report(report_id):
    connection = connect_db()
    try:
        cursor = connection.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
        if cursor.rowcount == 0:
            return api_error("Report not found.", 404)
        connection.commit()
        row = connection.execute(
            """
            SELECT r.*, p.title AS post_title, u.name AS reporter_name
            FROM reports r JOIN posts p ON p.id = r.post_id
            JOIN users u ON u.id = r.reported_by WHERE r.id = ?
            """,
            (report_id,),
        ).fetchone()
    finally:
        connection.close()
    return jsonify(report_json(row))


@app.get("/api/admin/users")
@admin_required
def admin_users():
    connection = connect_db()
    try:
        rows = connection.execute(
            """
            SELECT u.*,
              (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.status = 'approved') AS post_count,
              (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id) AS follower_count
            FROM users u ORDER BY u.created_at DESC LIMIT 200
            """
        ).fetchall()
    finally:
        connection.close()
    return jsonify([user_json(row, include_email=True) for row in rows])


@app.patch("/api/admin/users/<int:user_id>/status")
@admin_required
def set_user_status(user_id):
    data = request_data()
    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return api_error("Account status must be active or suspended.", 400)
    if user_id == current_user()["id"] and not is_active:
        return api_error("You cannot suspend your own account.", 400)
    connection = connect_db()
    try:
        target = connection.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            return api_error("Account not found.", 404)
        if target["role"] == "admin" and not is_active:
            admins = connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()[0]
            if admins <= 1:
                return api_error("At least one active administrator must remain.", 400)
        connection.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(is_active), user_id))
        connection.commit()
    finally:
        connection.close()
    return jsonify(user_json(get_user(user_id), include_email=True))


@app.get("/api/uploads/<path:filename>")
def uploaded_file(filename):
    response = send_from_directory(
        UPLOAD_DIR,
        filename,
        conditional=True,
        max_age=3600,
        as_attachment=Path(filename).suffix.lower() in {".pdf", ".docx", ".txt"},
    )
    response.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; media-src 'self'; sandbox"
    return response


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        debug=False,
    )
