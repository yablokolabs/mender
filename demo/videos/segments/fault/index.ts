import { defineSegment } from "videowright";
import "../../components/scene.css";
import {
	arrowIcon,
	fontsReady,
	pipeline,
	playBeats,
} from "../../components/scene.js";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "fault",
	advances: [2.2833, 8.1, 10.95],
	voiceover:
		"Then we inject a fault. The memory limit drops to sixty-four megabytes, below what the service needs to start. The pod is killed, again and again.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<header data-beat="0">
					<div class="kicker danger">Inject a fault</div>
					<h1 class="headline">The memory limit is too low</h1>
				</header>
				<div class="stage">
					<div class="terminal" data-beat="0">
						<div class="prompt">python3 demo/inject.py low-memory-limit</div>
					</div>
					<div class="split-row">
						<div class="panel" data-beat="1">
							<div class="panel-title">container memory limit</div>
							<div class="stat-value limit-change">
								<span class="old">512Mi</span>${arrowIcon}<span class="bad">64Mi</span>
							</div>
						</div>
						<div class="panel" data-beat="1">
							<div class="panel-title">the service needs at startup</div>
							<div class="stat-value">96Mi</div>
						</div>
					</div>
					<div class="alert" data-beat="2">
						<span>OOMKilled</span><span class="dot" aria-hidden="true"></span>
						<span>exit code 137</span><span class="dot" aria-hidden="true"></span>
						<span>CrashLoopBackOff</span>
					</div>
				</div>
				${pipeline(-1)}
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
