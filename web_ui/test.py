import web_ui.utils
import json

with open("changed_files.json", "r") as f:
    changed_files = json.load(f)
for file in changed_files:
    comments = utils.extract_comments(file)
    # save comment as json
    with open("comments.json", "w") as f:
        json.dump(comments, f, indent=4)