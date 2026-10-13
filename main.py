from flask import Flask, jsonify, request
import os

app = Flask(__name__)

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

@app.route('/trending', methods=['GET', 'OPTIONS'])
@app.route('/api/trending', methods=['GET', 'OPTIONS'])
@app.route('/explore', methods=['GET', 'OPTIONS'])
@app.route('/api/explore', methods=['GET', 'OPTIONS'])
def get_trending_explore():
    return jsonify({"data": posts_list})

@app.route('/events', methods=['GET', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'OPTIONS'])
def get_events():
    return jsonify({"data": []})

@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
@app.route('/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'OPTIONS'])
@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_empty_lists():
    return jsonify({"data": []})

@app.route('/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/posts/user', methods=['GET', 'OPTIONS'])
def get_user_posts():
    return jsonify({"data": posts_list})

@app.route('/profile', methods=['GET', 'OPTIONS'])
@app.route('/user/profile', methods=['GET', 'OPTIONS'])
@app.route('/api/user/profile', methods=['GET', 'OPTIONS'])
@app.route('/api/profile', methods=['GET', 'OPTIONS'])
@app.route('/api/auth/profile', methods=['GET', 'OPTIONS'])
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

@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
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

@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
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
