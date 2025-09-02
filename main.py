import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import uuid
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret")
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

active_users = set()
user_active_view = {}

# Initialize DB
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        avatar TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def get_ist_timestamp():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%H:%M')

@app.route("/")
def home():
    if "username" in session:
        return redirect("/chat")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        avatar = request.files.get("avatar")
        avatar_path = None
        if avatar:
            avatar_filename = f"{uuid.uuid4().hex}_{avatar.filename}"
            avatar_path = f"/static/avatars/{avatar_filename}"
            avatar.save(f"static/avatars/{avatar_filename}")
        try:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, avatar) VALUES (?, ?, ?)", (username, password, avatar_path))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            return "Username already exists!"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[0], password):
            session["username"] = username
            active_users.add(username)
            return redirect("/chat")
        else:
            return "Invalid credentials!"
    return render_template("login.html")

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect("/login")
    return render_template("chat.html", username=session["username"])

@app.route("/logout")
def logout():
    username = session.get("username")
    if username:
        active_users.discard(username)
        socketio.emit("user_left", {"username": username}, broadcast=True)
    session.pop("username", None)
    return redirect("/login")

@socketio.on("send_message")
def handle_message(data):
    message_id = str(uuid.uuid4())
    timestamp = get_ist_timestamp()
    username = session.get("username", "Anonymous")
    seen_status = "✅" if user_active_view.get(username) else "✅"
    emit("receive_message", {
        "id": message_id,
        "username": username,
        "message": data["message"],
        "timestamp": timestamp,
        "status": seen_status
    }, broadcast=True)

@socketio.on("delete_message")
def handle_delete(data):
    emit("remove_message", {"id": data["id"]}, broadcast=True)

@socketio.on("edit_message")
def handle_edit(data):
    emit("update_message", {
        "id": data["id"],
        "new_message": data["new_message"]
    }, broadcast=True)

@socketio.on("message_seen")
def handle_seen(data):
    emit("message_seen", {"id": data["id"]}, broadcast=True)

@socketio.on("user_typing")
def handle_typing(data):
    emit("user_typing", {"username": data["username"]}, broadcast=True)

@socketio.on("send_audio")
def handle_audio(data):
    audio_id = str(uuid.uuid4())
    timestamp = get_ist_timestamp()
    emit("receive_audio", {
        "id": audio_id,
        "username": session.get("username", "Anonymous"),
        "audio_data": data["audio_data"],
        "timestamp": timestamp
    }, broadcast=True)

@socketio.on("send_video")
def handle_video(data):
    video_id = str(uuid.uuid4())
    timestamp = get_ist_timestamp()
    emit("receive_video", {
        "id": video_id,
        "username": session.get("username", "Anonymous"),
        "video_data": data["video_data"],
        "timestamp": timestamp
    }, broadcast=True)

@socketio.on("send_file")
def handle_file(data):
    file_id = str(uuid.uuid4())
    timestamp = get_ist_timestamp()
    emit("receive_file", {
        "id": file_id,
        "username": session.get("username", "Anonymous"),
        "file_name": data["file_name"],
        "file_url": data["file_url"],
        "timestamp": timestamp
    }, broadcast=True)

@socketio.on("push_notify")
def handle_push_notify(data):
    emit("trigger_notification", {
        "title": data["title"],
        "body": data["body"]
    }, broadcast=True)

@socketio.on("profile_picture")
def handle_profile_picture(data):
    emit("profile_picture", {
        "username": data["username"],
        "avatar_url": data["avatar_url"]
    }, broadcast=True)

@socketio.on("active_view")
def handle_active_view(data):
    user_active_view[data["username"]] = True

@socketio.on("get_participants")
def handle_get_participants():
    emit("participants_list", {"users": list(active_users)}, room=request.sid)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
