import requests
import json

# Replace with your details
GITHUB_TOKEN = "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"  # Use a PAT or installation token
OWNER = "SemihCaglar"  # Repository owner
REPO = "new-repo"  # Repository name
HEAD_BRANCH = "feature-branch"  # The branch you want to merge (must exist)
BASE_BRANCH = "master"  # The branch you are merging into
NEW_BRANCH = "feature-branch"  # New branch to be created
FILE_PATH = "pr_demo.java"  # File to be added
FILE_CONTENT = """

public class DemoPR {

    public static void main(String[] args) {
        // this makes a new scanner, which can read from
        // STDIN, located at System.in. The scanner lets us look
        // for tokens, aka stuff the user has entered.
        Scanner sc = new Scanner(System.in);

        int a = 5; // Setting variable a to 5

        taskTmpPath = ttp; // task tmp
        
        // int temp = 0;
        // System.out.println("Temp: " + temp);

        // TODO: Refactor main method for clarity and error handling.
        System.out.println("Demo complete.");
    }
    
    /**
     * Substract two numbers.
     */
    public static int substract(int x, int y) {
        // add x and y
        return x - y;
    }
    
    public static void beautify() {
        /* ***********************
           *    Section Divider    *
           *********************** */
        System.out.println("Beautification method executed.");
    }
    
    public static void attributedMethod() {
        // Added by John Doe
        System.out.println("Attributed method executed.");
    }
    
    public void setFitnessePort(int fitnessePort) {
        /* I dedicate all this code, all my work, to my wife,
        Darlene, who will have to support me and our children
        and the dog once it gets released into the public.*/

        // Port on which fitnesse would run. Defaults to 8082
        this.fitnessePort = fitnessePort;
    }
}


"""

# GitHub API URLs
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"
REFS_URL = f"{BASE_URL}/git/refs"
BLOBS_URL = f"{BASE_URL}/git/blobs"
TREES_URL = f"{BASE_URL}/git/trees"
COMMITS_URL = f"{BASE_URL}/git/commits"
HEADS_URL = f"{REFS_URL}/heads/{NEW_BRANCH}"
PR_URL = f"{BASE_URL}/pulls"

# Headers for authentication
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Step 1: Get the latest commit SHA from master
response = requests.get(f"{REFS_URL}/heads/{BASE_BRANCH}", headers=HEADERS)
if response.status_code != 200:
    print(f"❌ Failed to get latest commit: {response.json()}")
    exit(1)
latest_commit_sha = response.json()["object"]["sha"]

# Step 2: Check if the new branch already exists
response = requests.get(HEADS_URL, headers=HEADERS)
if response.status_code == 200:
    print(f"🔄 Branch '{NEW_BRANCH}' already exists. Using existing branch.")
else:
    # Step 3: Create a new branch from master
    payload = {
        "ref": f"refs/heads/{NEW_BRANCH}",
        "sha": latest_commit_sha
    }
    response = requests.post(REFS_URL, headers=HEADERS, json=payload)
    if response.status_code != 201:
        print(f"❌ Failed to create branch: {response.json()}")
        exit(1)
    print(f"✅ Branch '{NEW_BRANCH}' created.")

# Step 4: Create a blob (content of the new file)
payload = {
    "content": json.dumps(FILE_CONTENT).encode("utf-8").decode("unicode_escape"),
    "encoding": "utf-8"
}
response = requests.post(BLOBS_URL, headers=HEADERS, json=payload)
if response.status_code != 201:
    print(f"❌ Failed to create blob: {response.json()}")
    exit(1)
blob_sha = response.json()["sha"]

# Step 5: Get the tree SHA of the latest commit
response = requests.get(f"{BASE_URL}/git/commits/{latest_commit_sha}", headers=HEADERS)
if response.status_code != 200:
    print(f"❌ Failed to get commit details: {response.json()}")
    exit(1)
tree_sha = response.json()["tree"]["sha"]

# Step 6: Create a new tree with the new file
payload = {
    "base_tree": tree_sha,
    "tree": [{
        "path": FILE_PATH,
        "mode": "100644",
        "type": "blob",
        "sha": blob_sha
    }]
}
response = requests.post(TREES_URL, headers=HEADERS, json=payload)
if response.status_code != 201:
    print(f"❌ Failed to create tree: {response.json()}")
    exit(1)
new_tree_sha = response.json()["sha"]

# Step 7: Create a new commit with the tree
payload = {
    "message": "Added pr_test.txt via API",
    "tree": new_tree_sha,
    "parents": [latest_commit_sha]
}
response = requests.post(COMMITS_URL, headers=HEADERS, json=payload)
if response.status_code != 201:
    print(f"❌ Failed to create commit: {response.json()}")
    exit(1)
new_commit_sha = response.json()["sha"]

# Step 8: Update the existing branch to point to the new commit
payload = {
    "sha": new_commit_sha,
    "force": True
}
response = requests.patch(HEADS_URL, headers=HEADERS, json=payload)
if response.status_code != 200:
    print(f"❌ Failed to update branch: {response.json()}")
    exit(1)
print(f"✅ Branch '{NEW_BRANCH}' updated with new commit.")

# Step 9: Create a pull request
payload = {
    "title": "Test PR via API",
    "body": "This PR adds pr_test.java automatically via the GitHub API.",
    "head": NEW_BRANCH,  # The source branch
    "base": BASE_BRANCH   # The target branch
}
response = requests.post(PR_URL, headers=HEADERS, json=payload)
if response.status_code != 201:
    print(f"❌ Failed to create PR: {response.json()}")
    exit(1)

pr_info = response.json()
print(f"✅ Pull Request Created: {pr_info['html_url']}")