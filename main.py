from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Simple in-memory database storage for this session
users_db = {}
current_session_user = {
    "id": 1,
    "name": "Abhijith Pangath",
    "email": "abhijithpangath911@gmail.com",
    "department": "Bsc Computer science"
}

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/')
def home():
    return "CampusCanvas API is running!"

@app.route('/session')
@app.route('/api/auth/session')
def get_session():
    return jsonify({"user": current_session_user})

@app.route('/posts')
def get_posts():
    sort_by = request.args.get('sort', 'featured')
    return jsonify({
        "data": [
            {
                "id": 1,
                "title": f"Welcome to CampusCanvas ({sort_by} view)!",
                "content": "The backend is successfully connected and running on Render.",
                "author": "System",
                "likes": 100,
                "category": "Announcement"
            }
        ]
    })

@app.route('/events')
@app.route('/creators')
@app.route('/bookmarks')
@app.route('/admin/reports')
@app.route('/admin/posts')
@app.route('/admin/users')
def get_empty_lists():
    return jsonify({"data": []})

@app.route('/user/posts')
@app.route('/api/user/posts')
def get_user_posts():
    return jsonify({
        "data": [
            {
                "id": 1,
                "title": "My First CampusCanvas Post",
                "content": "Hello world!",
                "author": "Abhijith Pangath",
                "likes": 5,
                "category": "General"
            }
        ]
    })

@app.route('/user/profile')
@app.route('/api/user/profile')
def get_user_profile():
    return jsonify({
        "id": 1,
        "name": "Abhijith Pangath",
        "email": "abhijithpangath911@gmail.com",
        "department": "Bsc Computer science"
    })

@app.route('/signup', methods=['POST'])
@app.route('/api/auth/register', methods=['POST'])
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

@app.route('/login', methods=['POST'])
@app.route('/api/auth/login', methods=['POST'])
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
