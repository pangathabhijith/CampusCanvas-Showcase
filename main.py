from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Simple in-memory storage
users_db = {}
current_session_user = {
    "id": 1,
    "name": "Abhijith Pangath",
    "email": "abhijithpangath911@gmail.com",
    "department": "Bsc Computer science"
}

posts_list = [
    {
        "id": 1,
        "title": "Welcome to CampusCanvas!",
        "content": "The backend is successfully connected and running on Render.",
        "author": "System",
        "likes": 100,
        "category": "Announcement"
    }
]

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/')
def home():
    return "CampusCanvas API is running!"

# Session and User Me routes
@app.route('/session')
@app.route('/api/auth/session')
@app.route('/me')
@app.route('/api/auth/me')
@app.route('/api/me')
@app.route('/users/me')
@app.route('/api/users/me')
def get_session():
    return jsonify({"user": current_session_user})

# Users list route
@app.route('/users')
@app.route('/api/users')
def get_users():
    return jsonify({"data": list(users_db.values())})

# Logout routes
@app.route('/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'OPTIONS'])
def logout():
    global current_session_user
    current_session_user = None
    return jsonify({"success": True, "message": "Logged out successfully"})

# Posts routes (handling queries like ?sort=trending&limit=4)
@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
def handle_posts():
    if request.method == 'POST':
        data = request.get_json() or {}
        new_post = {
            "id": len(posts_list) + 1,
            "title": data.get('title', 'Untitled Art / Photo'),
            "content": data.get('content', ''),
            "category": data.get('category', 'Photography'),
            "author": current_session_user.get('name', 'Abhijith Pangath'),
            "likes": 0
        }
        posts_list.insert(0, new_post)
        return jsonify({"success": True, "post": new_post})
    
    return jsonify({"data": posts_list})

# Trending & Explore routes
@app.route('/trending')
@app.route('/api/trending')
@app.route('/explore')
@app.route('/api/explore')
def get_trending_explore():
    return jsonify({"data": posts_list})

# Events routes
@app.route('/events')
@app.route('/api/events')
def get_events():
    return jsonify({"data": []})

# Other empty lists
@app.route('/creators')
@app.route('/api/creators')
@app.route('/bookmarks')
@app.route('/api/bookmarks')
@app.route('/admin/reports')
@app.route('/admin/posts')
@app.route('/admin/users')
def get_empty_lists():
    return jsonify({"data": []})

# User posts
@app.route('/user/posts')
@app.route('/api/user/posts')
@app.route('/api/posts/user')
def get_user_posts():
    return jsonify({"data": posts_list})

# Profile routes
@app.route('/profile')
@app.route('/user/profile')
@app.route('/api/user/profile')
@app.route('/api/profile')
@app.route('/api/auth/profile')
def get_user_profile():
    user_data = current_session_user or {
        "id": 1,
        "name": "Abhijith Pangath",
        "email": "abhijithpangath911@gmail.com",
        "department": "Bsc Computer science"
    }
    return jsonify({
        "data": user_data,
        **user_data
    })

# Signup / Register
@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
def signup():
    global current_session_user
    data = request.get_json() or {}
    name = data.get('name', 'Abhijith Pangath')
    email = data.get('email', 'abhijithpangath911@gmail.com')
    department = data.get('department', 'Bsc Computer science')
    
    user_obj = {
        "id": len(users_db) + 1,
        "name": name,
        "email": email,
        "department": department
    }
    users_db[email] = user_obj
    current_session_user = user_obj
    
    return jsonify({"success": True, "user": user_obj})

# Login
@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    global current_session_user
    data = request.get_json() or {}
    email = data.get('email')
    
    if email in users_db:
        current_session_user = users_db[email]
    else:
        current_session_user = {
            "id": 1,
            "name": data.get('name', 'Abhijith Pangath'),
            "email": email or 'abhijithpangath911@gmail.com',
            "department": 'Bsc Computer science'
        }
        
    return jsonify({"success": True, "user": current_session_user, "token": "mock-token"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
