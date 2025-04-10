from flask import Blueprint, request, jsonify
from github_event_handler import process_installation_event, process_pr_event
import json

github_bp = Blueprint('github', __name__)

@github_bp.route('/github-app-event', methods=['POST'])
def github_app_event():
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    payload = request.json
    print("Received GitHub event:", event_type)
    # save payload to file as json
    with open("github_event_payload.json", "w") as f:
        json.dump(payload, f, indent=4)
    if event_type == "installation":
        return process_installation_event(payload)
    elif event_type == "pull_request":
        return process_pr_event(payload)
    elif event_type == "ping":
        # Handle ping event
        print("Ping event received")
        return jsonify({"message": "Ping event received"}), 200
    #TODO: Handle other event types such as pull_request
    return jsonify({"message": "Event received"}), 200
