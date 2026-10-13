from flask import Flask, jsonify, request
import os, sqlite3, uuid, base64, json
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
DB = "campuscanvas.db"
sessions = {}

with sqlite3.connect(DB) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, data TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)")
    conn.commit()

def to_list(val):
    if isinstance(val, list): return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip(): return [x.strip() for x in val.split(',') if x.strip()]
    return []

def get_all_users():
    with sqlite3.connect(DB) as c:
        return {r[0]: json.loads(r[1]) for r in c.execute("SELECT email, data FROM users").fetchall()}

def save_user(email, u):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT OR REPLACE INTO users (email, data) VALUES (?, ?)", (email, json.dumps(u)))
        c.commit()

def get_all_posts():
    with sqlite3.connect(DB) as c:
        return [json.loads(r[1]) | {"id": r[0]} for r in c.execute("SELECT id, data FROM posts ORDER BY id DESC").fetchall()]

def dev_key():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0]
    return f"{ip}|{request.headers.get('User-Agent', '')}"

def get_user():
    tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    email = sessions.get(tok) or sessions.get(dev_key())
    return get_all_users().get(email) if email else None

def get_file():
    for f in request.files.values():
        if f and f.filename:
            m = f.mimetype or 'image/jpeg'
            return f"data:{m};base64,{base64.b64encode(f.read()).decode()}", m
    return None, None

@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    r.headers['Access-Control-Allow-Credentials'] = 'true'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return r

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
def router(path):
    if request.method == 'OPTIONS': return jsonify({"status": "OK"}), 200
    parts = [p for p in path.lower().split('/') if p]
    if not parts: return jsonify({"status": "CampusCanvas Live!"})

    d = request.get_json(silent=True) or request.form.to_dict() or {}
    users = get_all_users()
    u = get_user()

    # 1. SIGN OUT
    if 'logout' in parts:
        sessions.pop(request.headers.get('Authorization', '').replace('Bearer ', '').strip(), None)
        sessions.pop(dev_key(), None)
        return jsonify({"success": True, "user": None, "data": None})

    # 2. REGISTER & LOGIN (Multi-Student Persistent)
    if any(k in parts for k in ['register', 'signup', 'login']):
        email = (d.get('email') or f"{uuid.uuid4().hex[:6]}@campus.edu").strip().lower()
        ex = users.get(email, {})
        name = d.get('name') or ex.get('name') or email.split('@')[0]
        f_url, _ = get_file()
        av = f_url or d.get('avatar') or ex.get('avatar') or f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        prac = to_list(d.get('practices') or d.get('creativePractices') or ex.get('practices', []))
        u = {
            "id": ex.get('id', len(users) + 1), "name": name, "email": email,
            "phone": d.get('phone') or ex.get('phone', ''),
            "department": d.get('department') or ex.get('department', 'Computer Science'),
            "role": d.get('role') or ex.get('role', 'Student'), "bio": d.get('bio') or ex.get('bio', ''),
            "practices": prac, "creativePractices": prac, "skills": prac, "badges": [], "bookmarks": [],
            "avatar": av, "profilePhoto": av, "avatarUrl": av
        }
        save_user(email, u)
        tok = str(uuid.uuid4())
        sessions[tok] = sessions[dev_key()] = email
        return jsonify({**u, "user": u, "data": u, "token": tok, "success": True})

    # 3. PROFILE & SESSION (View & Save Changes)
    if any(k in parts for k in ['session', 'me', 'profile']):
        if request.method in ['PUT', 'PATCH', 'POST'] and u:
            f_url, _ = get_file()
            for k in ['name', 'department', 'bio', 'phone']:
                if k in d and d[k] is not None: u[k] = d[k]
            if 'practices' in d or 'creativePractices' in d:
                u['practices'] = u['creativePractices'] = to_list(d.get('practices') or d.get('creativePractices'))
            if f_url or d.get('avatar'): u['avatar'] = u['profilePhoto'] = u['avatarUrl'] = f_url or d.get('avatar')
            save_user(u['email'], u)
        return jsonify({**u, "user": u, "data": u, "success": True} if u else {"user": None, "data": None})

    # 4. UPLOADS, POSTS, LIKES & COMMENTS
    if any(k in parts for k in ['posts', 'upload', 'trending', 'explore']):
        posts = get_all_posts()
        if 'like' in parts or 'comments' in parts:
            pid = next((int(s) for s in parts if s.isdigit()), 0)
            for p in posts:
                if p['id'] == pid:
                    if 'like' in parts: p['likes'] = p.get('likes', 0) + 1
                    elif request.method == 'POST':
                        p.setdefault('comments', []).append({"id": len(p.get('comments', []))+1, "author": u['name'] if u else 'Student', "authorName": u['name'] if u else 'Student', "text": d.get('text') or d.get('content', ''), "createdAt": datetime.utcnow().isoformat()})
                    with sqlite3.connect(DB) as c: c.execute("UPDATE posts SET data = ? WHERE id = ?", (json.dumps(p), pid)); c.commit()
                    return jsonify({"success": True, "post": p, "data": p.get('comments', []) if 'comments' in parts else p})
        if request.method == 'POST':
            if not u: return jsonify({"error": "Sign in required"}), 401
            f_url, mime = get_file()
            m_url = f_url or d.get('mediaUrl') or d.get('imageUrl') or d.get('image') or ''
            p = {
                "title": d.get('title', 'Untitled'), "content": d.get('content') or d.get('description', ''),
                "description": d.get('description') or d.get('content', ''), "category": d.get('category', 'Photography'),
                "mediaType": 'video' if (mime and 'video' in mime) else ('audio' if (mime and 'audio' in mime) else 'image'),
                "imageUrl": m_url, "mediaUrl": m_url, "author": u['name'], "authorName": u['name'], "authorId": u['id'],
                "authorAvatar": u['avatar'], "department": u['department'], "tags": to_list(d.get('tags')),
                "likes": 0, "likedBy": [], "comments": [], "createdAt": datetime.utcnow().isoformat()
            }
            with sqlite3.connect(DB) as c:
                cur = c.execute("INSERT INTO posts (data) VALUES (?)", (json.dumps(p),))
                p["id"] = cur.lastrowid; c.commit()
            return jsonify({"success": True, "post": p, "data": p})
        res = sorted(posts, key=lambda x: x.get('likes', 0), reverse=True) if 'trending' in parts or request.args.get('sort') == 'trending' else posts
        return jsonify({"data": res, "posts": res})

    if 'users' in parts or 'creators' in parts:
        return jsonify({"data": list(users.values()), "users": list(users.values())})
    return jsonify({"data": [], "events": [], "bookmarks": []})

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
