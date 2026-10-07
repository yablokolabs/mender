# Audio Plan

## Plan

VO-only track. Single full-file voiceover placed at 0s, normalised to -16 LUFS
(the provider file measures -24.1 LUFS, which is quiet for a web video).

### Cue 1 -- VO (full file)
Source: audio/originals/voiceovers/v1/
Slice: full file
Place at: 0s
Volume: 100%
Fades: none
Notes: Full voiceover, see timing.json for word timings.

ffmpeg snippet:
[0:a] loudnorm=I=-16:TP=-1.5:LRA=11 [vo1]

### Final mix command

ffmpeg -y \
  -i audio/originals/voiceovers/v1/audio.mp3 \
  -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 44100 \
  -c:a libmp3lame -q:a 2 \
  {TRACK_OUT}

## Log

## 2026-10-07 11:41 -- Synced timing to v1
**Segments:** intro, setup, fault, triage, diagnosis, patch, sandbox, pr, outro
**Total duration:** 96.4s

## 2026-10-07 11:41 -- Adopted v1 as active track

## 2026-10-07 11:41 -- Rendered v1 (voice-over only, Lily)
**Change:** First audio plan for this video.
**Why:** The video had no narration.
**Render:** audio/tracks/v1/track.mp3
