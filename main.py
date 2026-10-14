from flask import Flask, jsonify, request
import os, uuid, base64
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

users_db = {}
sessions = {}
posts_list = []
events_list = []

def get_current_user():
    tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    email = sessions.get(tok) or sessions.get('latest')
    if email and email in users_db:
        return users_db[email]
    return {
        "id": 1,
        "name": "Student",
        "email": "student@campus.edu",
        "department": "Bsc Computer science",
        "role": "Student",
        "bio": "",
        "practices": ""
    }

def get_uploaded_file():
    for f in request.files.values():
        if f and f.filename:
            m = f.mimetype or 'image/jpeg'
            b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{m};base64,{b64}"
    return None

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
def add_cors(r):
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
@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_profile():
    u = get_current_user()
    if request.method in ['PUT', 'PATCH', 'POST']:
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        for k in ['name', 'department', 'bio', 'phone', 'practices', 'creativePractices']:
            if k in d and d[k] is not None:
                u['practices' if k == 'creativePractices' else k] = d[k]
        f_url = get_uploaded_file()
        if f_url:
            u['avatar'] = f_url
        users_db[u['email']] = u
        return jsonify({"success": True, "user": u})
    return jsonify({
        "id": u.get("id", 1),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "department": u.get("department", ""),
        "bio": u.get("bio", ""),
        "practices": u.get("practices", ""),
        "user": u,
        "data": u
    })

@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def auth():
    d = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (d.get('email') or f"{uuid.uuid4().hex[:6]}@campus.edu").strip().lower()
    ex = users_db.get(email, {})
    u = {
        "id": ex.get("id", len(users_db) + 1),
        "name": d.get('name') or ex.get('name') or email.split('@')[0],
        "email": email,
        "department": d.get('department') or ex.get('department') or 'Bsc Computer science',
        "role": d.get('role') or ex.get('role') or 'Student',
        "bio": d.get('bio') or ex.get('bio') or '',
        "practices": d.get('practices') or ex.get('practices') or ''
    }
    f_url = get_uploaded_file()
    if f_url:
        u['avatar'] = f_url
    users_db[email] = u
    tok = str(uuid.uuid4())
    sessions[tok] = email
    sessions['latest'] = email
    return jsonify({"success": True, "user": u, "token": tok})

@app.route('/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'OPTIONS'])
def logout():
    return jsonify({"success": True, "user": None})

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
    u = get_current_user()
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        img = get_uploaded_file() or d.get('imageUrl') or d.get('image') or d.get('mediaUrl') or ''
        p = {
            "id": len(posts_list) + 1,
            "title": d.get('title', 'Untitled Work'),
            "content": d.get('content') or d.get('description', ''),
            "category": d.get('category', 'Photography'),
            "imageUrl": img,
            "author": u.get('name', 'Student'),
            "department": u.get('department', ''),
            "likes": 0,
            "createdAt": datetime.utcnow().isoformat()
        }
        posts_list.insert(0, p)
        return jsonify({"success": True, "post": p, "data": p})
    return jsonify({"data": posts_list})

@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
def get_users():
    return jsonify({"data": list(users_db.values())})

@app.route('/users/<int:uid>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/<int:uid>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def single_user(uid):
    return handle_profile()

@app.route('/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
@app.route('/bookmarks', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def empty_lists():
    return jsonify({"data": []})

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
