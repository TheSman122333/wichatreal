from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, session
from flask_socketio import SocketIO
import os
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')



from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from flask_cors import CORS


from flask import send_from_directory

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename, mimetype={
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.mp3': 'audio/mpeg'
    }.get(filename.rsplit('.', 1)[-1].lower(), 'text/plain'))


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
# Update your SocketIO initialization
# Add to top of fil
# Update SocketIO initialization
socketio = SocketIO(app,
    cors_allowed_origins="*",
    async_mode='gevent',
    # Required fixes:
    transports=['websocket', 'polling'],
    allow_upgrades=True,
    ping_interval=25,
    ping_timeout=60,
    # For Render specifically:
    http_compression=True,
    engineio_logger=True  # Keep enabled for debugging
)

# Configure logging
if not os.path.exists('chat_logs'):
    os.makedirs('chat_logs')

logger = logging.getLogger('WIChat')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('chat_logs/chat.log', maxBytes=100000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# User tracking
connected_users = {}  # {username: sid}
room_users = defaultdict(set)  # {room: set_of_usernames}

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        if username in connected_users:
            return render_template('login.html', error="Username already taken")
        
        session['username'] = username
        logger.info(f"User logged in: {username}")
        return redirect(url_for('chat'))
    
    return render_template('login.html', app_name="WIChat")

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', 
                         username=session['username'],
                         rooms=['general'])

@app.route('/logout')
def logout():
    username = session.pop('username', None)
    if username in connected_users:
        del connected_users[username]
        emit('user_disconnected', {'username': username}, broadcast=True)
        logger.info(f"User logged out: {username}")
    return redirect(url_for('login'))

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        username = session['username']
        connected_users[username] = request.sid
        
        # Send current user list to new user
        emit('current_users', {'users': list(connected_users.keys())}, room=request.sid)
        
        # Notify others about new connection
        emit('user_connected', {'username': username}, broadcast=True, include_self=False)
        
        logger.info(f"User connected: {username} (Total: {len(connected_users)})")

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        username = session['username']
        if username in connected_users:
            # Leave all rooms
            for room in list(room_users.keys()):
                if username in room_users[room]:
                    room_users[room].remove(username)
                    emit('room_users_update', {
                        'room': room,
                        'users': list(room_users[room])
                    }, room=room)
            
            del connected_users[username]
            emit('user_disconnected', {'username': username}, broadcast=True)
            logger.info(f"User disconnected: {username}")

@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    username = session['username']
    
    join_room(room)
    room_users[room].add(username)
    
    emit('message', {
        'username': 'System',
        'message': f'{username} joined {room}',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'system': True
    }, room=room)
    
    emit('room_users_update', {
        'room': room,
        'users': list(room_users[room])
    }, room=room)
    
    logger.info(f"{username} joined room {room}")

@socketio.on('leave_room')
def handle_leave_room(data):
    room = data['room']
    username = session['username']
    
    leave_room(room)
    if username in room_users[room]:
        room_users[room].remove(username)
    
    emit('message', {
        'username': 'System',
        'message': f'{username} left {room}',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'system': True
    }, room=room)
    
    emit('room_users_update', {
        'room': room,
        'users': list(room_users[room])
    }, room=room)
    
    logger.info(f"{username} left room {room}")

@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    username = session['username']
    message = data['message']
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    message_data = {
        'username': username,
        'message': message,
        'timestamp': timestamp
    }
    
    emit('message', message_data, room=room)
    logger.info(f"Message in {room} from {username}: {message}")

@socketio.on('ping_user')
def handle_ping(data):
    target_user = data['username']
    if target_user in connected_users:
        emit('ping', {
            'from': session['username'],
            'message': data.get('message', 'You have been pinged!')
        }, room=connected_users[target_user])
        logger.info(f"Ping from {session['username']} to {target_user}")

@socketio.on('request_users')
def handle_request_users():
    if 'username' in session:
        emit('current_users', {'users': list(connected_users.keys())}, room=request.sid)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)


