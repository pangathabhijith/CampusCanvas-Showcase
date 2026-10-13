from flask import Flask, jsonify, request
import os
import base64
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Allow up to 50MB uploads for video/audio/photos

# Pre-loaded user database
users_db = {
    "abhijithpangath911@gmail.com": {
        "id": 1,
        "name": "Abhijith Pangath",
        "email": "abhijithpangath911@gmail.com",
        "password": "password123",
        "phone": "",
        "department": "Bsc Computer science",
        "role": "Student",
        "bio": "Computer Science student at MES Kalladi College.",
        "practices": "Photography, Drawing",
        "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=Abhijith%20Pangath"
    },
    "pangathabhijith@gmail.com": {
        "id": 2,
        "name": "Abhijith Pangath",
        "email": "pangathabhijith@gmail.com",
        "password": "password123",
        "phone": "",
        "department": "Bsc Computer science",
        "role": "Student",
        "bio": "Computer Science student at MES Kalladi College.",
        "practices": "Photography, Drawing",
        "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=Abhijith%20Pangath"
    }
}

current_session_user = users_db["abhijithpangath911@gmail.com"].copy()

# In-memory storage for creations (photos, videos, audio, drawings, campus life)
posts_list = [
    {
        "id": 1,
        "title": "Welcome to CampusCanvas!",
        "content": "Share your photography, drawings, videos, audio, and campus life moments.",
        "description": "Share your photography, drawings, videos, audio, and campus life moments.",
        "author": "Abhijith Pangath",
        "authorName": "Abhijith Pangath",
        "authorId": 1,
        "authorAvatar": "https://api.dicebear.com/7.x/initials/svg?seed=Abhijith%20Pangath",
        "department": "Bsc Computer science",
        "category": "Campus Life",
        "mediaType": "image",
        "imageUrl": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=800&auto=format&fit=crop&q=60",
        "mediaUrl": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=800&auto=format&fit=crop&q=60",
        "likes": 12,
        "likedBy": [],
        "shares": 3,
        "comments": [
            {
                "id": 1,
                "author": "Abhijith Pangath",
                "text": "Excited to see everyone's creations!",
                "createdAt": datetime.utcnow().isoformat()
            }
        ],
        "createdAt": datetime.utcnow().isoformat()
    }
]

events_list = [
    {
        "id": 1,
        "title": "MES Kalladi College Art & Tech Fest",
        "description": "Showcase your photography, drawings, music, and projects!",
        "date": "2026-11-01",
        "location": "Main Auditorium",
        "organizer": "Abhijith Pangath"
    }
]

bookmarks_list = []

def extract_uploaded_file_as_data_url(field_names):
    """Converts an uploaded file (image/video/audio) into a Base64 Data URL."""
    if not request.files:
        return None, None
    for name in field_names:
        if name in request.files:
            file = request.files[name]
            if file and file.filename:
                mime_type = file.mimetype or 'application/octet-stream'
                encoded = base64.b64encode(file.read()).decode('utf-8')
                return f"data:{mime_type};base64,{encoded}", mime_type
    # Fallback: take the first available file
    for file in request.files.values():
        if file and file.filename:
            mime_type = file.mimetype or 'application/octet-stream'
            encoded = base64.b64encode(file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}", mime_type
    return None, None

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
    return jsonify({"status": "running", "message": "CampusCanvas API is live!"})

# --- 1. REGISTRATION (Requires Email, Password, Phone, Profile Photo) ---
@app.route('/signup', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
@app.route('/register', methods=['POST', 'OPTIONS'])
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def signup():
    global current_session_user
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    
    name = data.get('name') or data.get('username') or 'Abhijith Pangath'
    email = (data.get('email') or 'abhijithpangath911@gmail.com').strip().lower()
    password = data.get('password') or 'defaultpass'
    phone = data.get('phone') or data.get('phoneNumber') or ''
    department = data.get('department') or 'Bsc Computer science'
    role = data.get('role') or 'Student'
    
    # Handle Profile Photo (file upload or URL)
    uploaded_avatar, _ = extract_uploaded_file_as_data_url(['avatar', 'profilePhoto', 'photo', 'image', 'file'])
    avatar_url = (
        uploaded_avatar
        or data.get('avatar')
        or data.get('profilePhoto')
        or data.get('avatarUrl')
        or f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
    )
    
    user_obj = {
        "id": len(users_db) + 1,
        "name": name,
        "email": email,
        "password": password,
        "phone": phone,
        "phoneNumber": phone,
        "department": department,
        "role": role,
        "bio": data.get('bio', ''),
        "practices": data.get('practices', ''),
        "avatar": avatar_url,
        "profilePhoto": avatar_url,
        "avatarUrl": avatar_url
    }
    users_db[email] = user_obj
    current_session_user = user_obj.copy()
    
    resp = user_obj.copy()
    resp["success"] = True
    resp["user"] = user_obj
    resp["data"] = user_obj
    resp["token"] = "campuscanvas-jwt-token"
    return jsonify(resp)

# --- 2. LOGIN & LOGOUT ---
@app.route('/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    global current_session_user
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (data.get('email') or '').strip().lower()
    
    if email and email in users_db:
        current_session_user = users_db[email].copy()
    else:
        name = data.get('name') or 'Abhijith Pangath'
        current_session_user = {
            "id": len(users_db) + 1,
            "name": name,
            "email": email or 'abhijithpangath911@gmail.com',
            "phone": data.get('phone', ''),
            "department": data.get('department') or 'Bsc Computer science',
            "role": "Student",
            "bio": "",
            "practices": "",
            "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        }
        if email:
            users_db[email] = current_session_user.copy()
            
    resp = current_session_user.copy()
    resp["success"] = True
    resp["user"] = current_session_user
    resp["data"] = current_session_user
    resp["token"] = "campuscanvas-jwt-token"
    return jsonify(resp)

@app.route('/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/auth/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
@app.route('/api/logout', methods=['POST', 'GET', 'DELETE', 'OPTIONS'])
def logout():
    global current_session_user
    current_session_user = None
    return jsonify({"success": True, "user": None, "message": "Logged out successfully"})

# --- 3. SESSION & PROFILE MANAGEMENT ---
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
def handle_user_session_and_profile():
    global current_session_user
    
    if request.method in ['PUT', 'PATCH', 'POST']:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        if current_session_user is None:
            current_session_user = users_db["abhijithpangath911@gmail.com"].copy()
            
        for field in ['name', 'department', 'bio', 'phone', 'phoneNumber']:
            if field in data and data[field] is not None:
                current_session_user[field] = data[field]
                
        if 'practices' in data:
            current_session_user['practices'] = data['practices']
        if 'creativePractices' in data:
            current_session_user['practices'] = data['creativePractices']
            
        uploaded_avatar, _ = extract_uploaded_file_as_data_url(['avatar', 'profilePhoto', 'photo', 'image', 'file'])
        if uploaded_avatar:
            current_session_user['avatar'] = uploaded_avatar
            current_session_user['profilePhoto'] = uploaded_avatar
        elif data.get('avatar') or data.get('profilePhoto'):
            avatar_val = data.get('avatar') or data.get('profilePhoto')
            current_session_user['avatar'] = avatar_val
            current_session_user['profilePhoto'] = avatar_val
            
        email = current_session_user.get('email')
        if email:
            users_db[email] = current_session_user.copy()

    if current_session_user is None:
        return jsonify({"user": None, "data": None})

    resp = current_session_user.copy()
    resp["user"] = current_session_user
    resp["data"] = current_session_user
    resp["success"] = True
    return jsonify(resp)

@app.route('/users', methods=['GET', 'OPTIONS'])
@app.route('/api/users', methods=['GET', 'OPTIONS'])
@app.route('/creators', methods=['GET', 'OPTIONS'])
@app.route('/api/creators', methods=['GET', 'OPTIONS'])
def get_users():
    return jsonify({"data": list(users_db.values()), "users": list(users_db.values())})

@app.route('/users/<user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
@app.route('/api/users/<user_id>', methods=['GET', 'PUT', 'PATCH', 'POST', 'OPTIONS'])
def get_or_update_specific_user(user_id):
    return handle_user_session_and_profile()

# --- 4. UPLOADS & LATEST CREATIONS FEED (Photos, Videos, Audio, Drawings, Events) ---
@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/upload', methods=['POST', 'OPTIONS'])
@app.route('/api/upload', methods=['POST', 'OPTIONS'])
@app.route('/trending', methods=['GET', 'OPTIONS'])
@app.route('/api/trending', methods=['GET', 'OPTIONS'])
@app.route('/explore', methods=['GET', 'OPTIONS'])
@app.route('/api/explore', methods=['GET', 'OPTIONS'])
@app.route('/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/user/posts', methods=['GET', 'OPTIONS'])
@app.route('/api/posts/user', methods=['GET', 'OPTIONS'])
def handle_posts():
    if request.method == 'POST':
        # Require account login to upload
        if current_session_user is None:
            return jsonify({"error": "Please register or sign in before uploading.", "success": False}), 401
            
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        uploaded_media, mime_type = extract_uploaded_file_as_data_url(['file', 'media', 'image', 'video', 'audio', 'artwork'])
        
        media_url = (
            uploaded_media
            or data.get('mediaUrl')
            or data.get('imageUrl')
            or data.get('image')
            or data.get('videoUrl')
            or data.get('audioUrl')
            or ''
        )
        
        # Detect media type (photo/drawing, video, audio)
        media_type = data.get('mediaType') or data.get('type') or 'image'
        if mime_type:
            if mime_type.startswith('video/'):
                media_type = 'video'
            elif mime_type.startswith('audio/'):
                media_type = 'audio'
                
        new_post = {
            "id": len(posts_list) + 1,
            "title": data.get('title', 'Untitled Creation'),
            "content": data.get('content') or data.get('description', ''),
            "description": data.get('description') or data.get('content', ''),
            "category": data.get('category', 'Photography'),
            "mediaType": media_type,
            "imageUrl": media_url,
            "mediaUrl": media_url,
            "videoUrl": media_url if media_type == 'video' else data.get('videoUrl', ''),
            "audioUrl": media_url if media_type == 'audio' else data.get('audioUrl', ''),
            "author": current_session_user.get('name', 'Abhijith Pangath'),
            "authorName": current_session_user.get('name', 'Abhijith Pangath'),
            "authorId": current_session_user.get('id', 1),
            "authorAvatar": current_session_user.get('avatar', ''),
            "department": current_session_user.get('department', 'Bsc Computer science'),
            "likes": 0,
            "likedBy": [],
            "shares": 0,
            "comments": [],
            "createdAt": datetime.utcnow().isoformat()
        }
        # Insert at index 0 so it immediately appears first in "Latest Creations"
        posts_list.insert(0, new_post)
        return jsonify({"success": True, "post": new_post, "data": new_post})
        
    # Handle sorting (?sort=latest, ?sort=trending, ?sort=featured)
    sort_by = request.args.get('sort', 'latest')
    results = list(posts_list)
    if sort_by == 'trending':
        results.sort(key=lambda x: x.get('likes', 0), reverse=True)
        
    return jsonify({"data": results, "posts": results})

# --- 5. LIKES, COMMENTS, SHARES & FAVORITES (BOOKMARKS) ---
@app.route('/posts/<int:post_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def single_post(post_id):
    for post in posts_list:
        if post['id'] == post_id:
            return jsonify({"data": post, "post": post, **post})
    return jsonify({"error": "Post not found"}), 404

@app.route('/posts/<int:post_id>/like', methods=['POST', 'PUT', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>/like', methods=['POST', 'PUT', 'OPTIONS'])
def like_post(post_id):
    for post in posts_list:
        if post['id'] == post_id:
            post['likes'] = post.get('likes', 0) + 1
            return jsonify({"success": True, "likes": post['likes'], "post": post, "data": post})
    return jsonify({"error": "Post not found"}), 404

@app.route('/posts/<int:post_id>/share', methods=['POST', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>/share', methods=['POST', 'OPTIONS'])
def share_post(post_id):
    for post in posts_list:
        if post['id'] == post_id:
            post['shares'] = post.get('shares', 0) + 1
            return jsonify({"success": True, "shares": post['shares'], "post": post})
    return jsonify({"error": "Post not found"}), 404

@app.route('/posts/<int:post_id>/comments', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>/comments', methods=['GET', 'POST', 'OPTIONS'])
def handle_comments(post_id):
    for post in posts_list:
        if post['id'] == post_id:
            if request.method == 'POST':
                data = request.get_json(silent=True) or request.form.to_dict() or {}
                author_name = current_session_user.get('name', 'Student') if current_session_user else 'Guest'
                new_comment = {
                    "id": len(post.get('comments', [])) + 1,
                    "author": author_name,
                    "authorName": author_name,
                    "authorAvatar": current_session_user.get('avatar', '') if current_session_user else '',
                    "text": data.get('text') or data.get('content') or data.get('comment', ''),
                    "content": data.get('text') or data.get('content') or data.get('comment', ''),
                    "createdAt": datetime.utcnow().isoformat()
                }
                post.setdefault('comments', []).append(new_comment)
                return jsonify({"success": True, "comment": new_comment, "data": post['comments']})
            return jsonify({"data": post.get('comments', []), "comments": post.get('comments', [])})
    return jsonify({"data": [], "comments": []})

@app.route('/bookmarks', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
@app.route('/api/bookmarks', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
@app.route('/posts/<int:post_id>/bookmark', methods=['POST', 'DELETE', 'OPTIONS'])
@app.route('/api/posts/<int:post_id>/bookmark', methods=['POST', 'DELETE', 'OPTIONS'])
def handle_bookmarks(post_id=None):
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        target_id = post_id or data.get('postId') or data.get('id')
        for post in posts_list:
            if post['id'] == target_id and post not in bookmarks_list:
                bookmarks_list.append(post)
        return jsonify({"success": True, "data": bookmarks_list, "bookmarks": bookmarks_list})
    return jsonify({"data": bookmarks_list, "bookmarks": bookmarks_list})

# --- 6. CAMPUS EVENTS & ADMIN ---
@app.route('/events', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/events', methods=['GET', 'POST', 'OPTIONS'])
def handle_events():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        new_event = {
            "id": len(events_list) + 1,
            "title": data.get('title', 'Campus Event'),
            "description": data.get('description') or data.get('content', ''),
            "date": data.get('date', 'Upcoming'),
            "location": data.get('location', 'MES Kalladi College'),
            "organizer": current_session_user.get('name', 'Abhijith Pangath') if current_session_user else 'Campus Admin'
        }
        events_list.insert(0, new_event)
        return jsonify({"success": True, "event": new_event, "data": new_event})
    return jsonify({"data": events_list, "events": events_list})

@app.route('/admin/reports', methods=['GET', 'OPTIONS'])
@app.route('/admin/posts', methods=['GET', 'OPTIONS'])
@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_admin_lists():
    return jsonify({"data": []})

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
