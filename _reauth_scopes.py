"""Re-auth with expanded scopes: YouTube Analytics (read) + manage videos. Writes token."""
import os, json, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
tokpath = os.path.join(ROOT, "yt_token.json")
old = json.load(open(tokpath))
cfg = {"installed": {
    "client_id": old["client_id"], "client_secret": old["client_secret"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost:8766/"]}}
flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
creds = flow.run_local_server(port=8766, open_browser=False, prompt="consent",
                              access_type="offline",
                              authorization_prompt_message="AUTHLINK: {url}")
if creds.refresh_token:
    old["token"] = creds.token
    old["refresh_token"] = creds.refresh_token
    old["scopes"] = list(creds.scopes) if creds.scopes else SCOPES
    old["expiry"] = creds.expiry.isoformat() + "Z" if creds.expiry else ""
    json.dump(old, open(tokpath, "w"), indent=2)
    print("TOKEN_OK")
else:
    print("NO_REFRESH")
