import { defineSegment } from "videowright";
import "../../components/scene.css";
import { fontsReady, pipeline, playBeats } from "../../components/scene.js";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "sandbox",
	advances: [5.45, 9.95],
	voiceover:
		"Before anything is proposed, the patch runs in a Docker container with no network. Twenty-one of twenty-one checks pass, on the first attempt.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<header data-beat="0">
					<div class="kicker">Verify</div>
					<h1 class="headline">Tested with <em>no network</em></h1>
				</header>
				<div class="stage">
					<div class="terminal" data-beat="0">
						<div class="prompt">docker run --rm --network none --memory 1g --cpus 2 \\</div>
						<div>    mender-demo-test:latest python3 demo/app/check.py</div>
						<div class="dim" data-beat="1">PASS check_memory_limit</div>
						<div class="dim" data-beat="1">PASS check_cpu_limit_present</div>
						<div class="dim" data-beat="1">PASS check_cpu_request_sane</div>
						<div class="dim" data-beat="1">... 18 more</div>
						<div class="ok strong" data-beat="1">21/21 checks passed</div>
					</div>
					<div class="row" data-beat="1">
						<span class="chip accent">passed on attempt 1</span><span class="chip">0.6 s</span>
					</div>
				</div>
				${pipeline(4)}
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
