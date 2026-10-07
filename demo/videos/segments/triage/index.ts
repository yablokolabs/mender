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
	id: "triage",
	advances: [2.5333, 9.5833],
	voiceover:
		"Mender collects the evidence. The nano model cuts eleven thousand tokens of logs and events down to a short list of signals and suspects.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<header data-beat="0">
					<div class="kicker">Evidence and triage</div>
					<h1 class="headline">From noise to <em>signals</em></h1>
				</header>
				<div class="stage funnel">
					<div class="terminal" data-beat="0">
						<div class="panel-title">cluster evidence · 11,020 tokens in</div>
						<div>Reason: OOMKilled</div>
						<div>Exit Code: 137</div>
						<div>Limits: memory: 64Mi</div>
						<div class="dim">starting checkout service (..., cache=96Mi)</div>
					</div>
					<div class="funnel-arrow" data-beat="1" aria-hidden="true">${arrowIcon}</div>
					<div class="panel accent" data-beat="1">
						<div class="panel-title">nano tier</div>
						<div class="stat-value">666</div>
						<div class="stat-label">tokens out: signals and suspects</div>
						<div class="row">
							<span class="chip">2.8 s</span><span class="chip">$0.0008</span>
						</div>
					</div>
				</div>
				<div class="pipeline-stack">${pipeline(0)}${pipeline(1, 1)}</div>
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
