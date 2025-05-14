// Chat System Core
class ChatSystem {
    constructor() {
        this.pendingDetails = [];
        this.missingFields = [];
        this.currentState = {};
        this.currentIntent = null;
        this.currentDetail = null;
        this.chatState = {};
        this.isCollecting = false;
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
        if (response.error) {
            this.appendMessage(`⚠️ Error: ${response.error}`, false);
            return;
        }

        if (response.missing_fields?.length > 0) {
            this.missingFields = response.missing_fields;
            this.currentState = response.current_state;
            this.currentIntent = response.intent;
            this.askNextField();
        }

        if (response.message) {
            this.appendMessage(response.message, false);
            this.updateAppointments();
        }
        }

        // Update askNextDetail and sendCollectedDetails methods
        askNextField() {
            if (this.missingFields.length > 0) {
                const nextField = this.missingFields[0];
                this.appendMessage(`Please provide your ${nextField.replace(/_/g, ' ')}:`, false);
            }
        }

            async sendCollectedDetails() {
                this.appendMessage("🔄 Finalizing your appointment...", false);
        
                try {
                    const intent = this.chatState.intent;
                    const action = `complete_${intent}`;
                    
                    this.appendMessage("🔄 Processing your request...", false);
                    
                    const response = await fetch('/ai-response', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action: action,
                            current_state: this.chatState
                        })
                    });
        
                    const result = await response.json();
                    
                    if (result.error) {
                        this.appendMessage(`⚠️ Error: ${result.error}`, false);
                    } else {
                        const successMessage = {
                            book: "✅ Appointment booked successfully!",
                            reschedule: "✅ Appointment rescheduled successfully!",
                            cancel: "✅ Appointment canceled successfully!"
                        }[intent];
                        
                        this.appendMessage(successMessage, false);
                        this.updateAppointments();
                    }
                } catch (error) {
                    this.appendMessage(`⚠️ Error: ${error.message}`, false);
                } finally {
                    this.resetCollectionState();
                }
            }

    resetCollectionState() {
        this.pendingDetails = [];
        this.currentDetail = null;
        this.chatState = {};
        this.isCollecting = false;

            }
            async handleUserResponse(message) {
                if (this.isCollecting && this.missingFields.length > 0) {
                    const currentField = this.missingFields.shift();
                    this.currentState[currentField] = message;
                    
                    // Update backend with collected field
                    const response = await this.fetchAIResponse(JSON.stringify({
                        action: 'update_field',
                        field: currentField,
                        value: message,
                        current_state: this.currentState
                    }));
                    
                    this.processAIResponse(response);
                }
            }
            async handleUserInput(message) {
                if (this.missingFields.length > 0) {
                    const currentField = this.missingFields.shift();
                    this.currentState[currentField] = message; // Send raw input
                    
                    // Check if more fields needed
                    if (this.missingFields.length === 0) {
                        // All fields collected - process immediately
                        const response = await this.fetchAIResponse(JSON.stringify({
                            message: "complete_action",
                            intent: this.currentIntent,
                            details: this.currentState
                        }));
                        this.processAIResponse(response);
                    } else {
                        this.askNextField();
                    }
                }
            }
        
            async finalizeBooking() {
                this.appendMessage("🔄 Finalizing your appointment...", false);
                const response = await this.fetchAIResponse(JSON.stringify({
                    action: 'complete_booking',
                    current_state: this.currentState
                }));
                this.processAIResponse(response);
            }
    
            async sendMessage() {
                const input = document.getElementById('userInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        this.appendMessage(message, true);

        if (this.missingFields.length > 0) {
            this.handleUserInput(message);
        } else {
            const response = await this.fetchAIResponse(message);
            this.processAIResponse(response);
        }
    
            }

            handleAIResponse(response) {
                if (response.error) {
                    this.appendMessage(`⚠️ Error: ${response.error}`, false);
                    return;
                }
        
                if (response.missing_field) {
                    this.appendMessage(response.message, false);
                    // Frontend will wait for next user input automatically
                } else if (response.appointment) {
                    this.appendMessage("✅ " + response.message, false);
                    this.updateAppointments();
                }        
            } 

    // Modify the fetchAIResponse method
        async fetchAIResponse(message) {
            try {
                console.log("🔹 Sending message to API:", message);
                const response = await fetch('/ai-response', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                console.log("🔹 API Response Status:", response.status);

                if (!response.ok) throw new Error('Failed to get AI response');
                return await response.json(); // Directly return the JSON response

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
            const response = await fetch('/api/appointments'); // Add 'const'
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