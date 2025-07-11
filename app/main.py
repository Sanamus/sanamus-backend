import time
import base64
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Zoom credentials from environment or fallback
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID") or "your_client_id"
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET") or "your_client_secret"
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID") or "your_account_id"

app = FastAPI()

_zoom_token = None
_token_expiry = 0

# Simple in-memory matchmaking
waiting_user = None
meeting_cache = {}

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

def create_zoom_meeting():
    token = get_zoom_access_token()
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    meeting_data = {
        "topic": "Sanamus Matchmaking",
        "type": 1,  # Instant Meeting
        "settings": {
            "join_before_host": True,
            "approval_type": 0,
            "waiting_room": False,
            "host_video": False,
            "participant_video": False
        }
    }

    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code != 201:
        raise HTTPException(
            status_code=500, detail=f"Zoom meeting creation failed: {response.text}")

    return response.json()

@app.get("/join")
async def join_meeting():
    global waiting_user, meeting_cache

    if waiting_user is None:
        # First user - create a meeting and become host
        meeting = create_zoom_meeting()
        meeting_cache["meeting"] = meeting
        waiting_user = True
        return RedirectResponse(url=meeting["start_url"])
    else:
        # Second user - join existing meeting
        meeting = meeting_cache.get("meeting")
        waiting_user = None
        meeting_cache = {}
        return RedirectResponse(url=meeting["join_url"])

@app.get("/")
def root():
    return JSONResponse({"message": "Sanamus backend is running."})
