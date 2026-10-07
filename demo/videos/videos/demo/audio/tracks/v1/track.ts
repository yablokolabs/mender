import type { AudioTrack } from "videowright";

// Each array holds segment-relative seconds: one entry for each reveal after the first,
// then the end of the segment. The values are multiples of one frame at 60 fps, and each
// segment's `advances` carries the same values.
const track: AudioTrack = {
	audio_file: "./audio/tracks/v1/track.mp3",
	length_s: 95.97,
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
	audio_plan_path: "../../audio_plan.md",
	plan_snapshot_path: "./plan_snapshot.md",
	created_at: "2026-10-07T11:41:05Z",
	notes: "Voice-over only: Lily (ElevenLabs), normalised to -16 LUFS.",
};

export default track;
