"""CLI-точка входа НАРЕЗКИ на воркере. Читает /job/job.json, гоняет clipper.clip_to_shorts(),
пишет прогресс в progress.json и результаты в /job/out/short*.mp4 + result.json.

  python -m studio.worker.run_clip /job
/job/job.json: {"video": "/job/inputs/in0.mov", "n": 5, "captions": true,
                "min_s": 20, "max_s": 60}
"""
import json
import os
import sys
import traceback


def main(job_dir):
    job = json.load(open(os.path.join(job_dir, "job.json"), encoding="utf-8"))
    prog_path = os.path.join(job_dir, "progress.json")

    def progress(msg, pct):
        try:
            json.dump({"stage": msg, "progress": pct}, open(prog_path, "w", encoding="utf-8"),
                      ensure_ascii=False)
        except Exception:
            pass

    out_dir = os.path.join(job_dir, "out")
    workdir = os.path.join(job_dir, "work")
    from studio import clipper
    try:
        res = clipper.clip_to_shorts(
            job["video"], out_dir, workdir,
            n=int(job.get("n", 5)), captions=job.get("captions", True),
            min_s=int(job.get("min_s", 20)), max_s=int(job.get("max_s", 60)),
            progress=progress)
        # пути делаем относительными для переноса на веб-узел
        for s in res.get("shorts", []):
            s["file"] = os.path.basename(s["path"])
        json.dump({"ok": True, "result": res}, open(os.path.join(job_dir, "result.json"), "w",
                  encoding="utf-8"), ensure_ascii=False)
        progress("готово", 100)
        print("CLIP_OK")
    except Exception as e:
        traceback.print_exc()
        json.dump({"ok": False, "error": str(e)[:500]}, open(os.path.join(job_dir, "result.json"), "w",
                  encoding="utf-8"), ensure_ascii=False)
        progress(f"ошибка: {e}", -1)
        print("CLIP_FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/job")
