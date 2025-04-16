import requests
import json
import os

# Load the payload from the JSON file
current_dir = os.path.dirname(os.path.abspath(__file__))
payload_path = os.path.join(current_dir, "update_pr_payload.json")
with open(payload_path, "r") as file:
    payload = json.load(file)

# Define the API endpoint URL
api_url = "https://smellsolver.eu.ngrok.io/github-app-event"  # Replace with your API URL

# Send POST request with the payload
headers = {"Content-Type": "application/json"}
response = requests.post(api_url, json=payload, headers=headers)

# Validate the response
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Test Passed: API responded with status 200.")
    print("Response Data:", response.json())
else:
    print("Test Failed: API did not respond with status 200.")
    print("Response Content:", response.text)# Python