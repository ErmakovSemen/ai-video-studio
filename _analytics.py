"""Pull per-video retention from YouTube Analytics (needs expanded-scope token).
Lists channel uploads + averageViewPercentage / avg duration / views, ranked."""
import os, json, sys, datetime
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

tok = json.load(open(os.path.join(ROOT, "yt_token.json")))
creds = Credentials(token=None, refresh_token=tok["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=tok["client_id"], client_secret=tok["client_secret"],
                    scopes=tok.get("scopes"))
yt = build("youtube", "v3", credentials=creds)
ya = build("youtubeAnalytics", "v2", credentials=creds)

ch = yt.channels().list(part="contentDetails", mine=True).execute()
uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
vids, page = [], None
while True and len(vids) < 60:
    pl = yt.playlistItems().list(part="contentDetails,snippet", playlistId=uploads,
                                 maxResults=50, pageToken=page).execute()
    for it in pl["items"]:
        vids.append((it["contentDetails"]["videoId"], it["snippet"]["title"]))
    page = pl.get("nextPageToken")
    if not page:
        break

ids = [v for v, _ in vids]
title = {v: t for v, t in vids}
rows = ya.reports().query(
    ids="channel==MINE", startDate="2020-01-01",
    endDate=datetime.date.today().isoformat(),
    metrics="views,averageViewPercentage,averageViewDuration,estimatedMinutesWatched",
    dimensions="video", filters="video==" + ",".join(ids[:50]),
    sort="-averageViewPercentage", maxResults=50).execute()

print(f"{'view%':>6} {'avgSec':>6} {'views':>6}  title")
for r in rows.get("rows", []):
    vid, views, vp, avs, _ = r
    print(f"{vp:6.1f} {avs:6.0f} {int(views):6d}  {title.get(vid,'')[:46]}")
