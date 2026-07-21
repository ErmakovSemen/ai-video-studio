"""CLI-точка входа монтажа НА ВОРКЕРЕ. Читает job.json, гоняет assemble.assemble(),
пишет прогресс в progress.json (чтобы веб-узел мог тянуть статус) и итог в out.mp4.

Запускается внутри контейнера prometey-app на эфемерном воркере:
  python -m studio.worker.run_montage /job

/job/job.json: {"inputs": ["/job/in0.mp4", ...], "prompt": "...", "captions": bool,
                "style": "...", "insert_mode": "fullscreen|lower", "aspect": "9:16|source"}
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

    out_path = os.path.join(job_dir, "out.mp4")
    workdir = os.path.join(job_dir, "work")
    os.makedirs(workdir, exist_ok=True)

    from studio import assemble
    try:
        res = assemble.assemble(
            job["inputs"], job.get("prompt", ""), out_path, workdir,
            progress=progress, captions=job.get("captions", False),
            style=job.get("style", "minimalist Asian ink wash on parchment"),
            max_tries=int(job.get("max_tries", 3)),
            aspect=job.get("aspect", "source"),
            insert_mode=job.get("insert_mode", "fullscreen"),
        )
        json.dump({"ok": True, "result": res}, open(os.path.join(job_dir, "result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        progress("готово", 100)
        print("MONTAGE_OK")
    except Exception as e:
        traceback.print_exc()
        json.dump({"ok": False, "error": str(e)[:500]}, open(os.path.join(job_dir, "result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        progress(f"ошибка: {e}", -1)
        print("MONTAGE_FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/job")
