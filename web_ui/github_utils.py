import time
import requests
import base64
import json
import config
import jwt

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
            else:
                print(f"Failed to fetch content for {file['filename']}: {response.status_code}")
                file["content"] = None
   
def get_base_and_head_sha(payload):
    """
    Extracts the base and head SHA from the payload.
    For "synchronize" events, it uses the 'before' and 'after' fields.
    For "opened" or "reopened" events, it uses the 'base' and 'head' fields
    within the pull_request object.
    """
    if "before" in payload and "after" in payload:
        return payload["before"], payload["after"]
    else:
        pr = payload.get("pull_request")
        if pr:
            return pr["base"]["sha"], pr["head"]["sha"]
    return None, None
    
def get_changed_files(payload):

    def get_compare_url(payload):
        """
        Generate a GitHub compare URL from the webhook payload.
        For "synchronize" events, it uses the 'before' and 'after' fields.
        For "opened" or "reopened" events, it uses the 'base' and 'head' fields
        within the pull_request object.
        """
        # Try to determine if it's a "synchronize" or "opened"/"reopened" payload
        base_sha, head_sha = get_base_and_head_sha(payload)
        repo_full_name = payload["repository"]["full_name"]
        
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
    
def post_multiline_comment(url, token, path, start_line, end_line, head_sha, base_sha, comment_body, side="RIGHT"):
    """
    Post a multiline review comment (or suggestion) to a PR.

    side: "RIGHT" (new code) or "LEFT" (base)
    """
    if start_line == end_line:
        payload = {
            "commit_id": head_sha,
            "path": path,
            "body": comment_body,
            "line": int(start_line),
            "side": side,
        }
    else:
        # TODO learn about right and left
        payload = {
            "commit_id": head_sha,
            "path": path,
            "body": comment_body,
            "start_line": int(start_line),
            "start_side": side,
            "line": int(end_line),
            "side": side,        # must match start_side
        }
    print(json.dumps(payload, indent=4))
    r = requests.post(
        url,
        headers={
            "Authorization": f"token {token}",
            # "Accept": "application/vnd.github+json"
            "Accept": "application/vnd.github.comfort-fade-preview+json"  # needed for multi-line
        },
        json=payload
    )
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        print("GitHub returned 422 with JSON:\n", json.dumps(r.json(), indent=2))
        raise
    return r.json()        # the created comment object

def post_suggestions_to_github(payload, path, comment_entry):
    # TODO check these explanations
    short_explanations = {
        "misleading"        : "Comment does not correctly reflect what the code does.",
        "obvious"           : "Redundant comment simply restates the code.",
        "commented out code": "Dead code left in comments; should be removed.",
        "irrelevant"        : "Comment is unrelated to explaining the code.",
        "task"              : "TODO/FIXME note without actionable detail.",
        "too much info"     : "Overly verbose comment that hurts readability.",
        "beautification"    : "Decorative / section‑divider comment with no value.",
        "nonlocal info"     : "Comment refers to code located elsewhere.",
        "vague"             : "Comment is unclear or lacks meaningful detail.",
        "not a smell"       : "Comment is clear and appropriate.",
    }
    smell_label = comment_entry["smell_label"]
    explanation = short_explanations.get(smell_label.lower(), "Comment smell detected.")
    new_content = comment_entry["new_comment_block"]
    comment_body = f"""**{smell_label} smell** : {explanation}\n```suggestion\n{new_content}\n```"""
    
    installation_id = payload["installation"]["id"]
    token = get_installation_access_token(installation_id)
    base_sha, head_sha = get_base_and_head_sha(payload)
    
    return post_multiline_comment(
        url = payload["pull_request"]["review_comments_url"], #        "review_comments_url": "https://api.github.com/repos/SemihCaglar/new-repo/pulls/13/comments",
        token = token,
        path = path,
        start_line = comment_entry["computed_start_line"],
        end_line = comment_entry["computed_end_line"],
        head_sha = head_sha,
        base_sha = base_sha,
        comment_body = comment_body,
    )