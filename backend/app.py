from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import requests
import google.generativeai as genai

# ------------------ CONFIG ------------------
FAKESTORE_API = "https://fakestoreapi.com"

# ------------------ Initialize Flask ------------------
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# ------------------ Conversation state ------------------
conversation_state = {
    "last_intent": None
}

# ------------------ Mock Orders (NO database needed) ------------------
mock_orders = {
    "123": {"status": "Shipped", "delivery": "2 days", "items": ["T-Shirt", "Shoes"]},
    "456": {"status": "Processing", "delivery": "5 days", "items": ["Laptop"]},
    "789": {"status": "Delivered", "delivery": "Delivered on Jan 10", "items": ["Phone"]}
}

mock_refunds = {}

# ------------------ Helper Functions ------------------
def is_order_id(text):
    return text.isdigit() and len(text) >= 3

def detect_intent(text):
    t = text.lower()
    if any(w in t for w in ["hi", "hello", "hey"]):
        return "greeting"
    if any(w in t for w in ["order", "status", "delivery", "shipped", "delivered"]):
        return "order_status"
    if any(w in t for w in ["refund", "return", "cancel"]):
        return "refund"
    if any(w in t for w in ["product", "products", "price", "buy"]):
        return "product"
    return "general"

# ------------------ External API ------------------
def get_products():
    try:
        r = requests.get(f"{FAKESTORE_API}/products", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Product API error:", e)
        return None

def get_product_by_id(pid):
    try:
        r = requests.get(f"{FAKESTORE_API}/products/{pid}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Product ID API error:", e)
        return None

# ------------------ Gemini fallback ------------------
def generate_ai_response(user_message):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI service is not configured."

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"""
You are a customer support assistant.
Be helpful and clear.
User: {user_message}
"""
        )
        return response.text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return "I'm unable to answer that right now."

# ------------------ Chat Route ------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "Please enter a message."})

    # ---------- Product by ID ----------
    if user_message.lower().startswith("product"):
        parts = user_message.split()
        if len(parts) == 2 and parts[1].isdigit():
            product = get_product_by_id(parts[1])
            if product:
                return jsonify({
                    "response": (
                        f"🛍️ {product['title']}\n"
                        f"💰 Price: ₹{int(product['price'] * 80)}\n"
                        f"⭐ Rating: {product['rating']['rate']}\n"
                        f"📝 {product['description']}"
                    )
                })
            return jsonify({"response": "❌ Product not found."})

    # ---------- Multi-turn: Order ----------
    if conversation_state["last_intent"] == "order_status":
        if is_order_id(user_message):
            order = mock_orders.get(user_message)
            if order:
                conversation_state["last_intent"] = None
                return jsonify({
                    "response": (
                        f"📦 Order {user_message}\n"
                        f"Status: {order['status']}\n"
                        f"Delivery: {order['delivery']}\n"
                        f"Items: {', '.join(order['items'])}"
                    )
                })
            return jsonify({"response": "❌ Invalid order ID. Try again."})

    # ---------- Multi-turn: Refund ----------
    if conversation_state["last_intent"] == "refund":
        if is_order_id(user_message):
            if user_message in mock_orders:
                mock_refunds[user_message] = "Initiated"
                conversation_state["last_intent"] = None
                return jsonify({
                    "response": f"✅ Refund initiated for order {user_message}."
                })
            return jsonify({"response": "❌ Order not found."})

    # ---------- Intent detection ----------
    intent = detect_intent(user_message)
    conversation_state["last_intent"] = intent

    if intent == "greeting":
        response = "Hi 👋 How can I help you today?"

    elif intent == "order_status":
        response = "📦 Please provide your order ID."

    elif intent == "refund":
        response = "💸 Please provide your order ID to initiate a refund."

    elif intent == "product":
        products = get_products()
        if not products:
            response = "⚠️ Unable to fetch products right now."
        else:
            response = "🛍️ Available products:\n"
            for p in products[:5]:
                response += f"\nID {p['id']} – {p['title']} (₹{int(p['price'] * 80)})"
            response += "\n\nType: product <id>"

        conversation_state["last_intent"] = None

    else:
        conversation_state["last_intent"] = None
        response = generate_ai_response(user_message)

    return jsonify({
        "response": response,
        "timestamp": datetime.now().isoformat()
    })

# ------------------ Health ------------------
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# ------------------ Frontend ------------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# ------------------ Main ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

