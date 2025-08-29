import os
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your_secret_key_here")
app.config['SECRET_KEY'] = app.secret_key

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Password for accessing the chat
CHAT_PASSWORD = os.environ.get("CHAT_PASSWORD", "24446666678910")

# Store active users and messages in memory
active_users = set()
chat_messages = []
message_counter = 0  # Unique ID generator

@app.route('/')
def index():
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == CHAT_PASSWORD:
            session['authenticated'] = True
            session.permanent = True
            flash('Access granted! Welcome to KashifChat.', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Incorrect password. Please try again.', 'error')
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'authenticated' not in session or not session['authenticated']:
        flash('Please log in to access the chat.', 'error')
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/delete', methods=['POST'])
def delete_message():
    """Delete a message by ID"""
    msg_id = request.json.get('id')
    global chat_messages
    chat_messages = [msg for msg in chat_messages if msg.get('id') != msg_id]
    emit('message_deleted', {'id': msg_id}, broadcast=True, namespace='/')
    return jsonify({'status': 'deleted'}), 200

@socketio.on('connect')
def handle_connect():
    if 'authenticated' not in session or not session['authenticated']:
        disconnect()
        return False
    print(f"Client connected: {request.sid}")
    for message in chat_messages[-50:]:
        emit('receive_message', message)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    username = session.get('username')
    if username and username in active_users:
        active_users.discard(username)
        emit('user_left', {'username': username}, broadcast=True)

@socketio.on('join_chat')
def handle_join(data):
    if 'authenticated' not in session or not session['authenticated']:
        disconnect()
        return
    username = data.get('username', '').strip()
    if not username:
        emit('error', {'message': 'Username is required'})
        return
    session['username'] = username
    active_users.add(username)
    global message_counter
    join_message = {
        'id': message_counter,
        'username': 'System',
        'message': f'{username} joined the chat',
        'timestamp': datetime.now().strftime('%H:%M'),
        'type': 'system'
    }
    message_counter += 1
    chat_messages.append(join_message)
    emit('receive_message', join_message, broadcast=True)
    emit('user_joined', {'username': username}, broadcast=True)
    print(f"📨 {username} joined the chat")

@socketio.on('send_message')
def handle_message(data):
    if 'authenticated' not in session or not session['authenticated']:
        disconnect()
        return
    username = data.get('username', '').strip()
    message = data.get('message', '').strip()
    if not username or not message:
        emit('error', {'message': 'Username and message are required'})
        return
    global message_counter
    message_data = {
        'id': message_counter,
        'username': username,
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M'),
        'type': 'user'
    }
    message_counter += 1
    chat_messages.append(message_data)
    if len(chat_messages) > 1000:
        chat_messages.pop(0)
    emit('receive_message', message_data, broadcast=True)
    print(f"📨 {username}: {message}")

@socketio.on('typing')
def handle_typing(data):
    if 'authenticated' not in session or not session['authenticated']:
        return
    username = data.get('username', '').strip()
    if username:
        emit('user_typing', {'username': username}, broadcast=True, include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    if 'authenticated' not in session or not session['authenticated']:
        return
    username = data.get('username', '').strip()
    if username:
        emit('user_stop_typing', {'username': username}, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
