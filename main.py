from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Persistent in-memory database of registered users
users_db = {}
# Default active session user initialized with your profile details
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
        "author": "Abhijith Pangath",
        "likes": 100,
        "category": "Announcement"
    }
]

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"status": "OK"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        return response, 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route('/')
def home():
    return "CampusCanvas API is running!"

@app.route('/session', methods=['GET', 'OPTIONS'])
@app.route('/api/auth/session', methods=['GET', 'OPTIONS'])
@app.route('/me', methods=['GET', 'OPTIONS'])
@app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
@app.route('/api/me', methods=['GET', 'OPTIONS'])
@app.route('/users/me', methods=['GET', 'OPTIONS'])
@app.route('/api/users/me', methods=['GET', 'OPTIONS'])
def get_session():
    return jsonify({"user": current_session_user})

@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
def get_users():
    return jsonify({"data": list(users_db.values())})

@app.route('/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'OPTIONS'])
def logout():
    global current_session_user
    current_session_user = None
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
def handle_posts():
    if request.method == 'POST':
        data = request.get_json() or {}
        author_name = current_session_user.get('name', 'Abhijith Pangath') if current_session_user else 'Abhijith Pangath'
        new_post = {
            "id": len(posts_list) + 1,
            "title": data.get('title', 'Untitled Art / Photo'),
            "content": data.get('content', ''),
            "category": data.get('category', 'Photography'),
            "author": author_name,
            "likes": 0
        }
        posts_list.insert(0, new_post)
        return jsonify({"success": True, "post": new_post})
    return jsonify({"data": posts_list})

@app
