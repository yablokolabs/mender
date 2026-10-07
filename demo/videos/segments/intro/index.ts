import { arrowIcon, defineScene } from "../../components/scene.js";
import logoUrl from "../../videos/demo/assets/mender-logo.png";

const flowSteps = ["Root cause", "Patch", "Sandbox test", "Pull request"]
	.map((step) => `<div class="flow-step" data-beat="1">${step}</div>`)
	.join(
		`<div class="flow-arrow" data-beat="1" aria-hidden="true">${arrowIcon}</div>`,
	);

export default defineScene({
	id: "intro",
	advances: [4.1833, 11.35, 14.3667],
	voiceover:
		"Mender takes a broken Kubernetes service and returns a verified fix. It finds the root cause, writes a patch, tests it in a sandbox, and prepares a pull request for a human to review. Mender never merges anything itself.",
	html: `
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
	`,
});
