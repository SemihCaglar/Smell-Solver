import json
import hmac
import hashlib
import requests
import config
from flask import Flask, request, jsonify, abort
from github import Github
from pyngrok import ngrok

# Configuration
REPO_NAME = config.REPO_NAME  # Replace with your GitHub repo
WEBHOOK_SECRET = config.WEBHOOK_SECRET  # Secure webhook secret
PORT = 5000  # Flask server port

# Initialize Flask
app = Flask(__name__)

# Function to start Ngrok only once
def start_ngrok():
    ngrok.set_auth_token(config.NGROK_TOKEN)
    if not ngrok.get_tunnels():
        print("Starting Ngrok...")
        http_tunnel = ngrok.connect(PORT, "http")
        return http_tunnel.public_url
    return ngrok.get_tunnels()[0].public_url

# Create or Update Webhook
def setup_webhook(ngrok_url):
    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # Delete all existing webhooks
    for hook in repo.get_hooks():
        print(f"🗑️ Deleting old webhook: {hook.config['url']}")
        hook.delete()

    # Add new webhook
    webhook_data = {
        "name": "web",
        "active": True,
        "events": ["push"],  # Trigger on push (new commits)
        "config": {
            "url": f"{ngrok_url}/webhook",
            "content_type": "json",
            "secret": WEBHOOK_SECRET,
            "insecure_ssl": "0"
        }
    }

    repo.create_hook(**webhook_data)
    print(f"✅ Webhook created: {webhook_data['config']['url']}")

# Flask route to handle webhook events
@app.route("/webhook", methods=["POST"])
def github_webhook():
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        abort(400, 'Missing X-Hub-Signature-256')

    payload = request.data
    if not payload:
        abort(400, 'Empty payload')

    def verify_signature(payload, signature):
        mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
        expected_signature = f"sha256={mac.hexdigest()}"
        return hmac.compare_digest(expected_signature, signature)

    if not verify_signature(payload, signature):
        abort(400, 'Invalid signature')

    payload_json = request.json

    # Save the payload to payload.json
    with open('payload.json', 'w') as f:
        json.dump(payload_json, f, indent=4)

    return handle_webhook(payload_json)

def handle_webhook(payload_json):
    if "commits" in payload_json:
        commit_messages = [commit["message"] for commit in payload_json["commits"]]
        print(f"📝 New commits pushed: {commit_messages}")
        return jsonify({"message": "Received commits", "commits": commit_messages}), 200
    elif payload_json.get("zen"):
        print("🔔 Ping event received")
        return jsonify({"message": "Ping event received"}), 200
    return jsonify({"message": "No commits found"}), 200

# Run Flask server only in the main process
if __name__ == "__main__":
    ngrok_url = start_ngrok()  # Start Ngrok only once
    print(f"Ngrok Tunnel Created: {ngrok_url}")

    setup_webhook(ngrok_url)  # Set up GitHub webhook

    app.run(port=PORT)