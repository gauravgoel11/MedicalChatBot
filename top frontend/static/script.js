// Chat System Core
class ChatSystem {
    constructor() {
        this.pendingDetails = [];
        this.currentDetail = null;
        this.chatState = { action: null, data: {} };
        this.isTyping = false;
        this.initializeChat();
    }

    initializeChat() {
        this.restoreChatHistory();
        this.setupEventListeners();
        this.updateAppointments();
        setInterval(() => this.updateAppointments(), 3000);
    }

    setupEventListeners() {
        document.getElementById('userInput').addEventListener('input', () => {
            this.toggleTypingIndicator(true);
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => this.toggleTypingIndicator(false), 1000);
        });
    }

    toggleTypingIndicator(show) {
        const indicator = document.getElementById('typingIndicator');
        indicator.style.opacity = show ? '1' : '0';
    }

    async processAIResponse(response) {
        console.log("🔹 Processing AI Response:", response);
        if (response.error) {
            this.appendMessage(`⚠️ Error: ${response.error}`, false);
            return;
          }
      
          if (response.message) {
            this.appendMessage(response.message, false);
            this.saveToHistory(response.message, false);
          }
      
          if (response.new_state?.missing_details) {
            this.pendingDetails = [...response.new_state.missing_details];
            this.chatState = response.new_state;
            this.askNextDetail();
          }
        }

    askNextDetail() {
          if (this.pendingDetails.length > 0) {
            this.currentDetail = this.pendingDetails.shift();
            const promptMessage = `Please provide your ${this.currentDetail}:`;
            this.appendMessage(promptMessage, false);
            this.saveToHistory(promptMessage, false);
          } else {
            this.currentDetail = null;
            this.sendCollectedDetails();
          }
        }
    async sendCollectedDetails() {
            this.appendMessage("🔄 Processing your request...", false);
            const updatedResponse = await this.fetchAIResponse(JSON.stringify(this.chatState.data));
            await this.processAIResponse(updatedResponse);
        }
    
    async sendMessage() {
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        this.appendMessage(message, true);
        this.saveToHistory(message, true);

        // Handle detail collection state
        if (this.chatState.action === 'collect_details') {
            const currentDetail = this.chatState.missingDetails[this.chatState.currentDetailIndex];
            this.chatState.data[currentDetail] = message;
            this.chatState.currentDetailIndex++;

            if (this.chatState.currentDetailIndex >= this.chatState.missingDetails.length) {
                // All details collected, send to backend
                try {
                    const response = await this.fetchAIResponse(JSON.stringify({
                        intent: 'book',
                        ...this.chatState.data
                    }));
                    await this.processAIResponse(response);
                    this.chatState = { action: null, data: {} }; // Reset state
                } catch (error) {
                    this.appendMessage(`⚠️ Error: ${error.message}`, false);
                }
            } else {
                // Ask next detail
                const nextDetail = this.chatState.missingDetails[this.chatState.currentDetailIndex];
                this.appendMessage(`Please provide your ${nextDetail}:`, false);
            }
            return;
        }

        try {
            const response = await this.fetchAIResponse(message);
            await this.processAIResponse(response);
        } catch (error) {
            this.appendMessage(`⚠️ Error: ${error.message}`, false);
        }
    }

    async fetchAIResponse(message) {
    try {
        console.log("🔹 Sending message to API:", message);  // ✅ Debug Log
        const response = await fetch('http://127.0.0.1:5000/ai-response', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        console.log("🔹 API Response Status:", response.status);  // ✅ Debug Log

        if (!response.ok) throw new Error('Failed to get AI response');

        const jsonResponse = await response.json();
        console.log("🔹 AI Response:", jsonResponse);  // ✅ Debug Log

        this.updateChatUI(jsonResponse.chat_history);  // ✅ Display Full Chat
        return jsonResponse;
    } catch (error) {
        console.error("Error:", error);
        return { error: "Unable to connect to chatbot API" };
    }
}

    appendMessage(content, isUser) {
        const messagesDiv = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas ${isUser ? 'fa-user' : 'fa-robot'}"></i>
            </div>
            <div class="message-content">
                ${!isUser ? `<strong>MedCare Assistant</strong><br>` : ''}
                ${this.formatMessageContent(content)}
            </div>
        `;

        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    formatMessageContent(content) {
        return content.replace(/\n/g, '<br>');
    }

    saveToHistory(content, isUser) {
        const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        history.push({ content, isUser, timestamp: new Date().toISOString() });
        localStorage.setItem('chatHistory', JSON.stringify(history.slice(-50)));
    }

    restoreChatHistory() {
        // Clear previous chat history on reload
        localStorage.removeItem('chatHistory');  
    
        // Fetch and display recent appointments (keeps them unaffected)
        this.updateAppointments();
    }
    

    // Appointment System
    async updateAppointments() {
        try {
            const response = await fetch('/api/appointments');
            const data = await response.json();
            this.renderAppointments(data.appointments);
        } catch (error) {
            console.error('Error updating appointments:', error);
        }
    }

    renderAppointments(appointments) {
        const container = document.getElementById('appointments-container');
        const lastFour = appointments.slice(-4).reverse();
        
        container.innerHTML = lastFour.map(app => `
            <div class="appointment-card">
                <h4>${app.patientName}</h4>
                <p><i class="fas fa-calendar-day"></i> ${app.date} ${app.time}</p>
                <p><i class="fas fa-user-md"></i> ${app.doctorName}</p>
                <p class="status" style="color: ${app.status === 'Cancelled' ? 'var(--danger-color)' : 'var(--success-color)'}">
                    <i class="fas fa-circle"></i> ${app.status}
                </p>
            </div>
        `).join('');
    }

    handleEnterKey(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    insertQuickAction(action) {
        const input = document.getElementById('userInput');
        input.value = action;
        input.focus();
    }

    // Manual Appointment Booking
    async bookManualAppointment() {
        const formData = {
            name: document.getElementById('name').value,
            age: document.getElementById('age').value,
            gender: document.getElementById('gender').value,
            contact_number: document.getElementById('contact').value,
            email: document.getElementById('email').value,
            medical_history: document.getElementById('department').value,
            appointment_date: document.getElementById('date').value,
            appointment_time: document.getElementById('time').value
        };

        try {
            const response = await fetch('/api/book-appointment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            if (data.error) {
                this.appendMessage(`⚠️ Error: ${data.error}`, false);
            } else {
                this.appendMessage("✅ Appointment booked successfully!", false);
                this.updateAppointments();
                this.toggleBookingForm();
            }
        } catch (error) {
            this.appendMessage(`⚠️ Error: ${error.message}`, false);
        }
    }

    toggleBookingForm() {
        const form = document.getElementById('bookingForm');
        form.classList.toggle('visible');
        form.setAttribute('aria-hidden', !form.classList.contains('visible'));
    }
}

// Initialize Chat System
const chatSystem = new ChatSystem();

// Global Functions for Event Listeners
function handleEnterKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        chatSystem.sendMessage();
    }
}

function insertQuickAction(action) {
    chatSystem.insertQuickAction(action);
}

function toggleBookingForm() {
    document.querySelector('.booking-form').classList.toggle('active');
    chatSystem.toggleBookingForm();
}

document.getElementById('book-appointment-btn').addEventListener('click', toggleBookingForm);


function bookManualAppointment() {
    chatSystem.bookManualAppointment();
}