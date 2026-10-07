#!/usr/bin/env python3
"""Rebuild audio track v1 of the demo video and sync the scene timing to it.

Run this after `videos/demo/audio/originals/voiceovers/v1/generate.sh`. It:

1. normalises the voiceover to -16 LUFS and writes `audio/tracks/v1/track.mp3`;
2. computes, from the word timestamps in `timing.json`, when each scene starts and when
   each reveal inside a scene happens;
3. writes those times to `audio/tracks/v1/track.ts` and to the `advances` of each
   segment (videowright reads the track; the segment values are the fallback).

The times are segment-relative seconds and multiples of one frame, so that rounding in
the render cannot add up to audio drift. Needs ffmpeg and ffprobe.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VIDEO = PROJECT / "videos" / "demo"
VOICEOVER = VIDEO / "audio" / "originals" / "voiceovers" / "v1"
TRACK = VIDEO / "audio" / "tracks" / "v1"

FPS = 60
SCENE_LEAD_S = 0.35  # a scene starts this long before its first word
CUE_LEAD_S = 0.15  # a reveal starts this long before its cue words
TAIL_S = 0.40  # the video goes on this long after the audio ends

# Segment id -> the words that start each reveal after the first one. The segments are
# in timeline order, one for each block of provider_script.md between <break> tags.
# The last match in the block is used, so a cue can repeat an earlier word.
CUES: dict[str, list[str]] = {
    "intro": ["It finds", "Mender never"],
    "setup": ["All twenty-one"],
    "fault": ["The memory limit", "The pod is"],
    "triage": ["The nano model"],
    "diagnosis": ["and writes", "The report carries"],
    "patch": ["It can only", "Here,"],
    "sandbox": ["Twenty-one of"],
    "pr": ["A person"],
    "outro": ["Mender."],
}


def normalise(word: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", word.lower())


def build_track() -> float:
    TRACK.mkdir(parents=True, exist_ok=True)
    track = TRACK / "track.mp3"
    subprocess.run(
        [
            *("ffmpeg", "-v", "error", "-y", "-i", str(VOICEOVER / "audio.mp3")),
            *("-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100"),
            *("-c:a", "libmp3lame", "-q:a", "2", str(track)),
        ],
        check=True,
    )
    probe = subprocess.run(
        [
            *("ffprobe", "-v", "error", "-show_entries", "format=duration"),
            *("-of", "default=nw=1:nk=1", str(track)),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(probe.stdout)


def compute_timing(duration: float) -> dict[str, list[float]]:
    words = json.loads((VOICEOVER / "timing.json").read_text())["words"]
    script = (VOICEOVER / "provider_script.md").read_text().split("\n---\n", 1)[1]
    blocks = [block.split() for block in re.split(r"<break[^>]*/>", script)]
    if len(blocks) != len(CUES):
        raise SystemExit(f"{len(blocks)} script blocks, but {len(CUES)} segments in CUES")
    spoken = [word["word"] for word in words]
    written = [word for block in blocks for word in block]
    if spoken != written:
        raise SystemExit("timing.json does not match provider_script.md; run generate.sh")

    firsts = [sum(len(block) for block in blocks[:index]) for index in range(len(blocks))]
    scene_starts = [0.0] + [words[first]["start"] - SCENE_LEAD_S for first in firsts[1:]]
    scene_ends = [*scene_starts[1:], duration + TAIL_S]

    timing: dict[str, list[float]] = {}
    for (segment, cues), block, first, start, end in zip(
        CUES.items(), blocks, firsts, scene_starts, scene_ends, strict=True
    ):
        block_words = [normalise(word) for word in block]
        reveals = []
        for cue in cues:
            target = [normalise(word) for word in cue.split()]
            matches = [
                index
                for index in range(len(block_words) - len(target) + 1)
                if block_words[index : index + len(target)] == target
            ]
            if not matches:
                raise SystemExit(f"cue {cue!r} is not in the script of segment {segment!r}")
            reveals.append(words[first + matches[-1]]["start"] - CUE_LEAD_S)
        moments = [*reveals, end]
        if moments != sorted(moments) or moments[0] - start < 0.5:
            raise SystemExit(f"segment {segment!r}: reveals are out of order or too early")
        start_frame = round(start * FPS)
        timing[segment] = [
            round((round(moment * FPS) - start_frame) / FPS, 4) for moment in moments
        ]
    return timing


def as_ts(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:g}" for value in values) + "]"


def write_track(duration: float, timing: dict[str, list[float]]) -> None:
    rows = "".join(f"\t\t\t{segment}: {as_ts(values)},\n" for segment, values in timing.items())
    (TRACK / "track.ts").write_text(
        'import type { AudioTrack } from "videowright";\n'
        "\n"
        "// Written by scripts/sync_audio.py. Each array holds segment-relative seconds: one\n"
        "// entry for each reveal after the first, then the end of the segment.\n"
        "const track: AudioTrack = {\n"
        '\taudio_file: "./audio/tracks/v1/track.mp3",\n'
        f"\tlength_s: {duration:.2f},\n"
        "\ttiming: {\n"
        "\t\tperSegment: {\n"
        f"{rows}"
        "\t\t},\n"
        "\t},\n"
        '\taudio_plan_path: "../../audio_plan.md",\n'
        '\tplan_snapshot_path: "./plan_snapshot.md",\n'
        f'\tcreated_at: "{datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}",\n'
        "};\n"
        "\n"
        "export default track;\n"
    )


def write_segments(timing: dict[str, list[float]]) -> None:
    for segment, values in timing.items():
        path = PROJECT / "segments" / segment / "index.ts"
        source, count = re.subn(
            r"advances: \[[^\]]*\],", f"advances: {as_ts(values)},", path.read_text()
        )
        if count != 1:
            raise SystemExit(f"{path}: expected one `advances: [...]` line")
        path.write_text(source)


def main() -> None:
    duration = build_track()
    timing = compute_timing(duration)
    write_track(duration, timing)
    write_segments(timing)
    total = sum(values[-1] for values in timing.values())
    for segment, values in timing.items():
        print(f"{segment:10s} {as_ts(values)}")
    print(f"audio {duration:.2f} s, video {total:.2f} s ({round(total * FPS)} frames)")


if __name__ == "__main__":
    main()
