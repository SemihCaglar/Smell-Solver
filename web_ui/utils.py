import time
import jwt
import requests
from pyngrok import ngrok
import config
import base64
import subprocess
import tempfile
import json
import os

from github_utils import *

def start_ngrok():
    """Start an ngrok tunnel with a reserved subdomain using pyngrok."""
    ngrok.set_auth_token(config.NGROK_TOKEN)
    if not ngrok.get_tunnels():
        public_url = ngrok.connect(config.NGROK_PORT, "http", subdomain=config.NGROK_SUBDOMAIN).public_url
        print(f"✅ ngrok tunnel started: {public_url}")
    return ngrok.get_tunnels()[0].public_url

def extract_comments(file):
    """
    Extracts comments from the given file content using the `nirjas` command.

    Args:
        file (dict): A dictionary containing file metadata, including its content.

    Returns:
        str: The output of the `nirjas` command, or None if an error occurs.
    """
    file_content = file.get("content")
    if not file_content:
        print(f"No content found for file: {file['filename']}")
        return None

    try:
        # Create a temporary file to store the content
        with tempfile.NamedTemporaryFile(mode="w+", suffix=f"_{os.path.basename(file['filename'])}") as temp_file:
            temp_file.write(file_content)
            temp_file.flush()  # Ensure content is written to disk

            # Run the `nirjas` command with the temporary file
            command = f"nirjas {temp_file.name}"
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # print(f"Command Output for {file['filename']}: {result.stdout}")
            parsed_output = json.loads(result.stdout)
            return parsed_output 
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing command for {file['filename']}: {e.stderr}")
        return None