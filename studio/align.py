"""Forced-ish alignment: get real per-word timings for TTS audio via faster-whisper ASR.

Used for backends that don't emit word boundaries (e.g. Yandex SpeechKit) so karaoke
captions land exactly on the voice. We transcribe the known VO audio, take ASR word
timings, and relabel them with the KNOWN script tokens (ASR spelling can drift). If the
word counts don't line up, return None and let the caller fall back to proportional timing.
"""
import os

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        name = os.getenv("WHISPER_MODEL", "small")
        _model = WhisperModel(name, device="cpu", compute_type="int8")
    return _model


def _asr_words(audio_path: str, lang: str = "ru"):
    model = _get_model()
    segments, _ = model.transcribe(audio_path, language=lang, word_timestamps=True,
                                   vad_filter=False)
    out = []
    for seg in segments:
        for w in (seg.words or []):
            out.append([w.word.strip(), float(w.start), float(w.end)])
    return out


def align_known(audio_path: str, text: str, lang: str = "ru"):
    """Return [(known_word, start, end), ...] or None if alignment isn't trustworthy."""
    try:
        asr = _asr_words(audio_path, lang)
    except Exception:
        return None
    known = text.split()
    if not asr or not known:
        return None
    # Best case: same number of tokens -> zip our text onto real ASR timings.
    if len(asr) == len(known):
        return [[known[i], asr[i][1], asr[i][2]] for i in range(len(known))]
    # Close mismatch (±2 tokens): stretch ASR timings proportionally onto known tokens.
    if abs(len(asr) - len(known)) <= max(2, len(known) // 6):
        t0, t1 = asr[0][1], asr[-1][2]
        span = max(0.01, t1 - t0)
        weights = [len(w) + 1 for w in known]
        tot = sum(weights)
        acc, res = t0, []
        for w, wt in zip(known, weights):
            end = acc + span * wt / tot
            res.append([w, acc, end]); acc = end
        return res
    return None
