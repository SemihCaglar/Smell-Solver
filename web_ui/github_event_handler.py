from flask import session, jsonify
import database.database as database
import utils
import json
import subprocess

def process_installation_event(payload):
    """
    Processes GitHub App installation events.
    For each repository in the payload, generate a random internal ID,
    store the repository details in the SQLite database, and store the list of internal IDs
    in the session.
    """
    action = payload.get("action")
    installation_id = str(payload["installation"]["id"])

    if action == "deleted":
        database.remove_installation(installation_id)
        session.pop("installation_id", None)
        session.pop("internal_repo_ids", None) #TODO check if this is correct
        print(f"❌ Installation {installation_id} deleted.")
        return jsonify({"message": "Installation deleted"}), 200

    repositories = payload.get("repositories", [])
    database.add_installation(installation_id)

    internal_ids = []
    for repo in repositories:
        repo_full_name = repo["full_name"]
        github_repo_id = str(repo["id"])
        internal_id = database.add_repository(installation_id, github_repo_id, repo_full_name)
        internal_ids.append(internal_id)
        print(f"✅ App installed on {repo_full_name} (GitHub Repo ID: {github_repo_id}, Internal ID: {internal_id}, Installation ID: {installation_id})")

    session["installation_id"] = installation_id # TODO check if this is correct
    session["internal_repo_ids"] = internal_ids

    print("Session data after setting:", session)

    return jsonify({
        "message": "Installation successful",
        "installation_id": installation_id,
        "repositories": internal_ids
    }), 200

def process_pr_event(payload):
    # TODO consider closed and open and others
    installation_id = str(payload["installation"]["id"])
    owner = str(payload["repository"]["owner"]["login"])
    repo = str(payload["repository"]["name"])
    repo_full_name = str(payload["repository"]["full_name"])
    pr_number = str(payload["number"])

    changed_files = utils.get_changed_files(payload) 
    # TODO: process changed files.
    for file in changed_files:
        file["comments"] = utils.extract_comments(file)

    with open("payloads/changed_files.json", "w") as f:
        json.dump(changed_files, f, indent=4)
        
    # TODO burda kaldım

    # files are ready in the format: 
    #     {
    #     "sha": "917838fcc0d15a637cc04a473f6e77728a44aa7e",
    #     "filename": "pr_demo.java",
    #     "status": "added",
    #     "additions": 53,
    #     "deletions": 0,
    #     "changes": 53,
    #     "blob_url": "https://github.com/SemihCaglar/new-repo/blob/f6a750dad6153da6dbc38aabe5778f43366a7e4c/pr_demo.java",
    #     "patch": "@@ -0,0 +1,53 @@\n+\"\n+\n+public class DemoPR {\n+\n+    public static void main(String[] args) {\n+        // this makes a new scanner, which can read from\n+        // STDIN, located at System.in. The scanner lets us look\n+        // for tokens, aka stuff the user has entered.\n+        Scanner sc = new Scanner(System.in);\n+\n+        int a = 5; // Setting variable a to 5\n+\n+        taskTmpPath = ttp; // task tmp\n+        \n+        // int temp = 0;\n+        // System.out.println(\"Temp: \" + temp);\n+\n+        // TODO: Refactor main method for clarity and error handling.\n+        System.out.println(\"Demo complete.\");\n+    }\n+    \n+    /**\n+     * Substract two numbers.\n+     */\n+    public static int substract(int x, int y) {\n+        // add x and y\n+        return x - y;\n+    }\n+    \n+    public static void beautify() {\n+        /* ***********************\n+           *    Section Divider    *\n+           *********************** */\n+        System.out.println(\"Beautification method executed.\");\n+    }\n+    \n+    public static void attributedMethod() {\n+        // Added by John Doe\n+        System.out.println(\"Attributed method executed.\");\n+    }\n+    \n+    public void setFitnessePort(int fitnessePort) {\n+        /* I dedicate all this code, all my work, to my wife,\n+        Darlene, who will have to support me and our children\n+        and the dog once it gets released into the public.*/\n+\n+        // Port on which fitnesse would run. Defaults to 8082\n+        this.fitnessePort = fitnessePort;\n+    }\n+}\n+\n+\n+\"\n\\ No newline at end of file",
    #     "content": "\"\n\npublic class Demo..."
    # }
    
    return jsonify({
        "message": "Pull request event processed",
        "owner": owner,
        "repo_name": repo,
        "number": pr_number,
    }), 200
    