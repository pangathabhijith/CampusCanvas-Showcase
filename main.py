from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# In-memory storage for users and session
users_db = {
    "abhijithpangath911@gmail.com": {
        "id": 1,
        "name": "Abhijith Pangath",
        "email": "abhijithpangath911@gmail.com",
        "department": "Bsc Computer science",
        "role": "Student",
        "bio": "Computer Science student & creator at MES Kalladi College.",
        "practices": "Photography, Drawing"
    }
}

current_session_user = users_db["abhijithpangath911@gmail.com"].copy()

# In-memory storage for posts/uploads
posts_list = [
    {
        "id": 1,
        "title": "Welcome to CampusCanvas!",
        "content": "The backend is successfully connected and running on Render.",
        "description": "The backend is successfully connected and running on Render.",
        "author": "Abhijith Pangath",
        "authorName": "Abhijith Pangath",
        "department": "Bsc Computer science",
        "likes": 100,
        "category": "Announcement",
        "imageUrl": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=800&q=80",
        "createdAt": "2026-10-14T00:00:00Z"
    }
]

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"status": "OK"})
        origin = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response, 200

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return response

@app.route('/')
def home():
    return jsonify({"status": "online", "message": "CampusCanvas API is running!"})

# --- SESSION & CURRENT USER ROUTES ---
@app.route('/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/session', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/me', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_session_and_me():
    global current_session_user
    if request.method in ['PUT', 'PATCH', 'POST']:
        data = request.get_json(silent=True) or {}
        if current_session_user is None:
            current_session_user = users_db["abhijithpangath911@gmail.com"].copy()
        
        for key in ['name', 'department', 'bio', 'practices', 'role', 'email']:
            if key in data and data[key] is not None:
                current_session_user[key] = data[key]
                
        email = current_session_user.get('email')
        if email:
            users_db[email] = current_session_user.copy()

    if current_session_user is None:
        return jsonify({"user": None, "data": None})

    return jsonify({
        "success": True,
        "user": current_session_user,
        "data": current_session_user,
        "id": current_session_user.get("id", 1),
        "name": current_session_user.get("name", "Abhijith Pangath"),
        "email": current_session_user.get("email", "abhijithpangath911@gmail.com"),
        "department": current_session_user.get("department", "Bsc Computer science"),
        "role": current_session_user.get("role", "Student"),
        "bio": current_session_user.get("bio", ""),
        "practices": current_session_user.get("practices", "")
    })

# --- PROFILE ROUTES (VIEW & SAVE CHANGES) ---
@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def handle_user_profile(user_id=None):
    return handle_session_and_me()

# --- AUTHENTICATION: SIGNUP / LOGIN / LOGOUT ---
@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def signup():
    global current_session_user
    data = request.get_json(silent=True) or {}
    
    name = data.get('name') or data.get('username') or 'Abhijith Pangath'
    email = data.get('email') or 'abhijithpangath911@gmail.com'
    department = data.get('department') or 'Bsc Computer science'
    role = data.get('role') or 'Student'
    
    user_obj = {
        "id": len(users_db) + 1,
        "name": name,
        "email": email,
        "department": department,
        "role": role,
        "bio": data.get('bio', ''),
        "practices": data.get('practices', '')
    }
    users_db[email] = user_obj
    current_session_user = user_obj.copy()
    
    return jsonify({
        "success": True,
        "user": current_session_user,
        "data": current_session_user,
        "token": "mock-jwt-token"
    })

@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    global current_session_user
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    
    if email and email in users_db:
        current_session_user = users_db[email].copy()
    else:
        current_session_user = {
            "id": 1,
            "name": data.get('name') or 'Abhijith Pangath',
            "email": email or 'abhijithpangath911@gmail.com',
            "department": data.get('department') or 'Bsc Computer science',
            "role": "Student",
            "bio": "",
            "practices": ""
        }
        if email:
            users_db[email] = current_session_user.copy()
            
    return jsonify({
        "success": True,
        "user": current_session_user,
        "data": current_session_user,
        "token": "mock-jwt-token"
    })

@app.route('/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'OPTIONS'])
def logout():
    global current_session_user
    current_session_user = None
    return jsonify({"success": True, "message": "Logged out successfully"})

# --- POSTS, UPLOADS, TRENDING & EXPLORE ---
@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/works', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/works', methods=['GET', 'POST', 'OPTIONS'])
def handle_posts():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data and request.form:
            data = request.form.to_dict()
            
        author_name = current_session_user.get('name', 'Abhijith Pangath') if current_session_user else 'Abhijith Pangath'
        author_dept = current_session_user.get('department', 'Bsc Computer science') if current_session_user else 'Bsc Computer science'
        
        new_post = {
            "id": len(posts_list) + 1,
            "title": data.get('title') or 'Untitled Artwork',
            "content": data.get('content') or data.get('description') or '',
            "description": data.get('description') or data.get('content') or '',
            "category": data.get('category') or 'Photography',
            "imageUrl": data.get('imageUrl') or data.get('image') or data.get('mediaUrl') or '',
            "author": author_name,
            "authorName": author_name,
            "department": author_dept,
            "likes": 0,
            "createdAt": "2026-10-14T00:00:00Z"
        }
        posts_list.insert(0, new_post)
        return jsonify({"success": True, "post": new_post, "data": new_post})
        
    return jsonify({"data": posts_list, "posts": posts_list})

@app.route('/trending', methods=['GET', 'OPTIONS'])
@app.route('/api/trending', methods=['GET', 'OPTIONS'])
@app.route('/explore', methods=['GET', 'OPTIONS'])
@app.route('/api/explore', methods=['GET', 'OPTIONS'])
@app.route('/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/posts/user', methods=['GET', 'OPTIONS'])
def get_post_collections():
    return jsonify({"data": posts_list, "posts": posts_list})

# --- USERS, CREATORS & EVENTS ---
@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
def get_users():
    users = list(users_db.values())
    return jsonify({"data": users, "users": users})

@app.route('/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_empty_lists():
    return jsonify({"data": [], "events": []})

# --- CATCH-ALL FALLBACK (Prevents unexpected 404 crashes) ---
@app.route('/api/<path:subpath>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
def api_catch_all(subpath):
    return jsonify({"success": True, "data": [], "user": current_session_user})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
