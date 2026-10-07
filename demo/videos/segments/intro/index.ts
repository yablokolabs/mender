import { defineSegment } from "videowright";
import "../../components/scene.css";
import { arrowIcon, fontsReady, playBeats } from "../../components/scene.js";
import logoUrl from "../../videos/demo/assets/mender-logo.png";

let host: HTMLElement | null = null;

const flowSteps = ["Root cause", "Patch", "Sandbox test", "Pull request"]
	.map((step) => `<div class="flow-step" data-beat="1">${step}</div>`)
	.join(
		`<div class="flow-arrow" data-beat="1" aria-hidden="true">${arrowIcon}</div>`,
	);

export default defineSegment({
	id: "intro",
	advances: [4.5667, 13.1667, 16.45],
	voiceover:
		"Mender takes a broken Kubernetes service and returns a verified fix. It finds the root cause, writes a patch, tests it in a sandbox, and prepares a pull request for a human to review. Mender never merges anything itself.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene centered">
				<div class="brand" data-beat="0">
					<img class="logo" src="${logoUrl}" alt="">
					<div>
						<div class="wordmark">Mender</div>
						<div class="lede">Kubernetes incident-to-fix agent</div>
					</div>
				</div>
				<div class="flow">${flowSteps}</div>
				<div class="promise" data-beat="2">A human reviews and merges. <em>Mender never merges.</em></div>
			</div>
		`;
		await fontsReady();
	},

	async play(ctx) {
		if (host) await playBeats(ctx, host);
	},

	unmount() {
		host = null;
	},
});
