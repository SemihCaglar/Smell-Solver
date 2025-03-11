import requests
import config
from requests.auth import HTTPBasicAuth

def create_repo(token, repo_name):
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "private": False
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        repo_info = response.json()
        return repo_info
    else:
        return None

if __name__ == "__main__":
    token = "your_personal_access_token"
    repo_name = "new-repo"
    repo_info = create_repo(token, repo_name)
    if repo_info:
        print(f"Repository created: {repo_info['name']} - URL: {repo_info['html_url']}")
    else:
        print("Failed to create repository")
import requests
import config

def get_pull_requests(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pull_requests = response.json()
        return pull_requests
    else:
        return None

if __name__ == "__main__":
    owner = "octocat"
    repo = "Hello-World"
    pull_requests = get_pull_requests(owner, repo)
    if pull_requests:
        for pr in pull_requests:
            print(f"PR #{pr['number']}: {pr['title']} - {pr['html_url']}")
    else:
        print("Failed to get pull requests")