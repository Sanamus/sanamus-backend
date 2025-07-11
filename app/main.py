import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
import time
import base64

load_dotenv()

app = FastAPI()

# Zoom credentials
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")

# Token cache
_zoom_token = None
_token_expiry = 0

# In-memory queue (replace with Redis for production)
queue = []

def get_zoom_access_token():
    global _zoom_token, _token_expiry

    if _zoom_token and time.time() < _token_expiry - 60:
        return _zoom_token

    auth_str = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    url = "https://zoom.us/oauth/token"
    headers = {
        "Authorization": f"Basic {b64_auth_str}"
    }
    params = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }

    response = requests.post(url, headers=headers, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Zoom token error: {response.text}")

    data = response.json()
    _zoom_token = data["access_token"]
    _token_expiry = time.time() + data["expires_in"]
    return _zoom_token

def create_zoom_meeting():
    token = get_zoom_access_token()
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    meeting_data = {
        "topic": "Sanamus Matchmaking",
        "type": 1,  # Instant meeting
        "settings": {
            "join_before_host": True,
            "approval_type": 0,
            "mute_upon_entry": True
        }
    }

    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code != 201:
        raise HTTPException(status_code=500, detail=f"Zoom meeting creation failed: {response.text}")

    return response.json()

@app.get("/join")
def join_queue():
    global queue

    if queue:
        # Someone is already waiting → pair them with current user
        partner = queue.pop(0)
        meeting = create_zoom_meeting()
        join_url = meeting["join_url"]

        # (Optional) Notify the first user via websocket or long polling
        print(f"Paired {partner} with new user. Meeting: {join_url}")

        return RedirectResponse(url=join_url)

    else:
        # No one in queue → add this user and wait
        user_id = str(time.time())  # Temporary user identifier
        queue.append(user_id)
        return {"message": "Waiting for a match... Please stay on this page."}