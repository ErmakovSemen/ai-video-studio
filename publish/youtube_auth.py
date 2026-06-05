"""One-time: mint a YouTube refresh token (run LOCALLY, opens your browser).

Prereq: a Google Cloud OAuth client of type "Desktop app" (see SETUP-YOUTUBE.md).
Provide its credentials one of two ways:
  A)  export YT_CLIENT_ID=...   export YT_CLIENT_SECRET=...   then run this.
  B)  put the downloaded client_secret.json next to this repo and run this.

Run:
    python -m publish.youtube_auth

It opens a browser, you pick the channel and click Allow, and it prints:
    YT_CLIENT_ID=...
    YT_CLIENT_SECRET=...
    YT_REFRESH_TOKEN=...
Set those three as env vars (locally and in Render) and the server can post itself.
"""
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Missing deps. Run: pip install google-auth-oauthlib google-api-python-client")

    cid, cs = os.getenv("YT_CLIENT_ID"), os.getenv("YT_CLIENT_SECRET")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    secret_file = os.path.join(here, "client_secret.json")

    if cid and cs:
        cfg = {"installed": {
            "client_id": cid, "client_secret": cs,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]}}
        flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    elif os.path.exists(secret_file):
        flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
        import json
        data = json.load(open(secret_file))["installed"]
        cid, cs = data["client_id"], data["client_secret"]
    else:
        sys.exit("No credentials. Set YT_CLIENT_ID/YT_CLIENT_SECRET or add client_secret.json. "
                 "See SETUP-YOUTUBE.md")

    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        sys.exit("No refresh token returned. Revoke prior access and retry with prompt=consent.")

    print("\n===== COPY THESE INTO YOUR ENV (locally + Render) =====")
    print(f"YT_CLIENT_ID={cid}")
    print(f"YT_CLIENT_SECRET={cs}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
    print("=======================================================")


if __name__ == "__main__":
    main()
