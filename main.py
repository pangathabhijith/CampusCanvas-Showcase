from flask import Flask, jsonify, request
import os, uuid, base64
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
users, sessions, posts, events = {}, {}, [], []

def dev_key():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0]
    return f"{ip}|{request.headers.get('User-Agent', '')}"

def get_user():
    tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    return users.get(sessions.get(tok) or sessions.get(dev_key()))

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
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    if not path:
        return jsonify({"status": "CampusCanvas Live!"})

    d = request.get_json(silent=True) or request.form.to_dict() or {}
    u = get_user()

    # 1. SIGN OUT
    if 'logout' in path:
        sessions.pop(request.headers.get('Authorization', '').replace('Bearer ', '').strip(), None)
        sessions.pop(dev_key(), None)
        return jsonify({"success": True, "user": None, "data": None})

    # 2. REGISTER & LOGIN (Multi-Student)
    if any(k in path for k in ['register', 'signup', 'login']):
        email = (d.get('email') or f"{uuid.uuid4().hex[:6]}@campus.edu").strip().lower()
        name = d.get('name') or users.get(email, {}).get('name') or email.split('@')[0]
        f_url, _ = get_file()
        av = f_url or d.get('avatar') or users.get(email, {}).get('avatar') or f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        u = {
            "id": users.get(email, {}).get('id', len(users) + 1),
            "name": name, "email": email, "phone": d.get('phone', ''),
            "department": d.get('department') or users.get(email, {}).get('department', 'General'),
            "role": d.get('role', 'Student'), "bio": users.get(email, {}).get('bio', ''),
            "practices": users.get(email, {}).get('practices', ''), "avatar": av, "profilePhoto": av
        }
        users[email] = u
        tok = str(uuid.uuid4())
        sessions[tok] = sessions[dev_key()] = email
        return jsonify({**u, "user": u, "data": u, "token": tok, "success": True})

    # 3. PROFILE & SESSION (View & Save Changes)
    if any(k in path for k in ['session', 'me', 'profile']):
        if request.method in ['PUT', 'PATCH', 'POST'] and u:
            f_url, _ = get_file()
            for k in ['name', 'department', 'bio', 'phone', 'practices', 'creativePractices']:
                if k in d: u['practices' if k == 'creativePractices' else k] = ", ".join(d[k]) if isinstance(d[k], list) else d[k]
            if f_url or d.get('avatar'): u['avatar'] = u['profilePhoto'] = f_url or d.get('avatar')
        return jsonify({**u, "user": u, "data": u, "success": True} if u else {"user": None, "data": None})

    # 4. LIKES & COMMENTS
    if 'like' in path or 'comment' in path:
        pid = next((int(s) for s in path.split('/') if s.isdigit()), 0)
        for p in posts:
            if p['id'] == pid:
                if 'like' in path: p['likes'] += 1
                elif request.method == 'POST':
                    p['comments'].append({"id": len(p['comments'])+1, "author": u['name'] if u else 'Student', "text": d.get('text') or d.get('content', ''), "createdAt": datetime.utcnow().isoformat()})
                return jsonify({"success": True, "post": p, "data": p['comments'] if 'comment' in path else p})

    # 5. UPLOADS & FEEDS (Photos, Videos, Audio, Drawings)
    if any(k in path for k in ['posts', 'upload', 'trending', 'explore']):
        if request.method == 'POST':
            if not u: return jsonify({"error": "Sign in required"}), 401
            f_url, mime = get_file()
            m_url = f_url or d.get('mediaUrl') or d.get('imageUrl') or d.get('image') or ''
            p = {
                "id": len(posts) + 1, "title": d.get('title', 'Untitled'), "content": d.get('content') or d.get('description', ''),
                "description": d.get('description') or d.get('content', ''), "category": d.get('category', 'Photography'),
                "mediaType": 'video' if (mime and 'video' in mime) else ('audio' if (mime and 'audio' in mime) else 'image'),
                "imageUrl": m_url, "mediaUrl": m_url, "author": u['name'], "authorName": u['name'],
                "authorAvatar": u['avatar'], "department": u['department'], "likes": 0, "comments": [], "createdAt": datetime.utcnow().isoformat()
            }
            posts.insert(0, p)
            return jsonify({"success": True, "post": p, "data": p})
        res = sorted(posts, key=lambda x: x['likes'], reverse=True) if 'trending' in path or request.args.get('sort') == 'trending' else posts
        return jsonify({"data": res, "posts": res})

    # 6. USERS, EVENTS & OTHER LISTS
    if 'users' in path or 'creators' in path:
        return jsonify({"data": list(users.values()), "users": list(users.values())})
    return jsonify({"data": events, "events": events, "bookmarks": []})

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
