import time
import base64
import os
import requests
import uuid
import redis

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID") or "your_client_id"
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET") or "your_client_secret"
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID") or "your_account_id"

# Connect to Redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
MATCHMAKING_QUEUE = "sanamus:queue"
MEETING_CACHE = "sanamus:meeting_cache"

app = FastAPI()

_zoom_token = None
_token_expiry = 0

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
        "type": 1,
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
        raise HTTPException(status_code=500, detail=f"Zoom meeting creation failed: {response.text}")

    return response.json()

@app.get("/join")
async def join_meeting():
    user_id = str(uuid.uuid4())  # Could be real user ID later

    queue = redis_client.lrange(MATCHMAKING_QUEUE, 0, -1)

    if queue:
        # Match with the person at the front
        partner_id = redis_client.lpop(MATCHMAKING_QUEUE)
        meeting_data = create_zoom_meeting()

        # Clear previous meeting (just in case)
        redis_client.delete(MEETING_CACHE)

        # Store full meeting info (optional)
        redis_client.hmset(MEETING_CACHE, {
            "host": user_id,
            "guest": partner_id,
            "start_url": meeting_data["start_url"],
            "join_url": meeting_data["join_url"]
        })

        return RedirectResponse(url=meeting_data["join_url"])
    else:
        # No one waiting — queue this user
        redis_client.rpush(MATCHMAKING_QUEUE, user_id)
        return JSONResponse({
            "status": "waiting",
            "message": "Waiting for another user to join..."
        })

@app.get("/")
def root():
    return JSONResponse({"message": "Sanamus backend is running."})