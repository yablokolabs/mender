import { defineSegment } from "videowright";
import "../../components/scene.css";
import { fontsReady, playBeats } from "../../components/scene.js";
import logoUrl from "../../videos/demo/assets/mender-logo.png";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "outro",
	advances: [4.7667, 8.4333],
	voiceover:
		"From broken service to a verified fix in twenty-five seconds. Mender. It never merges without you.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<div class="stage split">
					<div class="hero-stat" data-beat="0">
						<div class="stat-value"><em>25 s</em></div>
						<div class="lede">from a broken service to a verified, prepared pull request</div>
					</div>
					<div class="panel" data-beat="0">
						<div class="panel-title">23-fault evaluation · 2026-10-06</div>
						<div class="eval-rows">
							<span class="value">20/23</span><span class="label">fixes passed the sandbox tests</span>
							<span class="value">9/23</span><span class="label">root causes matched by strict label</span>
							<span class="value">33.8 s</span><span class="label">median time to a prepared PR</span>
						</div>
					</div>
				</div>
				<div class="closing" data-beat="1">
					<img class="logo small" src="${logoUrl}" alt="">
					<div class="wordmark small">Mender</div>
					<div class="promise">It never merges without you.</div>
					<div class="repo">github.com/yablokolabs/mender</div>
				</div>
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
