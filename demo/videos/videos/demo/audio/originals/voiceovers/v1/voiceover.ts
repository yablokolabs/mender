import type { Voiceover } from "videowright";

// The scene timing for this audio is in audio/tracks/v1/track.ts, which is the file
// that videowright reads. scripts/sync_audio.py writes it.
const voiceover: Voiceover = {
	audio_file: "./audio.mp3",
	provider: "elevenlabs",
	provider_timing_file: "./timing.json",
	eleven_labs_voice_id: "pFZP5JQG7iQjIQuC4Bku", // Lily
	timing: { perSegment: {} },
	notes:
		"Lily: British English, female, warm and steady. Model eleven_multilingual_v2.",
};

export default voiceover;
