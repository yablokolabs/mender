import type { Voiceover } from "videowright";

// The render reads timing from audio/tracks/v1/track.ts. This copy keeps the voiceover
// self-contained, as the videowright layout expects.
const voiceover: Voiceover = {
	audio_file: "./audio.mp3",
	provider: "elevenlabs",
	provider_timing_file: "./timing.json",
	eleven_labs_voice_id: "pFZP5JQG7iQjIQuC4Bku", // Lily
	timing: {
		perSegment: {
			intro: [4.5667, 13.1667, 16.45],
			setup: [4.0833, 6.55],
			fault: [2.2833, 8.1, 10.95],
			triage: [2.5333, 9.5833],
			diagnosis: [4.6667, 7, 11.2333],
			patch: [2.7, 5.8667, 11.4833],
			sandbox: [5.45, 9.95],
			pr: [8.9333, 11.7333],
			outro: [4.7667, 8.4333],
		},
	},
	notes: "Lily: British English, female, warm and steady. Model eleven_multilingual_v2.",
};

export default voiceover;
