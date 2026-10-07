import "../../styles/mender/tokens.css";
import type { Timeline } from "videowright";
import defaultAudioTrack from "./audio/tracks/v1/track.js";

const timeline: Timeline = {
	meta: {
		title: "Mender demo: from a broken service to a verified pull request",
	},
	segments: [
		{ id: "intro" },
		{ id: "setup", transition: "fade" },
		{ id: "fault", transition: "fade" },
		{ id: "triage", transition: "fade" },
		{ id: "diagnosis", transition: "fade" },
		{ id: "patch", transition: "fade" },
		{ id: "sandbox", transition: "fade" },
		{ id: "pr", transition: "fade" },
		{ id: "outro", transition: "fade" },
	],
	default_audio_track: defaultAudioTrack,
};

export default timeline;
