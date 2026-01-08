// API endpoint - adjust this to match your Flask backend URL
const API_URL = 'http://127.0.0.1:5000/chat';

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const loadingIndicator = document.getElementById('loadingIndicator');

/**
 * Initialize the chat interface
 */
function init() {
    // Add event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-scroll to bottom on load
    scrollToBottom();
}

/**
 * Send a message to the chatbot
 */
async function sendMessage() {
    const message = userInput.value.trim();
    
    // Don't send empty messages
    if (!message) {
        return;
    }

    // Display user message
    addMessage(message, 'user');
    
    // Clear input
    userInput.value = '';
    
    // Disable input and show loading
    setLoading(true);
    
    try {
        // Send message to backend
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Display bot response
        addMessage(data.response, 'bot');
        
    } catch (error) {
        console.error('Error:', error);
        addMessage(
            'Sorry, I encountered an error. Please try again later or check if the backend server is running.',
            'bot'
        );
    } finally {
        // Hide loading and re-enable input
        setLoading(false);
    }
}

/**
 * Add a message to the chat interface
 * @param {string} text - The message text
 * @param {string} sender - 'user' or 'bot'
 */
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textParagraph = document.createElement('p');
    textParagraph.textContent = text;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = getCurrentTime();
    
    contentDiv.appendChild(textParagraph);
    contentDiv.appendChild(timestamp);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    scrollToBottom();
}

/**
 * Get current time in HH:MM format
 * @returns {string} Formatted time string
 */
function getCurrentTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show or hide loading indicator
 * @param {boolean} isLoading - Whether to show loading
 */
function setLoading(isLoading) {
    if (isLoading) {
        loadingIndicator.style.display = 'block';
        sendButton.disabled = true;
        userInput.disabled = true;
        scrollToBottom();
    } else {
        loadingIndicator.style.display = 'none';
        sendButton.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', init);

