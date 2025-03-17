import time
import jwt
import requests
from pyngrok import ngrok
import config

def start_ngrok():
    """Start an ngrok tunnel with a reserved subdomain using pyngrok."""
    ngrok.set_auth_token(config.NGROK_TOKEN)
    if not ngrok.get_tunnels():
        public_url = ngrok.connect(config.NGROK_PORT, "http", subdomain=config.NGROK_SUBDOMAIN).public_url
        print(f"✅ ngrok tunnel started: {public_url}")
    return ngrok.get_tunnels()[0].public_url

def get_jwt():
    """Generates a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10 minutes expiration
        "iss": config.GITHUB_APP_ID
    }
    token = jwt.encode(payload, config.GITHUB_PRIVATE_KEY, algorithm="RS256")
    return token

def get_installation_access_token(installation_id):
    """Obtains an installation access token using the installation ID."""
    jwt_token = get_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        token = response.json()["token"]
        return token
    else:
        print("Error obtaining installation token:", response.json())
        return None
