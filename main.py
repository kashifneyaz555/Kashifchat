from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret")
socketio = SocketIO(app)

# Initialize DB
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

init_db()

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
        try:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
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
    session.pop("username", None)
    return redirect("/login")

@socketio.on("send_message")
def handle_message(data):
    emit("receive_message", {
        "username": session.get("username", "Anonymous"),
        "message": data["message"]
    }, broadcast=True)
@socketio.on("delete_message")
def handle_delete(data):
    emit("remove_message", {"id": data["id"]}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
