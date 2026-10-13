from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# This allows your Cloudflare frontend to request data from this Render backend
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
    # Returns an empty session so the frontend doesn't crash looking for a user
    return jsonify(None)

@app.route('/posts')
def get_posts():
    # Returns some dummy data as an array so your React .map() function works perfectly
    return jsonify([
        {
            "id": 1,
            "title": "Welcome to CampusCanvas!",
            "content": "The backend is successfully connected and running on Render.",
            "author": "System",
            "likes": 100
        }
    ])

if __name__ == "__main__":
    # Render provides the PORT dynamically, so we must listen for it
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
