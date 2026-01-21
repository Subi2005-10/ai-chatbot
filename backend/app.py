"""
AI-Powered Customer Support Chatbot - Backend API
Flask REST API for handling chat requests, NLP processing, and AI responses
"""
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import re
import os
from datetime import datetime
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Download required NLTK data (only needed once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# ------------------ Initialize Flask ------------------
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# ------------------ Frontend Serving ------------------
@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

# ------------------ Configuration ------------------
DATABASE = 'database.db'
FAQ_FILE = 'faq_data.json'

# ------------------ Database Initialization ------------------
def init_database():
    """Initialize SQLite database with tables for FAQs and chat history"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create FAQs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            keywords TEXT NOT NULL,
            response TEXT NOT NULL
        )
    ''')
    
    # Create chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Load FAQs from JSON file into database
    if os.path.exists(FAQ_FILE):
        with open(FAQ_FILE, 'r', encoding='utf-8') as f:
            faq_data = json.load(f)
            for faq in faq_data.get('faqs', []):
                cursor.execute('SELECT id FROM faqs WHERE id = ?', (faq['id'],))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO faqs (id, question, keywords, response)
                        VALUES (?, ?, ?, ?)
                    ''', (faq['id'], faq['question'], json.dumps(faq['keywords']), faq['response']))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'response': 'Please enter a message.'})

    # ✅ STEP 1: If bot is waiting for order ID
    if conversation_state["last_intent"] == "order_status" and is_order_id(user_message):
        order_id = user_message

        mock_orders = {
            '123': {'status': 'Shipped', 'delivery': '2 days'},
            '456': {'status': 'Processing', 'delivery': '5 days'},
            '789': {'status': 'Delivered', 'delivery': 'Delivered on Jan 10'}
        }

        order = mock_orders.get(order_id)

        if order:
            bot_response = (
                f"📦 Order {order_id} Status: {order['status']}\n"
                f"Estimated Delivery: {order['delivery']}"
            )
        else:
            bot_response = f"❌ No order found with ID {order_id}. Please check and try again."

        conversation_state["last_intent"] = None
        return jsonify({'response': bot_response})

    # ✅ STEP 2: Detect intent
    intent = detect_intent(user_message)
    conversation_state["last_intent"] = intent

    if intent == "greeting":
        bot_response = "Hi 👋 How can I help you today?"

    elif intent == "order_status":
        bot_response = "Sure 📦 Please provide your order ID."

    elif intent == "refund":
        bot_response = "I can help with refunds. Please share your order ID."

    elif intent == "product":
        bot_response = "Which product would you like to know about?"

    else:
        conversation_state["last_intent"] = None
        bot_response = generate_ai_response(user_message)

    save_chat_history(user_message, bot_response)
    return jsonify({'response': bot_response})


# ------------------ NLP Utilities ------------------
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    try:
        tokens = word_tokenize(text)
    except:
        tokens = text.split()
    try:
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token not in stop_words]
    except:
        pass
    return tokens

def match_faq(user_message):
    user_tokens = preprocess_text(user_message)
    user_text = ' '.join(user_tokens)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, question, keywords, response FROM faqs')
    faqs = cursor.fetchall()
    conn.close()
    
    best_match = None
    best_score = 0
    
    for faq_id, question, keywords_json, response in faqs:
        try:
            keywords = json.loads(keywords_json)
        except:
            keywords = []
        score = 0
        for keyword in keywords:
            if keyword.lower() in user_text or keyword.lower() in user_message.lower():
                score += 1
        question_tokens = preprocess_text(question)
        for token in question_tokens:
            if token in user_tokens:
                score += 1
        if score > best_score:
            best_score = score
            best_match = response
    if best_score >= 2:
        return best_match
    return None

def generate_ai_response(user_message):
    api_key = os.environ.get("AIzaSyCyI9FGoFaXwWFKN6LHhXxhOkt4rjP1dNM")

    if not api_key:
        return "Gemini API key not found."

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"You are a helpful customer support assistant for an e-commerce store.\n"
            f"Be friendly, concise, and helpful.\n\n"
            f"User: {user_message}"
        )
        return response.text
    except Exception as e:
        print("Gemini API error:", e)
        return "Sorry, I'm having trouble responding right now."

def save_chat_history(user_message, bot_response):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_history (user_message, bot_response) VALUES (?, ?)', (user_message, bot_response))
    conn.commit()
    conn.close()

# ------------------ API Routes ------------------
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        print("USER MESSAGE:", user_message)   # 👈 ADD THIS LINE

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        faq_response = match_faq(user_message)
        bot_response = faq_response if faq_response else generate_ai_response(user_message)
        save_chat_history(user_message, bot_response)
        return jsonify({'response': bot_response, 'timestamp': datetime.now().isoformat()}), 200

@app.route('/order_status', methods=['GET'])
def order_status():
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'error': 'order_id parameter is required'}), 400
    mock_orders = {
        '123': {'order_id': '123', 'status': 'Shipped', 'tracking_number': 'TRACK123456', 'estimated_delivery': '2024-01-15', 'items': ['Product A', 'Product B']},
        '456': {'order_id': '456', 'status': 'Processing', 'tracking_number': None, 'estimated_delivery': '2024-01-20', 'items': ['Product C']},
        '789': {'order_id': '789', 'status': 'Delivered', 'tracking_number': 'TRACK789012', 'delivery_date': '2024-01-10', 'items': ['Product D']}
    }
    order = mock_orders.get(order_id)
    if order:
        return jsonify(order), 200
    else:
        return jsonify({'error': 'Order not found', 'message': f'No order found with ID: {order_id}'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

# ------------------ Main ------------------
if __name__ == '__main__':
    init_database()
    print("Starting AI Customer Support Chatbot Backend...")
    print("Server running on http://0.0.0.0:3000")
    app.run(host='0.0.0.0', port=3000, debug=True)
