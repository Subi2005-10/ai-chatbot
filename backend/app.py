"""
AI-Powered Customer Support Chatbot - Backend API
Flask REST API for handling chat requests, NLP processing, and AI responses
"""

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
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if openai_api_key:
        try:
            import openai
            openai.api_key = openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful customer support assistant for an e-commerce store. Be friendly, concise, and helpful."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")
    
    user_lower = user_message.lower()
    if any(word in user_lower for word in ['order', 'purchase', 'bought']):
        if 'status' in user_lower or 'where' in user_lower:
            return "I'd be happy to help you check your order status. Please provide your order ID."
        return "I can help you with your order. Please provide your order ID."
    if any(word in user_lower for word in ['product', 'item', 'buy', 'price']):
        return "I can help you find information about our products. Please specify which product."
    if any(word in user_lower for word in ['problem', 'issue', 'wrong', 'broken', 'not working', 'complaint']):
        return "I'm sorry to hear you're experiencing an issue. Please provide details so I can assist."
    return "Thank you for your message. I understand you need assistance. I can connect you with a support agent if needed."

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
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        faq_response = match_faq(user_message)
        bot_response = faq_response if faq_response else generate_ai_response(user_message)
        save_chat_history(user_message, bot_response)
        return jsonify({'response': bot_response, 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'An error occurred', 'response': 'I encountered an error. Please try again.'}), 500

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
