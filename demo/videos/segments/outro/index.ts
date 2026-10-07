import { defineScene } from "../../components/scene.js";
import logoUrl from "../../videos/demo/assets/mender-logo.png";

// 25 s is the pipeline time of this run: triage 2.8 s, diagnosis 15.3 s, patch 6.2 s,
// verify 0.6 s. It starts when the evidence is collected.
export default defineScene({
	id: "outro",
	advances: [3.85, 7.4167],
	voiceover:
		"From evidence to a verified fix in twenty-five seconds. Mender. It never merges without you.",
	html: `
		<div class="mender-scene">
			<div class="stage split">
				<div class="hero-stat" data-beat="0">
					<div class="stat-value"><em>25 s</em></div>
					<div class="lede">pipeline time of this run: from collected evidence to a verified, prepared pull request</div>
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
	`,
});
