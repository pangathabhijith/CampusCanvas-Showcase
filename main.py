from flask import Flask, jsonify, request
import os
import sqlite3
import uuid
import base64
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload limit

DB_PATH = "campuscanvas.db"

# Track active sessions per token and per student device so students never overwrite each other
sessions_by_token = {}
sessions_by_device = {}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT DEFAULT '',
            department TEXT DEFAULT '',
            role TEXT DEFAULT 'Student',
            bio TEXT DEFAULT '',
            practices TEXT DEFAULT '',
            avatar TEXT DEFAULT ''
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            category TEXT DEFAULT 'Photography',
            media_type TEXT DEFAULT 'image',
            media_url TEXT DEFAULT '',
            author_id INTEGER,
            author_name TEXT DEFAULT 'Student',
            author_avatar TEXT DEFAULT '',
            department TEXT DEFAULT '',
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author_name TEXT,
            author_avatar TEXT,
            text TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            date TEXT,
            location TEXT,
            organizer TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            user_id INTEGER,
            post_id INTEGER,
            UNIQUE(user_id, post_id)
        )
    ''')
    conn.commit()
    conn.close()


init_db()


def get_device_key():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
    ua = request.headers.get('User-Agent', 'unknown')
    return f"{ip}|{ua}"


def get_user_by_id(user_id):
    if not user_id:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return format_user(dict(row))


def format_user(u):
    practices_str = u.get("practices") or ""
    practices_list = [p.strip() for p in practices_str.split(",") if p.strip()] if practices_str else []
    return {
        "id": u["id"],
        "name": u["name"],
        "email": u["email"],
        "phone": u.get("phone") or "",
        "phoneNumber": u.get("phone") or "",
        "department": u.get("department") or "",
        "role": u.get("role") or "Student",
        "bio": u.get("bio") or "",
        "practices": practices_str,
        "creativePractices": practices_list,
        "avatar": u.get("avatar") or f"https://api.dicebear.com/7.x/initials/svg?seed={u['name']}",
        "profilePhoto": u.get("avatar") or f"https://api.dicebear.com/7.x/initials/svg?seed={u['name']}",
        "avatarUrl": u.get("avatar") or f"https://api.dicebear.com/7.x/initials/svg?seed={u['name']}"
    }


def get_current_student():
    # 1. Check Authorization Bearer Token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '').strip()
        if token in sessions_by_token:
            return get_user_by_id(sessions_by_token[token])

    # 2. Check custom token header or query param
    token = request.headers.get('X-Auth-Token') or request.args.get('token')
    if token and token in sessions_by_token:
        return get_user_by_id(sessions_by_token[token])

    # 3. Check student's browser/device session
    device_key = get_device_key()
    if device_key in sessions_by_device:
        return get_user_by_id(sessions_by_device[device_key])

    return None


def extract_uploaded_file_as_data_url(field_names):
    if not request.files:
        return None, None
    for name in field_names:
        if name in request.files:
            file = request.files[name]
            if file and file.filename:
                mime_type = file.mimetype or 'application/octet-stream'
                encoded = base64.b64encode(file.read()).decode('utf-8')
                return f"data:{mime_type};base64,{encoded}", mime_type
    for file in request.files.values():
        if file and file.filename:
            mime_type = file.mimetype or 'application/octet-stream'
            encoded = base64.b64encode(file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}", mime_type
    return None, None


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"status": "OK"})
        origin = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, X-Auth-Token'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response, 200


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, X-Auth-Token'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return response


@app.route('/')
def home():
    return jsonify({"status": "running", "message": "CampusCanvas Multi-Student API is live!"})


# --- 1. STUDENT REGISTRATION ---
@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def signup():
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    name = (data.get('name') or data.get('username') or 'Student').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    phone = (data.get('phone') or data.get('phoneNumber') or '').strip()
    department = (data.get('department') or 'General').strip()
    role = (data.get('role') or 'Student').strip()
    bio = (data.get('bio') or '').strip()

    practices_val = data.get('practices') or data.get('creativePractices') or ''
    if isinstance(practices_val, list):
        practices_val = ", ".join(practices_val)

    if not email:
        return jsonify({"error": "Email address is required", "success": False}), 400

    uploaded_avatar, _ = extract_uploaded_file_as_data_url(['avatar', 'profilePhoto', 'photo', 'image', 'file'])
    avatar_url = (
        uploaded_avatar
        or data.get('avatar')
        or data.get('profilePhoto')
        or data.get('avatarUrl')
        or f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
    )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    existing = c.fetchone()

    if existing:
        # Update existing student record with latest registration info
        c.execute('''
            UPDATE users
            SET name = ?, password = ?, phone = ?, department = ?, role = ?, avatar = ?
            WHERE email = ?
        ''', (name, password, phone, department, role, avatar_url, email))
        user_id = existing["id"]
    else:
        c.execute('''
            INSERT INTO users (name, email, password, phone, department, role, bio, practices, avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, password, phone, department, role, bio, practices_val, avatar_url))
        user_id = c.lastrowid

    conn.commit()
    conn.close()

    user_obj = get_user_by_id(user_id)
    token = str(uuid.uuid4())
    sessions_by_token[token] = user_id
    sessions_by_device[get_device_key()] = user_id

    resp = dict(user_obj)
    resp["success"] = True
    resp["user"] = user_obj
    resp["data"] = user_obj
    resp["token"] = token
    return jsonify(resp)


# --- 2. STUDENT LOGIN & LOGOUT ---
@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email:
        return jsonify({"error": "Please enter your email", "success": False}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Account not found. Please create an account first.", "success": False}), 404

    if row["password"] and password and row["password"] != password:
        conn.close()
        return jsonify({"error": "Invalid password.", "success": False}), 401

    user_id = row["id"]
    conn.close()

    user_obj = get_user_by_id(user_id)
    token = str(uuid.uuid4())
    sessions_by_token[token] = user_id
    sessions_by_device[get_device_key()] = user_id

    resp = dict(user_obj)
    resp["success"] = True
    resp["user"] = user_obj
    resp["data"] = user_obj
    resp["token"] = token
    return jsonify(resp)


@app.route('/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
def logout():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '').strip()
        sessions_by_token.pop(token, None)
    sessions_by_device.pop(get_device_key(), None)
    return jsonify({"success": True, "user": None, "data": None, "message": "Signed out successfully"})


# --- 3. CURRENT STUDENT SESSION & PROFILE ---
@app.route('/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_profile():
    student = get_current_student()

    if request.method in ['PUT', 'PATCH', 'POST']:
        if not student:
            return jsonify({"error": "Not signed in", "success": False}), 401

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        name = data.get('name', student['name'])
        department = data.get('department', student['department'])
        bio = data.get('bio', student['bio'])
        phone = data.get('phone') or data.get('phoneNumber') or student['phone']

        practices_val = data.get('practices') if 'practices' in data else data.get('creativePractices', student['practices'])
        if isinstance(practices_val, list):
            practices_val = ", ".join(practices_val)

        uploaded_avatar, _ = extract_uploaded_file_as_data_url(['avatar', 'profilePhoto', 'photo', 'image', 'file'])
        avatar_url = uploaded_avatar or data.get('avatar') or data.get('profilePhoto') or student['avatar']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE users
            SET name = ?, department = ?, bio = ?, phone = ?, practices = ?, avatar = ?
            WHERE id = ?
        ''', (name, department, bio, phone, str(practices_val), avatar_url, student['id']))
        conn.commit()
        conn.close()

        student = get_user_by_id(student['id'])

    if not student:
        return jsonify({"user": None, "data": None})

    resp = dict(student)
    resp["user"] = student
    resp["data"] = student
    resp["success"] = True
    return jsonify(resp)


# --- 4. ALL STUDENTS / CREATORS DIRECTORY ---
@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
def get_all_students():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    users = [format_user(dict(r)) for r in rows]
    return jsonify({"data": users, "users": users})


@app.route('/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def get_specific_student(user_id):
    if request.method in ['PUT', 'PATCH', 'POST']:
        return handle_profile()
    user_obj = get_user_by_id(user_id)
    if not user_obj:
        return jsonify({"error": "Student not found"}), 404
    resp = dict(user_obj)
    resp["user"] = user_obj
    resp["data"] = user_obj
    return jsonify(resp)


# --- 5. POSTS, CREATIONS & MULTIMEDIA UPLOADS ---
def serialize_posts(rows):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    result = []
    for r in rows:
        post = dict(r)
        c.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC", (post["id"],))
        comments = [
            {
                "id": cm["id"],
                "author": cm["author_name"],
                "authorName": cm["author_name"],
                "authorAvatar": cm["author_avatar"],
                "text": cm["text"],
                "content": cm["text"],
                "createdAt": cm["created_at"]
            }
            for cm in c.fetchall()
        ]
        result.append({
            "id": post["id"],
            "title": post["title"],
            "content": post["content"],
            "description": post["content"],
            "category": post["category"],
            "mediaType": post["media_type"],
            "imageUrl": post["media_url"],
            "mediaUrl": post["media_url"],
            "videoUrl": post["media_url"] if post["media_type"] == "video" else "",
            "audioUrl": post["media_url"] if post["media_type"] == "audio" else "",
            "author": post["author_name"],
            "authorName": post["author_name"],
            "authorId": post["author_id"],
            "authorAvatar": post["author_avatar"],
            "department": post["department"],
            "likes": post["likes"],
            "shares": post["shares"],
            "comments": comments,
            "createdAt": post["created_at"]
        })
    conn.close()
    return result


@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/upload', methods=['POST', 'OPTIONS'])
@app.route('/api/upload', methods=['POST', 'OPTIONS'])
@app.route('/trending', methods=['GET', 'OPTIONS'])
@app.route('/api/trending', methods=['GET', 'OPTIONS'])
@app.route('/explore', methods=['GET', 'OPTIONS'])
@app.route('/api/explore', methods=['GET', 'OPTIONS'])
@app.route('/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/posts/user', methods=['GET', 'OPTIONS'])
def handle_posts():
    student = get_current_student()

    if request.method == 'POST':
        if not student:
            return jsonify({"error": "Please register or sign in to upload your work.", "success": False}), 401

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        uploaded_media, mime_type = extract_uploaded_file_as_data_url(['file', 'media', 'image', 'video', 'audio', 'artwork'])

        media_url = (
            uploaded_media
            or data.get('mediaUrl')
            or data.get('imageUrl')
            or data.get('image')
            or data.get('videoUrl')
            or data.get('audioUrl')
            or ''
        )

        media_type = data.get('mediaType') or data.get('type') or 'image'
        if mime_type:
            if mime_type.startswith('video/'):
                media_type = 'video'
            elif mime_type.startswith('audio/'):
                media_type = 'audio'

        title = data.get('title') or 'Untitled Creation'
        content = data.get('content') or data.get('description') or ''
        category = data.get('category') or 'Photography'
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            INSERT INTO posts (title, content, category, media_type, media_url, author_id, author_name, author_avatar, department, likes, shares, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
        ''', (
            title,
            content,
            category,
            media_type,
            media_url,
            student['id'],
            student['name'],
            student['avatar'],
            student['department'],
            now
        ))
        new_id = c.lastrowid
        conn.commit()
        c.execute("SELECT * FROM posts WHERE id = ?", (new_id,))
        new_row = c.fetchone()
        conn.close()

        new_post = serialize_posts([new_row])[0]
        return jsonify({"success": True, "post": new_post, "data": new_post})

    sort_by = request.args.get('sort', 'latest')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.path in ['/user/posts', '/api/user/posts', '/api/posts/user'] and student:
        c.execute("SELECT * FROM posts WHERE author_id = ? ORDER BY id DESC", (student['id'],))
    elif sort_by == 'trending' or 'trending' in request.path:
        c.execute("SELECT * FROM posts ORDER BY likes DESC, id DESC")
    else:
        c.execute("SELECT * FROM posts ORDER BY id DESC")

    rows = c.fetchall()
    conn.close()
    posts = serialize_posts(rows)
    return jsonify({"data": posts, "posts": posts})


# --- 6. LIKES, COMMENTS, SHARES & BOOKMARKS ---
@app.route('/posts/<int:post_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def single_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
