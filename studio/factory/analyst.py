"""Агент-аналитик: раз в сутки смотрит YouTube Analytics и пишет выводы для креатора."""
import datetime, json, time
from studio.factory import common as C

RUN_EVERY_HOURS = 24


def _fetch_rankings(limit=20):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    tok = json.load(open(C.ROOT / "yt_token.json"))
    creds = Credentials(token=None, refresh_token=tok["refresh_token"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=tok["client_id"], client_secret=tok["client_secret"],
                        scopes=tok.get("scopes"))
    yt = build("youtube", "v3", credentials=creds)
    ya = build("youtubeAnalytics", "v2", credentials=creds)
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    vids, page = [], None
    while len(vids) < 60:
        pl = yt.playlistItems().list(part="contentDetails,snippet", playlistId=uploads,
                                     maxResults=50, pageToken=page).execute()
        for it in pl["items"]:
            vids.append((it["contentDetails"]["videoId"], it["snippet"]["title"]))
        page = pl.get("nextPageToken")
        if not page:
            break
    if not vids:
        return []
    ids = [v for v, _ in vids]
    title = {v: t for v, t in vids}
    rows = ya.reports().query(
        ids="channel==MINE", startDate="2020-01-01", endDate=datetime.date.today().isoformat(),
        metrics="views,averageViewPercentage,averageViewDuration", dimensions="video",
        filters="video==" + ",".join(ids[:50]), sort="-averageViewPercentage", maxResults=limit).execute()
    return [{"title": title.get(r[0], ""), "views": int(r[1]), "view_pct": r[2], "avg_sec": r[3]}
            for r in rows.get("rows", [])]


def maybe_analyze(project: dict) -> bool:
    last = C.read_state(f"analyst_last_{project['id']}.json", default={"ts": 0})
    if time.time() - last.get("ts", 0) < RUN_EVERY_HOURS * 3600:
        return False

    try:
        rows = _fetch_rankings()
    except Exception as e:
        C.log("analyst", f"ошибка YouTube Analytics: {e}")
        C.write_state(f"analyst_last_{project['id']}.json", {"ts": time.time(), "error": str(e)[:200]})
        return True

    if not rows:
        C.write_state(f"analyst_last_{project['id']}.json", {"ts": time.time()})
        return True

    top = rows[:5]; bottom = rows[-5:]
    md = ["# Выводы аналитики (авто, обновляется раз в сутки)", "",
          "## Лучше всего досматривают (view%)"]
    md += [f"- {r['title']} — {r['view_pct']:.0f}%, {r['views']} просмотров" for r in top]
    md += ["", "## Хуже всего досматривают"]
    md += [f"- {r['title']} — {r['view_pct']:.0f}%, {r['views']} просмотров" for r in bottom]
    md += ["", "Используй эти паттерны при выборе темы и хука для новых видео."]
    (C.STATE_DIR / f"insights_{project['id']}.md").write_text("\n".join(md), encoding="utf-8")
    C.write_state(f"analyst_last_{project['id']}.json", {"ts": time.time(), "videos": len(rows)})
    C.log("analyst", f"обновил инсайты по {len(rows)} видео")
    return True
