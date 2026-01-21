from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import google.generativeai as genai

# ------------------ Initialize Flask ------------------
# Point static_folder to frontend relative to this file
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# ------------------ Conversation state ------------------
conversation_state = {
    "last_intent": None,       # Tracks current intent: 'order_status', 'refund', 'product', etc.
    "pending_order_id": None   # Tracks order ID if needed
}

# ------------------ Mock Data ------------------
mock_orders = {
    '123': {'status': 'Shipped', 'delivery': '2 days', 'items': ['Product A', 'Product B']},
    '456': {'status': 'Processing', 'delivery': '5 days', 'items': ['Product C']},
    '789': {'status': 'Delivered', 'delivery': 'Delivered on Jan 10', 'items': ['Product D']}
}

mock_refunds = {}  # In-memory refund tracking
mock_products = {
    'laptop': '💻 Laptop – High-performance, ₹65,000, 16GB RAM, 512GB SSD',
    'phone': '📱 5G Smartphone – ₹25,000, 128GB storage, 6GB RAM'
}

# ------------------ Helper Functions ------------------
def is_order_id(message):
    """Check if the message is a valid order ID (digits)."""
    return message.isdigit() and len(message) >= 3

def detect_intent(message):
    """Basic intent detection using keywords."""
    msg = message.lower()
    if any(word in msg for word in ["hi", "hello", "hey"]):
        return "greeting"
    if any(word in msg for word in ["order", "delivery", "status"]):
        return "order_status"
    if any(word in msg for word in ["refund", "return", "money back"]):
        return "refund"
    if any(word in msg for word in ["product", "price", "buy"]):
        return "product"
    return "general"

def generate_ai_response(user_message):
    """Fallback AI response using Gemini Pro."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI service is not configured."

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"""
You are a professional customer support assistant.
Respond naturally, helpfully, and concisely.
Do NOT over-apologize.
Ask follow-up questions if needed.
User: {user_message}
"""
        )
        return response.text if response and response.text else "I'm here to help! Could you rephrase?"
    except Exception as e:
        print("Gemini error:", e)
        return "I'm having trouble answering that right now."

# ------------------ API Routes ------------------

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'response': 'Please enter a message.'})

    # STEP 1: Multi-turn: if waiting for order ID
    if conversation_state["last_intent"] == "order_status" and is_order_id(user_message):
        order_id = user_message
        conversation_state["pending_order_id"] = order_id

        order = mock_orders.get(order_id)
        if order:
            bot_response = (
                f"📦 Order {order_id} Status: {order['status']}\n"
                f"Estimated Delivery: {order['delivery']}\n"
                f"Items: {', '.join(order['items'])}"
            )
        else:
            bot_response = f"❌ No order found with ID {order_id}. Please type a valid order ID."
            conversation_state["last_intent"] = "order_status"  # still waiting

        if order:
            conversation_state["last_intent"] = None
            conversation_state["pending_order_id"] = None

        return jsonify({'response': bot_response})

    # STEP 2: Multi-turn: if waiting for refund order ID
    if conversation_state["last_intent"] == "refund" and is_order_id(user_message):
        order_id = user_message
        order = mock_orders.get(order_id)
        if order:
            mock_refunds[order_id] = "Pending"
            bot_response = f"✅ Refund for order {order_id} has been initiated. You will receive confirmation soon."
        else:
            bot_response = f"❌ No order found with ID {order_id}. Please type a valid order ID."
            conversation_state["last_intent"] = "refund"
            return jsonify({'response': bot_response})

        conversation_state["last_intent"] = None
        return jsonify({'response': bot_response})

    # STEP 3: Detect intent
    intent = detect_intent(user_message)
    conversation_state["last_intent"] = intent

    if intent == "greeting":
        bot_response = "Hi 👋 How can I help you today?"

    elif intent == "order_status":
        bot_response = "Sure 📦 Please provide your order ID."

    elif intent == "refund":
        bot_response = "I can help with refunds. Please provide your order ID."

    elif intent == "product":
        product_key = user_message.lower()
        product_info = mock_products.get(product_key)
        if product_info:
            bot_response = product_info
        else:
            bot_response = "Which product would you like to know about? We have Laptop and Phone."
        conversation_state["last_intent"] = None

    else:
        conversation_state["last_intent"] = None
        bot_response = generate_ai_response(user_message)

    return jsonify({'response': bot_response, 'timestamp': datetime.now().isoformat()})

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Frontend serving
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# ------------------ Main ------------------
if __name__ == '__main__':
    print("Starting AI Customer Support Chatbot Backend...")
    port = int(os.environ.get("PORT", 3000))
    print(f"Server running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
