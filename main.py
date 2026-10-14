
  from flask import Flask, jsonify, request
import os, sqlite3, uuid, base64, json
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
DB = "campuscanvas.db"

with sqlite3.connect(DB) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, data TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT)")
    conn.commit()

DEFAULT_USER = {
    "id": 1,
    "name": "Student",
    "email": "student@campus.edu",
    "department": "Computer Science",
    "role": "Student",
    "bio": "",
    "practices": ""
}

def get_user():
    with sqlite3.connect(DB) as c:
        tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        row = c.execute("SELECT v FROM state WHERE k = ?", (f"tok:{tok}",)).fetchone() if tok else None
        if not row:
            row = c.execute("SELECT v FROM state WHERE k = 'current_email'").fetchone()
        if row and row[0]:
            u_row = c.execute("SELECT data FROM users WHERE email = ?", (row[0],)).fetchone()
            if u_row:
                return json.loads(u_row[0])
        any_u = c.execute("SELECT data FROM users LIMIT 1").fetchone()
        return json.loads(any_u[0]) if any_u else DEFAULT_USER.copy()

def save_user(u, tok=None):
    email = u["email"]
    with sqlite3.connect(DB) as c:
        c.execute("INSERT OR REPLACE INTO users (email, data) VALUES (?, ?)", (email, json.dumps(u)))
        c.execute("INSERT OR REPLACE INTO state (k, v) VALUES ('current_email', ?)", (email,))
        if tok:
            c.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", (f"tok:{tok}", email))
        c.commit()

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        r = jsonify({"status": "OK"})
        r.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        r.headers['Access-Control-Allow-Credentials'] = 'true'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
        r.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return r, 200

@app.after_request
def add_cors_headers(r):
    r.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    r.headers['Access-Control-Allow-Credentials'] = 'true'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return r

@app.route('/')
def home():
    return "CampusCanvas API is running!"

@app.route('/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_session():
    u = get_user()
    if request.method in ['PUT', 'PATCH', 'POST']:
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        for k in ['name', 'department', 'bio', 'practices', 'creativePractices']:
            if k in d and d[k] is not None:
                u['practices' if k == 'creativePractices' else k] = d[k]
        save_user(u)
        return jsonify({"success": True, "user": u})
    return jsonify({"user": u})

@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_profile():
    u = get_user()
    if request.method in ['PUT', 'PATCH', 'POST']:
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        for k in ['name', 'department', 'bio', 'practices', 'creativePractices']:
            if k in d and d[k] is not None:
                u['practices' if k == 'creativePractices' else k] = d[k]
        save_user(u)
        return jsonify({"success": True, "user": u})
    return jsonify({
        "id": u.get("id", 1),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "department": u.get("department", ""),
        "bio": u.get("bio", ""),
        "practices": u.get("practices", ""),
        "data": u
    })

@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def signup():
    d = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (d.get('email') or f"{uuid.uuid4().hex[:6]}@campus.edu").strip().lower()
    with sqlite3.connect(DB) as c:
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    u = {
        "id": count + 1,
        "name": d.get('name') or d.get('username') or email.split('@')[0],
        "email": email,
        "department": d.get('department') or 'Computer Science',
        "role": d.get('role') or 'Student',
        "bio": d.get('bio') or '',
        "practices": d.get('practices') or ''
    }
    tok = str(uuid.uuid4())
    save_user(u, tok)
    return jsonify({"success": True, "user": u, "token": tok})

@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    d = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (d.get('email') or '').strip().lower()
    with sqlite3.connect(DB) as c:
        row = c.execute("SELECT data FROM users WHERE email = ?", (email,)).fetchone()
    u = json.loads(row[0]) if row else {
        "id": 1,
        "name": d.get('name') or (email.split('@')[0] if email else 'Student'),
        "email": email or 'student@campus.edu',
        "department": d.get('department') or 'Computer Science',
        "role": 'Student',
        "bio": '',
        "practices": ''
    }
    tok = str(uuid.uuid4())
    save_user(u, tok)
    return jsonify({"success": True, "user": u, "token": tok})

@app.route('/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'OPTIONS'])
def logout():
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/trending', methods=['GET', 'OPTIONS'])
@app.route('/api/trending', methods=['GET', 'OPTIONS'])
@app.route('/explore', methods=['GET', 'OPTIONS'])
@app.route('/api/explore', methods=['GET', 'OPTIONS'])
@app.route('/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/posts/user', methods=['GET', 'OPTIONS'])
def handle_posts():
    u = get_user()
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        img = d.get('imageUrl') or d.get('image') or d.get('mediaUrl') or ''
        for f in request.files.values():
            if f and f.filename:
                m = f.mimetype or 'image/jpeg'
                img = f"data:{m};base64,{base64.b64encode(f.read()).decode()}"
        p = {
            "title": d.get('title', 'Untitled Work'),
            "content": d.get('content') or d.get('description', ''),
            "category": d.get('category', 'Photography'),
            "imageUrl": img,
            "author": u.get('name', 'Student'),
            "department": u.get('department', ''),
            "likes": 0,
            "createdAt": datetime.utcnow().isoformat()
        }
        with sqlite3.connect(DB) as c:
            cur = c.execute("INSERT INTO posts (data) VALUES (?)", (json.dumps(p),))
            p["id"] = cur.lastrowid
            c.commit()
        return jsonify({"success": True, "post": p})
    with sqlite3.connect(DB) as c:
        rows = c.execute("SELECT id, data FROM posts ORDER BY id DESC").fetchall()
    posts = [json.loads(r[1]) | {"id": r[0]} for r in rows]
    return jsonify({"data": posts})

@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
def get_users():
    with sqlite3.connect(DB) as c:
        users = [json.loads(r[0]) for r in c.execute("SELECT data FROM users").fetchall()]
    return jsonify({"data": users})

@app.route('/events', methods=['GET', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
@app.route('/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_empty_lists():
    return jsonify({"data": []})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
