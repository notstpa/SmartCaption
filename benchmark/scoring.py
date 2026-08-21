"""Score SmartCaption's output against hand-made ground-truth captions.

Ground truth is an Adobe-style CSV of HH:MM:SS:FF timecodes. Reports word error
rate (how much text is wrong) and median timing offset (how far captions sit
from the words they belong to), so a config that recovers more words but smears
their timing cannot look like a win.
"""
import csv
import os
import re
import sys
import unicodedata

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
os.environ.setdefault("HF_HOME", os.path.join(_REPO, "models"))
os.environ.setdefault("HF_HUB_CACHE", os.path.join(_REPO, "models"))

# Hand captions censor profanity and carry performance notes; neither is
# something the transcriber can be expected to reproduce.
UNCENSOR = {
    "fck": "fuck", "fuk": "fuck", "fcking": "fucking", "fking": "fucking",
    "btch": "bitch", "puy": "pussy", "pusy": "pussy", "sht": "shit",
}
BY_SHAPE = {
    ("f", 4): "fuck", ("f", 5): "fucks", ("f", 6): "fucked", ("f", 7): "fucking",
    ("b", 5): "bitch", ("s", 4): "shit", ("p", 5): "pussy", ("a", 3): "ass",
    ("d", 4): "damn", ("c", 4): "cunt",
}
# Only a field that is entirely wrapped in asterisks is stage direction. A
# looser pattern eats the asterisks used to censor profanity: "pu**y" contains
# "**", and across a line it will happily span from f*ck to b*tch.
NON_SPEECH = re.compile(r"\*[^*]*\*")          # matched against the whole field
EMOTICON = re.compile(r"[:;>]-?[)(/|\\D3P]+")   # :) :/ >:(

# Spoken-form variants that are the same word to a listener. Scoring these as
# errors would punish a correct transcription for spelling.
EQUIV = {
    # Contractions collapse to ONE canonical token on both sides. Expanding
    # "you're" to "you are" while the hand caption writes "your" would score a
    # more-accurate transcription as two errors.
    "youre": "your", "your": "your",
    "im": "im", "ive": "ive", "ill": "ill", "id": "id",
    "its": "its", "thats": "thats", "whats": "whats", "hes": "hes", "shes": "shes",
    "dont": "dont", "didnt": "didnt", "cant": "cant", "wont": "wont", "isnt": "isnt",
    # Multi-word spoken forms expand on both sides so they line up.
    "gonna": "going to", "wanna": "want to", "gotta": "got to", "kinda": "kind of",
    "cuz": "because", "cause": "because", "goin": "going",
    "ok": "okay", "alright": "all right", "yea": "yeah", "ya": "yeah",
    "bout": "about", "til": "until", "till": "until",
    "aww": "aw", "awww": "aw", "ah": "aw",
}


def normalize_tokens(text):
    text = text.strip()
    if NON_SPEECH.fullmatch(text):
        return []
    text = EMOTICON.sub(" ", text)
    text = unicodedata.normalize("NFKD", text).lower()
    out = []
    for raw in text.split():
        word = re.sub(r"[^a-z'*-]", "", raw)
        if not word:
            continue
        if "*" in word:
            stripped = word.replace("*", "")
            # "f******" strips to a bare "f"; length is what distinguishes
            # fuck from fucking, so fall back to (initial, masked length).
            word = UNCENSOR.get(stripped) or BY_SHAPE.get((stripped[:1], len(word)), stripped)
        word = word.replace("-", "").replace("'", "")
        if not word:
            continue
        out.extend(EQUIV.get(word, word).split())
    return out


def parse_timecode(tc, fps=60.0):
    h, m, s, f = (int(part) for part in tc.split(":"))
    return h * 3600 + m * 60 + s + f / fps


def load_truth(csv_path, fps=60.0):
    """-> (token list, [(token, start_seconds), ...])"""
    timed = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            start = parse_timecode(row["Start Time"], fps)
            end = parse_timecode(row["End Time"], fps)
            toks = normalize_tokens(row["Text"])
            if not toks:
                continue
            # Spread a caption's words evenly across its own span.
            step = (end - start) / len(toks)
            for i, tok in enumerate(toks):
                timed.append((tok, start + i * step))
    return [t for t, _ in timed], timed


def levenshtein_ops(ref, hyp):
    """Standard WER table; returns (substitutions, deletions, insertions, alignment)."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
        bt[i][0] = "del"
    for j in range(1, m + 1):
        d[0][j] = j
        bt[0][j] = "ins"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                d[i][j], bt[i][j] = d[i - 1][j - 1], "ok"
                continue
            sub, dele, ins = d[i - 1][j - 1] + 1, d[i - 1][j] + 1, d[i][j - 1] + 1
            best = min(sub, dele, ins)
            d[i][j] = best
            bt[i][j] = "sub" if best == sub else ("del" if best == dele else "ins")
    i, j, ops, align = n, m, {"sub": 0, "del": 0, "ins": 0, "ok": 0}, []
    while i > 0 or j > 0:
        op = bt[i][j]
        ops[op] += 1
        if op in ("ok", "sub"):
            align.append((op, i - 1, j - 1))
            i, j = i - 1, j - 1
        elif op == "del":
            align.append((op, i - 1, None))
            i -= 1
        else:
            align.append((op, None, j - 1))
            j -= 1
    align.reverse()
    return ops, align


def score(truth_tokens, truth_timed, hyp_timed):
    """hyp_timed: [(token, start_seconds), ...]"""
    hyp_tokens = [t for t, _ in hyp_timed]
    ops, align = levenshtein_ops(truth_tokens, hyp_tokens)
    errors = ops["sub"] + ops["del"] + ops["ins"]
    wer = errors / max(len(truth_tokens), 1)

    offsets = []
    for op, ri, hj in align:
        if op == "ok":
            offsets.append(hyp_timed[hj][1] - truth_timed[ri][1])
    offsets.sort()
    med = offsets[len(offsets) // 2] if offsets else float("nan")
    mad = (sorted(abs(o - med) for o in offsets)[len(offsets) // 2]
           if offsets else float("nan"))
    within = sum(1 for o in offsets if abs(o - 0.0) <= 0.5) / len(offsets) if offsets else 0.0
    return {
        "wer": wer, "sub": ops["sub"], "del": ops["del"], "ins": ops["ins"],
        "hit": ops["ok"], "ref_len": len(truth_tokens), "hyp_len": len(hyp_tokens),
        "median_offset": med, "offset_spread": mad, "within_0.5s": within,
    }
