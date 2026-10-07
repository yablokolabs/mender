#!/usr/bin/env bash
# Generates audio.mp3 and timing.json for this voiceover from provider_script.md.
# Needs ELEVENLABS_API_KEY in the environment (do not commit it), curl and jq.
# One run uses about 1,500 ElevenLabs characters. A library voice needs a paid plan.
# Afterwards run scripts/sync_audio.py to rebuild the track and the timing.
set -euo pipefail

: "${ELEVENLABS_API_KEY:?set ELEVENLABS_API_KEY in the environment}"
VOICE_ID="${VOICE_ID:-pFZP5JQG7iQjIQuC4Bku}" # Lily

here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# The text to speak is everything below the --- line.
script_text="$(sed '1,/^---$/d' "$here/provider_script.md")"
if [ -z "${script_text//[[:space:]]/}" ]; then
  echo "provider_script.md has no text below a --- line" >&2
  exit 1
fi
request="$(jq -n --arg text "$script_text" '{
  text: $text,
  model_id: "eleven_multilingual_v2",
  voice_settings: {stability: 0.5, similarity_boost: 0.75}
}')"

status="$(curl -sS --max-time 300 -o "$work/response.json" -w '%{http_code}' \
  -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}/with-timestamps" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$request")"
if [ "$status" != "200" ]; then
  echo "ElevenLabs returned HTTP $status:" >&2
  cat "$work/response.json" >&2
  exit 1
fi

# -e makes jq fail on a response that has no audio or no words, so a bad response
# cannot replace the files of the last good run.
jq -er '.audio_base64' "$work/response.json" | base64 --decode > "$work/audio.mp3"

# The API returns one timestamp for each character. Group the characters into words
# and leave out the <break ... /> tags.
jq -e '
  .alignment as $a
  | reduce range(0; $a.characters | length) as $i
      ({words: [], word: null, in_tag: false};
       $a.characters[$i] as $c
       | if .in_tag then (if $c == ">" then .in_tag = false else . end)
         elif $c == "<" then (if .word then .words += [.word] | .word = null else . end) | .in_tag = true
         elif ($c | test("^\\s+$")) then (if .word then .words += [.word] | .word = null else . end)
         elif .word then .word.word += $c | .word.end = $a.character_end_times_seconds[$i]
         else .word = {
           word: $c,
           start: $a.character_start_times_seconds[$i],
           end: $a.character_end_times_seconds[$i]
         }
         end)
  | {words: (if .word then .words + [.word] else .words end)}
  | select(.words | length > 0)
' "$work/response.json" > "$work/timing.json"

mv "$work/audio.mp3" "$here/audio.mp3"
mv "$work/timing.json" "$here/timing.json"
echo "wrote $here/audio.mp3 and $here/timing.json"
