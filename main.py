from flask import Flask, jsonify, request
import os

app = Flask(__name__)

users_db = {}
current_session_user = None

posts_list = [
    {
        "id": 1,
        "title": "Welcome to CampusCanvas!",
        "content": "Share your photography, drawings, videos, audio, and campus life.",
        "author": "CampusCanvas",
        "department": "Campus Community",
        "likes": 10,
        "category": "Announcement"
    }
]

def normalize_practices(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val.strip():
        return [x.strip() for x in val.split(",") if x.strip()]
    return []

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"status": "OK"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response, 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return response

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
def get_session():
    global current_session_user
    if request.method in ['PUT', 'PATCH', 'POST']:
        data = request.get_json(silent=True) or {}
        if current_session_user is None:
            current_session_user = {"id": 1, "name": "Student", "email": "student@campus.edu", "department": "Computer Science"}
        if 'name' in data and data['name']:
            current_session_user['name'] = data['name']
        if 'department' in data and data['department']:
            current_session_user['department'] = data['department']
        if 'bio' in data:
            current_session_user['bio'] = data['bio']
        if 'practices' in data or 'creativePractices' in data:
            raw = data.get('practices') or data.get('creativePractices')
            current_session_user['practices'] = normalize_practices(raw)
        email = current_session_user.get('email')
        if email:
            users_db[email] = current_session_user
        return jsonify({"success": True, "user": current_session_user})
    return jsonify({"user": current_session_user})

@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
def get_users():
    return jsonify({"data": list(users_db.values())})

@app.route('/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
def logout():
    global current_session_user
    current_session_user = None
    return jsonify({"success": True, "user": None, "message": "Logged out successfully"})

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
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        author_name = current_session_user.get('name', 'Student') if current_session_user else 'Student'
        author_dept = current_session_user.get('department', '') if current_session_user else ''
        new_post = {
            "id": len(posts_list) + 1,
            "title": data.get('title', 'Untitled Work'),
            "content": data.get('content') or data.get('description', ''),
            "category": data.get('category', 'Photography'),
            "imageUrl": data.get('imageUrl') or data.get('image') or data.get('mediaUrl', ''),
            "author": author_name,
            "department": author_dept,
            "likes": 0
        }
        posts_list.insert(0, new_post)
        return jsonify({"success": True, "post": new_post})
    return jsonify({"data": posts_list})

@app.route('/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
@app.route('/bookmarks', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_empty_lists():
    return jsonify({"data": []})

@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def get_user_profile(user_id=None):
    if request.method in ['PUT', 'PATCH', 'POST']:
        return get_session()
    user_data = current_session_user or {
        "id": 1,
        "name": "Student",
        "email": "student@campus.edu",
        "department": "Computer Science"
    }
    resp = dict(user_data)
    resp["data"] = user_data
    return jsonify(resp)

@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def signup():
    global current_session_user
    data = request.get_json(silent=True) or {}
    name = data.get('name') or data.get('username') or 'Student'
    email = (data.get('email') or 'student@campus.edu').strip().lower()
    department = data.get('department') or 'Computer Science'
    role = data.get('role') or 'Student'

    user_obj = {
        "id": len(users_db) + 1,
        "name": name,
        "email": email,
        "department": department,
        "role": role
    }
    users_db[email] = user_obj
    current_session_user = user_obj
    return jsonify({"success": True, "user": user_obj, "token": "mock-token"})

@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    global current_session_user
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if email and email in users_db:
        current_session_user = users_db[email]
    else:
        current_session_user = {
            "id": len(users_db) + 1,
            "name": data.get('name') or (email.split('@')[0] if email else 'Student'),
            "email": email or 'student@campus.edu',
            "department": data.get('department') or 'Computer Science',
            "role": 'Student'
        }
        if email:
            users_db[email] = current_session_user

    return jsonify({"success": True, "user": current_session_user, "token": "mock-token"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

