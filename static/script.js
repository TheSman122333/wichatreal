document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
          transports: ['websocket', 'polling'],
          reconnection: true,
          reconnectionAttempts: Infinity,
          reconnectionDelay: 1000,
          path: '/socket.io'  // Explicit path
        });
    let currentRoom = 'general';
    const currentUser = document.querySelector('.user-info h3').textContent;
    
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const currentRoomDisplay = document.getElementById('current-room');
    const roomUsersDisplay = document.getElementById('room-users');
    const userList = document.getElementById('user-list');
    const userCount = document.getElementById('user-count');
    const pingSound = document.getElementById('ping-sound');
    
    // Initialize
    joinRoom(currentRoom);
    requestNotificationPermission();
    
    // Socket event handlers
    socket.on('current_users', function(data) {
        updateUserList(data.users);
    });
    
    socket.on('user_connected', function(data) {
        addUserToList(data.username);
    });
    
    socket.on('user_disconnected', function(data) {
        removeUserFromList(data.username);
    });
    
    socket.on('room_users_update', function(data) {
        if (data.room === currentRoom) {
            updateRoomUsers(data.users);
        }
    });
    
    socket.on('message', function(data) {
        displayMessage(data);
    });
    
    socket.on('ping', function(data) {
        playPingSound();
        showNotification(`Ping from ${data.from}`, data.message);
        showAlert(`Ping from ${data.from}`, data.message);
    });
    
    // Room management
    document.querySelectorAll('.room-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const newRoom = this.getAttribute('data-room');
            if (newRoom !== currentRoom) {
                leaveRoom(currentRoom);
                currentRoom = newRoom;
                currentRoomDisplay.textContent = newRoom.charAt(0).toUpperCase() + newRoom.slice(1);
                joinRoom(newRoom);
            }
        });
    });
    
    function joinRoom(room) {
        socket.emit('join_room', { room: room });
        messagesContainer.innerHTML = '';
    }
    
    function leaveRoom(room) {
        socket.emit('leave_room', { room: room });
    }
    
    // User list management
    function updateUserList(users) {
        userList.innerHTML = '';
        userCount.textContent = `(${users.length})`;
        users.forEach(user => addUserToList(user));
    }
    
    function addUserToList(username) {
        if (!document.querySelector(`#user-list [data-user="${username}"]`)) {
            const li = document.createElement('li');
            li.dataset.user = username;
            li.innerHTML = `
                ${username} 
                <span class="status online">online</span>
                ${username !== currentUser ? `<button class="ping-btn" data-user="${username}">Ping</button>` : ''}
            `;
            userList.appendChild(li);
            
            const pingBtn = li.querySelector('.ping-btn');
            if (pingBtn) {
                pingBtn.addEventListener('click', function() {
                    const targetUser = this.getAttribute('data-user');
                    const message = prompt(`Ping ${targetUser}:`, 'Hello!');
                    if (message) {
                        socket.emit('ping_user', {
                            username: targetUser,
                            message: message
                        });
                    }
                });
            }
        }
    }
    
    function removeUserFromList(username) {
        const userElement = document.querySelector(`#user-list [data-user="${username}"]`);
        if (userElement) {
            userElement.remove();
            userCount.textContent = `(${userList.children.length})`;
        }
    }
    
    function updateRoomUsers(users) {
        roomUsersDisplay.textContent = `${users.length} users: ${users.join(', ')}`;
    }
    
    // Message handling
    function displayMessage(data) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message';
        if (data.system) {
            messageElement.classList.add('system-message');
        }
        
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="message-username">${data.username}</span>
                <span class="message-timestamp">${data.timestamp}</span>
            </div>
            <div class="message-content">${data.message}</div>
        `;
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            socket.emit('send_message', {
                room: currentRoom,
                message: message
            });
            messageInput.value = '';
        }
    }
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Notification helpers
    function requestNotificationPermission() {
        if (Notification.permission !== 'granted') {
            Notification.requestPermission();
        }
    }
    
    function playPingSound() {
        pingSound.currentTime = 0;
        pingSound.play().catch(e => console.log("Audio play failed:", e));
    }
    
    function showNotification(title, message) {
        if (Notification.permission === 'granted') {
            new Notification(title, { body: message });
        }
    }
    
    function showAlert(title, message) {
        const alert = document.createElement('div');
        alert.className = 'ping-alert';
        alert.innerHTML = `<strong>${title}</strong><br>${message}`;
        document.body.appendChild(alert);
        
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.5s forwards';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    }
    
    // Request initial user list
    socket.emit('request_users');
});
