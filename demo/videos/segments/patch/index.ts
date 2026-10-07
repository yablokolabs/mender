import { defineSegment } from "videowright";
import "../../components/scene.css";
import { checkIcon, fontsReady, pipeline, playBeats } from "../../components/scene.js";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "patch",
	advances: [2.7, 5.8667, 11.4833],
	voiceover:
		"The super model then writes the patch. It can only touch the files it was given. Here, it raises the memory limit back to five hundred and twelve megabytes.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<header data-beat="0">
					<div class="kicker">Patch</div>
					<h1 class="headline">One file. <em>One fix.</em></h1>
				</header>
				<div class="stage">
					<div class="row" data-beat="0">
						<span class="chip">super tier</span><span class="chip">6.2 s</span><span class="chip">$0.0046</span>
					</div>
					<div class="row" data-beat="1">
						<span class="chip accent">${checkIcon}allowed file</span>
						<span class="mono">demo/manifests/deploy.yaml</span>
						<span class="dim">any other path is rejected</span>
					</div>
					<div class="terminal" data-beat="2">
						<div class="dim">demo/manifests/deploy.yaml</div>
						<div>  limits:</div>
						<div>    cpu: "1"</div>
						<div class="del">-   memory: 64Mi</div>
						<div class="add">+   memory: 512Mi</div>
					</div>
				</div>
				${pipeline(3)}
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
