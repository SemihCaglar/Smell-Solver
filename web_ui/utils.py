import time
import jwt
import requests
from pyngrok import ngrok
import config
import base64
import subprocess
import tempfile
import json
import os

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

    def get_compare_url(payload):
        """
        Generate a GitHub compare URL from the webhook payload.
        For "synchronize" events, it uses the 'before' and 'after' fields.
        For "opened" or "reopened" events, it uses the 'base' and 'head' fields
        within the pull_request object.
        """
        # Try to determine if it's a "synchronize" or "opened"/"reopened" payload
        repo_full_name = payload["repository"]["full_name"]
        base_sha = ""
        head_sha = ""
        
        # Check if payload has a "before" key (typically for "synchronize" events)
        if "before" in payload and "after" in payload:
            base_sha = payload["before"]
            head_sha = payload["after"]
        else:
            # For opened, reopened, and similar events, use pull_request object
            pr = payload.get("pull_request")
            if pr:
                # Some events might include "base" and "head" objects under the pull_request
                base_sha = pr["base"]["sha"]
                head_sha = pr["head"]["sha"]
        
        if repo_full_name and base_sha and head_sha:
            return f"https://api.github.com/repos/{repo_full_name}/compare/{base_sha}...{head_sha}"
        else:
            return None

    installation_id = str(payload["installation"]["id"])
    owner = str(payload["repository"]["owner"]["login"])
    repo = str(payload["repository"]["name"])
    pr_number = str(payload["number"])

    """Retrieve the list of changed files in a pull request."""
    token = get_installation_access_token(installation_id)
    if not token:
        return None

    url = get_compare_url(payload)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    #save response as json
    with open("payloads/response.json", "w") as f:
        json.dump(response.json(), f, indent=4)
    if response.status_code == 200:
        files = response.json().get("files", [])  # Extract the 'files' key from the response
        # only keep python and java files
        files = [file for file in files if file["filename"].endswith(('.java', '.py'))]
        add_content_to_files(token, files)
        return files
    else:
        print("Error retrieving changed files:", response.json())
        return None

def extract_comments(file):
    """
    Extracts comments from the given file content using the `nirjas` command.

    Args:
        file (dict): A dictionary containing file metadata, including its content.

    Returns:
        str: The output of the `nirjas` command, or None if an error occurs.
    """
    file_content = file.get("content")
    if not file_content:
        print(f"No content found for file: {file['filename']}")
        return None

    try:
        # Create a temporary file to store the content
        with tempfile.NamedTemporaryFile(mode="w+", suffix=f"_{os.path.basename(file['filename'])}") as temp_file:
            temp_file.write(file_content)
            temp_file.flush()  # Ensure content is written to disk

            # Run the `nirjas` command with the temporary file
            command = f"nirjas {temp_file.name}"
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"Command Output for {file['filename']}: {result.stdout}")
            parsed_output = json.loads(result.stdout)
            return parsed_output 
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing command for {file['filename']}: {e.stderr}")
        return None