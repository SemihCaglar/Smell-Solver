import time
import jwt
import requests
from pyngrok import ngrok
import config
import base64

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

def add_content_to_files(token, changed_files):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    for file in changed_files:
        contents_url = file.get("contents_url")
        if contents_url:
            response = requests.get(contents_url, headers=headers)
            if response.status_code == 200:
                file_content = response.json().get("content")
                decoded_content = base64.b64decode(file_content).decode('utf-8') if file_content else None
                file["content"] = decoded_content
                file.pop("patch", None)
            else:
                print(f"Failed to fetch content for {file['filename']}: {response.status_code}")
                file["content"] = None
    

def get_changed_files(payload):

    installation_id = str(payload["installation"]["id"])
    owner = str(payload["repository"]["owner"]["login"])
    repo = str(payload["repository"]["name"])
    pr_number = str(payload["number"])

    """Retrieve the list of changed files in a pull request."""
    token = get_installation_access_token(installation_id)
    if not token:
        return None

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        files = response.json()
        # only keep python and java files
        files = [file for file in files if file["filename"].endswith(('.java', '.py'))]
        add_content_to_files(token, files)
        return files
    else:
        print("Error retrieving changed files:", response.json())
        return None