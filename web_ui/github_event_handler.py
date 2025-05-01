from flask import session, jsonify
import database.database as database
import utils
import json
import subprocess
from file_utils import add_context_to_comments, filter_comments_by_diff_intersection, replace_comment_block
from database.database import *

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
    github_repo_id   = payload["repository"]["id"]

    repo_internal_id = get_repository_id_by_full_name(repo_full_name)  
    if repo_internal_id is None:
        repo_internal_id = add_repository(
            installation_id,
            github_repo_id,
            repo_full_name
        )


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
    #        # TODO look for settings enabled
    #         comment_entry["repair_suggestion"] = ai_processor.repair_comment(associated_code, comment_block, comment_entry["smell_label"])

    #         # change content for the line range
    #         comment_entry["new_comment_block"] = replace_comment_block(file["content"], comment_entry, file["comments_metadata"]["lang"])
            
    # load changed files from the json
    with open("payloads/changed_files.json", "r") as f:
        changed_files = json.load(f)
            
    # for file in changed_files:
    #     comments = file["comments"]
    #     for comment_entry in comments:
    #         comment_entry["new_comment_block"] = replace_comment_block(file["content"], comment_entry, file["comments_metadata"]["lang"])
    #         # now we have computed_start_line, computed_end_line, new_comment_block for each comment
    #         response = utils.post_suggestions_to_github(payload, file["filename"], comment_entry)
    #         comment_entry["github_response"] = response
    #         print(response)

    with open("payloads/changed_files.json", "w") as f:
        json.dump(changed_files, f, indent=4)
       
    # DATABASE STUFF 
    # 1) Upsert the PR and get your local ID
    pr_id = add_or_update_pull_request(
        repo_internal_id = repo_internal_id,
        pr_number        = int(payload["number"]),
        title            = payload["pull_request"]["title"],
        status           = payload["action"],               # e.g. "opened", "synchronize", "closed"
        created_at       = payload["pull_request"]["created_at"]
    )

    # 3) Inside your loop over changed_files:
    for file in changed_files:
        # assign exactly the vars your helper needs:
        file_path = file["filename"]
        blob_sha  = file["sha"]
        status    = file["status"]
        # now call the helper with those variables:
        file_id = add_file_record(pr_id, repo_internal_id, file_path, blob_sha, status)

    commit_sha = payload["pull_request"]["head"]["sha"]
    for file in changed_files:
        file_path  = file["filename"]
        for comment_entry in file["comments"]:
            # 1) Post the suggestion
            response = comment_entry["github_response"] 
            
            github_id  = response["id"]
            github_url = response["html_url"]
            
            # 3) Prepare your own fields
            pr_id         = pr_id                            # from your earlier upsert
            line          = comment_entry["computed_start_line"]
            smell_type    = comment_entry["smell_label"]
            comment_body  = comment_entry["comment"]
            suggestion    = comment_entry.get("repair_suggestion", None)
            repair_flag   = comment_entry.get("repair_enabled", True)
            is_smell        = (smell_type != "Not A Smell")        #! or however you flag non-smells
            associated_code = comment_entry["associated_code"]

            add_comment_smell(
                        pr_id=pr_id,
                        file_path=file_path,
                        commit_sha=commit_sha,
                        line=line,
                        side="RIGHT",
                        smell_type=smell_type,
                        associated_code=associated_code,
                        comment_body=comment_body,
                        suggestion=suggestion,
                        github_comment_id=github_id,
                        github_comment_url=github_url,
                        is_smell=is_smell,
                        repair_enabled=repair_flag,
                        status="Pending"
                    )

    
    return jsonify({
        "message": "Pull request event processed",
        "owner": owner,
        "repo_name": repo,
        "number": pr_number,
    }), 200
    