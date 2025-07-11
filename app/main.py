import requests
from fastapi import FastAPI, HTTPException
import time
import base64
from dotenv import load_dotenv
import os
from fastapi.responses import RedirectResponse

load_dotenv()

ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID") or "aej6RB_qS7aMUFtZF4CWIw"
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET") or "xqxcoSiwd0d5Yw18iHlIGynS6kOCyNnO"
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID") or "qccLladIR1GXcA31gqfhZg"

app = FastAPI()

_zoom_token = None
_token_expiry = 0
waiting_user = None  # Simple in-memory matchmaking


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
        raise HTTPException(
            status_code=500, detail=f"Zoom token error: {response.text}")

    data = response.json()
    _zoom_token = data["access_token"]
    _token_expiry = time.time() + data["expires_in"]
    return _zoom_token


@app.post("/create_meeting")
def create_meeting():
    token = get_zoom_access_token()
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    meeting_data = {
        "topic": "Sanamus Matchmaking Meeting",
        "type": 1,
        "settings": {
            "join_before_host": True,
            "approval_type": 0,
            "mute_upon_entry": True
        }
    }

    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code != 201:
        raise HTTPException(
            status_code=500, detail=f"Zoom meeting creation failed: {response.text}")

    meeting = response.json()
    return {
        "join_url": meeting["join_url"],
        "start_url": meeting["start_url"],
        "meeting_id": meeting["id"],
    }


@app.get("/join")
def join_matchmaking():
    global waiting_user

    if waiting_user is None:
        # No one is waiting, this user becomes the waiting user
        token = get_zoom_access_token()
        url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        meeting_data = {
            "topic": "Sanamus Matchmaking Meeting",
            "type": 1,
            "settings": {
                "join_before_host": True,
                "approval_type": 0,
                "mute_upon_entry": True
            }
        }

        response = requests.post(url, headers=headers, json=meeting_data)
        if response.status_code != 201:
            raise HTTPException(
                status_code=500, detail=f"Zoom meeting creation failed: {response.text}")
        
        meeting = response.json()
        waiting_user = meeting["join_url"]
        return {"message": "Waiting for another user to join...", "join_url": waiting_user}
    
    else:
        # Someone is waiting, pair them
        join_url = waiting_user
        waiting_user = None  # Reset
        return RedirectResponse(join_url)

from fastapi.responses import RedirectResponse

waiting_user = None
meeting_cache = {}

@app.get("/join")
async def join_meeting():
    global waiting_user, meeting_cache

    if waiting_user is None:
        # First user — create meeting and store it
        meeting = create_zoom_meeting()
        meeting_cache["meeting"] = meeting
        waiting_user = True
        return RedirectResponse(url=meeting["start_url"])  # Host redirected
    else:
        # Second user — join meeting
        meeting = meeting_cache.get("meeting")
        waiting_user = None
        meeting_cache = {}
        return RedirectResponse(url=meeting["join_url"])  # Attendee redirected