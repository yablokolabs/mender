import type { AudioTrack } from "videowright";

// Written by scripts/sync_audio.py. Each array holds segment-relative seconds: one
// entry for each reveal after the first, then the end of the segment.
const track: AudioTrack = {
	audio_file: "./audio/tracks/v1/track.mp3",
	length_s: 93.52,
	timing: {
		perSegment: {
			intro: [4.1833, 11.35, 14.3667],
			setup: [4.0667, 6.5],
			fault: [2.1833, 7.8167, 11.1],
			triage: [2.2333, 10.1167],
			diagnosis: [4.7, 6.9667, 11.4333],
			patch: [2.8167, 5.6667, 11.4],
			sandbox: [6.4, 10.9667],
			pr: [7.9833, 10.6167],
			outro: [3.85, 7.4167],
		},
	},
	audio_plan_path: "../../audio_plan.md",
	plan_snapshot_path: "./plan_snapshot.md",
	created_at: "2026-10-07T13:50:31Z",
};

export default track;
