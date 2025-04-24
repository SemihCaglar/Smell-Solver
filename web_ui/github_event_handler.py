from flask import session, jsonify
import database.database as database
import utils
import json
import subprocess
from file_utils import add_context_to_comments, filter_comments_by_diff_intersection, replace_comment_block

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

    from ai_content.main import CommentSmellAI
    ai_processor = CommentSmellAI()

    # changed_files = utils.get_changed_files(payload) 
    # for file in changed_files:
    #     comments = utils.extract_comments(file)
    #     file["comments_metadata"] = comments["metadata"]
    #     comments = add_context_to_comments(comments, file["content"], file["comments_metadata"]["lang"])
    #     comments = filter_comments_by_diff_intersection(file["patch"], comments, file["content"])
    #     file["comments"] = comments
        
    #     # TODO i probably should handle previous comments here 
    #     # TODO remove method level comments
    #     for comment_entry in comments:
    #         comment_block = comment_entry["comment"]
    #         associated_code = comment_entry["associated_code"]

    #         # get suggestion
    #         comment_entry["smell_label"] = ai_processor.detect_comment_smell(associated_code, comment_block)
    #         comment_entry["repair_suggestion"] = ai_processor.repair_comment(associated_code, comment_block, comment_entry["smell_label"])

    #         # change content for the line range
    #         comment_entry["new_comment_block"] = replace_comment_block(file["content"], comment_entry, file["comments_metadata"]["lang"])
            
    # load changed files from the json
    with open("payloads/changed_files.json", "r") as f:
        changed_files = json.load(f)
            
    for file in changed_files:
        comments = file["comments"]
        for comment_entry in comments:
            comment_entry["new_comment_block"] = replace_comment_block(file["content"], comment_entry, file["comments_metadata"]["lang"])
            # now we have computed_start_line, computed_end_line, new_comment_block for each comment
            response = utils.post_suggestions_to_github(payload, file["filename"], comment_entry)
            comment_entry["github_response"] = response
            print(response)

    with open("payloads/changed_files.json", "w") as f:
        json.dump(changed_files, f, indent=4)
        
    # TODO burda kaldım
    
    return jsonify({
        "message": "Pull request event processed",
        "owner": owner,
        "repo_name": repo,
        "number": pr_number,
    }), 200
    