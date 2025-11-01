from flask import Flask, request, jsonify
import asyncio
import threading
from bot import telegram_bot
import os

app = Flask(__name__)

# Initialize Telegram bot in a separate thread
def start_bot():
    asyncio.run(telegram_bot())

@app.route('/')
def home():
    return "Free Fire Top-Up Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram"""
    update = request.get_json()
    # Process Telegram updates here
    return jsonify({"status": "success"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "freefire-topup-bot"})

if __name__ == '__main__':
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
