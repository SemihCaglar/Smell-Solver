from flask import Blueprint, request, jsonify
from github_event_handler import process_installation_event

github_bp = Blueprint('github', __name__)

@github_bp.route('/github-app-event', methods=['POST'])
def github_app_event():
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    payload = request.json
    print("Received GitHub event:", event_type)
    if event_type == "installation":
        return process_installation_event(payload)
    #TODO: Handle other event types such as pull_request
    return jsonify({"message": "Event received"}), 200
