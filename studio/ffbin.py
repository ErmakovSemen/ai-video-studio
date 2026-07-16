"""Выбор ffmpeg-бинарника: предпочитаем системный (обычно собран с drawtext/libass),
бэкапом — статический из imageio_ffmpeg. Причина: минимальные статические сборки
imageio_ffmpeg на некоторых платформах (напр. linux-x86_64-v7.0.2) собраны БЕЗ
фильтра drawtext, из-за чего burn_hook/scene_clip (титры, хук, подписи) молча
падали — ffmpeg возвращал ошибку, а вызовы вида subprocess.run(capture_output=True)
без проверки returncode эту ошибку проглатывали."""
import functools
import os
import shutil
import subprocess


@functools.lru_cache(maxsize=1)
def resolve() -> str:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff and _has_drawtext(sys_ff):
        return sys_ff
    import imageio_ffmpeg
    bundled = imageio_ffmpeg.get_ffmpeg_exe()
    if _has_drawtext(bundled):
        return bundled
    # ни один вариант не имеет drawtext — берём системный, если он вообще есть
    # (лучше сломаться явно на конкретном вызове, чем совсем не запуститься)
    return sys_ff or bundled


def _has_drawtext(ff: str) -> bool:
    try:
        r = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=10)
        return "drawtext" in r.stdout
    except Exception:
        return False


def run_checked(args: list, out_path: str = None, timeout: int = 300):
    """subprocess.run для ffmpeg, который реально проверяет результат — иначе сбой
    (например, отсутствующий фильтр, битый инпут, OOM) молча оставляет пустой/старый
    выходной файл, и весь пайплайн думает, что всё в порядке."""
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({args[0]} ...): {r.stderr[-800:]}")
    if out_path and (not os.path.exists(out_path) or os.path.getsize(out_path) < 100):
        raise RuntimeError(f"ffmpeg вернул код 0, но {out_path} не создан/пуст: {r.stderr[-800:]}")
    return r
