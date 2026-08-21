"""Score SmartCaption's transcription against hand-made captions.

Answers "did that setting actually help?" with a number instead of an opinion.
Every accuracy claim in the Model Guide and Accuracy Tips came from this.

Usage:
    python benchmark/run_benchmark.py <media file> <reference file> [--fps 60]

The reference is either an Adobe-style CSV ("Start Time","End Time","Text",...)
with HH:MM:SS:FF timecodes, or an .srt. Pass --fps for CSV references; it is
the frame rate of the video the timecodes were authored against.

Reports, per configuration:
    WER          word error rate -- the headline number, lower is better
    missed       words in the reference that never appeared (dropped speech)
    wrong        words transcribed as something else
    extra        words invented that were not said
    off          median timing error, + means captions run late
    <0.5s        share of matched words timed within half a second

Comparing configurations is what this is for; the absolute WER has a floor,
because hand captions use casual spellings and skip filler that a transcriber
faithfully includes.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scoring import load_truth, normalize_tokens, score  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main  # noqa: E402


def load_srt(path):
    """Parse an .srt into the same (tokens, [(token, start)]) shape as the CSV."""
    text = open(path, encoding="utf-8-sig").read()
    timed = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if len(lines) < 2:
            continue
        stamp = next((ln for ln in lines if "-->" in ln), None)
        if not stamp:
            continue
        body = " ".join(lines[lines.index(stamp) + 1:])
        start_s, end_s = (p.strip() for p in stamp.split("-->"))

        def to_seconds(value):
            h, m, rest = value.split(":")
            s, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        start, end = to_seconds(start_s), to_seconds(end_s)
        toks = normalize_tokens(body)
        if not toks:
            continue
        step = (end - start) / len(toks)
        for i, tok in enumerate(toks):
            timed.append((tok, start + i * step))
    return [t for t, _ in timed], timed


def load_reference(path, fps):
    if path.lower().endswith(".srt"):
        return load_srt(path)
    return load_truth(path, fps)


def transcribe(model_dir, media, **overrides):
    from faster_whisper import WhisperModel

    settings = {
        "vad_filter": True, "beam_size": 5, "condition_on_previous_text": False,
        "no_speech_threshold": 0.8, "initial_prompt": None, "language": "en",
        "compute_type": "int8",
    }
    settings.update(overrides)
    model = WhisperModel(model_dir, compute_type=settings["compute_type"],
                         device="cpu", local_files_only=True)
    gen, _ = model.transcribe(
        media,
        language=settings["language"],
        beam_size=settings["beam_size"],
        temperature=main.TEMPERATURE_FALLBACK,
        compression_ratio_threshold=main.COMPRESSION_RATIO_THRESHOLD,
        log_prob_threshold=main.LOG_PROB_THRESHOLD,
        no_speech_threshold=settings["no_speech_threshold"],
        condition_on_previous_text=settings["condition_on_previous_text"],
        word_timestamps=True,
        hallucination_silence_threshold=main.HALLUCINATION_SILENCE_THRESHOLD,
        vad_filter=settings["vad_filter"],
        initial_prompt=settings["initial_prompt"],
        vad_parameters={"min_silence_duration_ms": 700,
                        "min_speech_duration_ms": 100, "speech_pad_ms": 400},
    )
    timed = []
    for seg in gen:
        for word in (seg.words or []):
            for tok in normalize_tokens(word.word):
                timed.append((tok, word.start))
    return timed


CONFIGS = [
    ("large-v3-turbo  VAD on   (default)", "large-v3-turbo", {}),
    ("large-v3-turbo  VAD off",            "large-v3-turbo", {"vad_filter": False}),
    ("small           VAD on",             "small", {}),
    ("small           VAD off",            "small", {"vad_filter": False}),
]


def main_cli():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("media")
    parser.add_argument("reference")
    parser.add_argument("--fps", type=float, default=60.0,
                        help="frame rate for CSV timecodes (default 60)")
    parser.add_argument("--vocabulary", default=None,
                        help="comma-separated terms to prime the decoder with")
    args = parser.parse_args()

    truth, truth_timed = load_reference(args.reference, args.fps)
    print(f"reference: {len(truth)} words from {os.path.basename(args.reference)}\n")
    print(f"{'config':38} {'WER':>7} {'missed':>7} {'wrong':>6} {'extra':>6} {'off':>7} {'<0.5s':>6}")
    print("-" * 82)

    rows = []
    for label, model_name, overrides in CONFIGS:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "models", model_name)
        if not os.path.isfile(os.path.join(model_dir, "model.bin")):
            print(f"{label:38}   (not downloaded - skipping)")
            continue
        if args.vocabulary:
            overrides = {**overrides, "initial_prompt": args.vocabulary}
        result = score(truth, truth_timed, transcribe(model_dir, args.media, **overrides))
        rows.append((label, result))
        print(f"{label:38} {result['wer']:6.1%} {result['del']:7} {result['sub']:6} "
              f"{result['ins']:6} {result['median_offset']:+6.2f}s {result['within_0.5s']:5.0%}")

    if rows:
        best_label, best = min(rows, key=lambda r: r[1]["wer"])
        print(f"\nbest: {best_label.strip()} at {best['wer']:.1%} WER")


if __name__ == "__main__":
    main_cli()
