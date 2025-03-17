from flask import session, jsonify
import database.database as database

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

    session["installation_id"] = installation_id
    session["internal_repo_ids"] = internal_ids

    print("Session data after setting:", session)

    return jsonify({
        "message": "Installation successful",
        "installation_id": installation_id,
        "repositories": internal_ids
    }), 200
