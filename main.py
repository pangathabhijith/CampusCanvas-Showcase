from flask import Flask, jsonify, request
import os

app = Flask(__name__)

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
def get_session():
    return jsonify({"user": None})

@app.route('/posts')
def get_posts():
    sort_by = request.args.get('sort', 'featured')
    return jsonify([
            {
                "id": 1,
                "title": f"Welcome to CampusCanvas ({sort_by} view)!",
                "content": "The backend is successfully connected and running on Render.",
                "author": "System",
                "likes": 100,
                "category": "Announcement"
            }
    ])

@app.route('/events')
@app.route('/creators')
@app.route('/bookmarks')
@app.route('/admin/reports')
@app.route('/admin/posts')
@app.route('/admin/users')
def get_empty_lists():
    return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
