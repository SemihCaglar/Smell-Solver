import requests
import json

# Replace these with your own configuration.
GITHUB_TOKEN = "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"
OWNER = "SemihCaglar"
REPO = "new-repo"
BASE_BRANCH = "master"
NEW_BRANCH = "feature-branch"

# Define six dummy files. You can adjust the file paths as needed.
FILES = [
    {"path": "file1.txt", "content": "// Content for file 1."},
    {"path": "folder1/file2.java", "content": "// Content for file 2."},
    {"path": "folder1/file3.java", "content": "// Content for file 3."},
    {"path": "folder2/file4.java", "content": "// Content for file 4."},
    {"path": "folder3/subfolder/file5.java", "content": "// Content for file 5."},
    {"path": "file6.java", "content": "// Content for file 6."}
]

# GitHub API base URLs.
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"
REFS_URL = f"{BASE_URL}/git/refs"
BLOBS_URL = f"{BASE_URL}/git/blobs"
TREES_URL = f"{BASE_URL}/git/trees"
COMMITS_URL = f"{BASE_URL}/git/commits"
PR_URL = f"{BASE_URL}/pulls"
BRANCH_URL = f"{REFS_URL}/heads/{NEW_BRANCH}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_latest_commit_sha(branch):
    url = f"{REFS_URL}/heads/{branch}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to get latest commit: {response.json()}")
    return response.json()["object"]["sha"]

def branch_exists(branch):
    url = f"{REFS_URL}/heads/{branch}"
    response = requests.get(url, headers=HEADERS)
    return response.status_code == 200

def create_branch(new_branch, sha):
    payload = {
        "ref": f"refs/heads/{new_branch}",
        "sha": sha
    }
    response = requests.post(REFS_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create branch: {response.json()}")
    print(f"✅ Branch '{new_branch}' created.")

def create_blob(content):
    payload = {
        "content": content,
        "encoding": "utf-8"
    }
    response = requests.post(BLOBS_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create blob: {response.json()}")
    return response.json()["sha"]

def create_tree(base_tree_sha, blobs):
    # blobs: list of dicts with keys: "path", "mode", "type", "sha"
    payload = {
        "base_tree": base_tree_sha,
        "tree": blobs
    }
    response = requests.post(TREES_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create tree: {response.json()}")
    return response.json()["sha"]

def create_commit(message, tree_sha, parent_sha):
    payload = {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha]
    }
    response = requests.post(COMMITS_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create commit: {response.json()}")
    return response.json()["sha"]

def update_branch(branch, new_commit_sha):
    url = f"{REFS_URL}/heads/{branch}"
    payload = {
        "sha": new_commit_sha,
        "force": True
    }
    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to update branch: {response.json()}")
    print(f"✅ Branch '{branch}' updated with new commit.")

def create_pull_request(title, body, head, base):
    payload = {
        "title": title,
        "body": body,
        "head": head,  # source branch
        "base": base   # target branch
    }
    response = requests.post(PR_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create PR: {response.json()}")
    pr_info = response.json()
    print(f"✅ Pull Request Created: {pr_info['html_url']}")
    return pr_info

def main():
    # Step 1: Get the latest commit SHA from the base branch.
    latest_commit_sha = get_latest_commit_sha(BASE_BRANCH)
    print(f"Latest commit SHA from {BASE_BRANCH}: {latest_commit_sha}")

    # Step 2: If the new branch doesn't exist, create it.
    if branch_exists(NEW_BRANCH):
        print(f"🔄 Branch '{NEW_BRANCH}' already exists. Using the existing branch.")
    else:
        create_branch(NEW_BRANCH, latest_commit_sha)

    # Step 3: For each file, create a blob and prepare a new tree entry.
    tree_entries = []
    for file in FILES:
        blob_sha = create_blob(file["content"])
        tree_entries.append({
            "path": file["path"],
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha
        })
        print(f"Created blob for {file['path']}")

    # Step 4: Get the tree SHA of the latest commit.
    commit_details = requests.get(f"{BASE_URL}/git/commits/{latest_commit_sha}", headers=HEADERS)
    if commit_details.status_code != 200:
        raise Exception(f"Failed to get commit details: {commit_details.json()}")
    base_tree_sha = commit_details.json()["tree"]["sha"]
    print(f"Base tree SHA: {base_tree_sha}")

    # Step 5: Create a new tree with the new files.
    new_tree_sha = create_tree(base_tree_sha, tree_entries)
    print(f"New tree SHA: {new_tree_sha}")

    # Step 6: Create a new commit with the new tree.
    commit_message = "Add dummy files for test PR"
    new_commit_sha = create_commit(commit_message, new_tree_sha, latest_commit_sha)
    print(f"New commit SHA: {new_commit_sha}")

    # Step 7: Update the new branch to point to the new commit.
    update_branch(NEW_BRANCH, new_commit_sha)

    # Step 8: Create a pull request.
    pr_title = "Test PR via API - Dummy File Tree"
    pr_body = "This pull request adds six dummy files for testing purposes."
    create_pull_request(pr_title, pr_body, NEW_BRANCH, BASE_BRANCH)

if __name__ == "__main__":
    main()
