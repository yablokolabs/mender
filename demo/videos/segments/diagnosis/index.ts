import { defineSegment } from "videowright";
import "../../components/scene.css";
import { fontsReady, pipeline, playBeats } from "../../components/scene.js";

let host: HTMLElement | null = null;

// The three sources that the committed root-cause report cites as [1], [6] and [11].
const citations = [
	["[1]", "devopsboys.com", "Kubernetes CrashLoopBackOff After Changing Resource Limits"],
	["[6]", "medium.com", "Why Pods Get OOMKilled in Kubernetes"],
	["[11]", "cast.ai", "OOMKilled (Exit Code 137): Causes and How to Fix It"],
]
	.map(
		([number, site, title]) => `
			<div class="cite" data-beat="2">
				<span class="num">${number}</span><span class="host">${site}</span>
				<span class="title">${title}</span>
			</div>`,
	)
	.join("");

export default defineSegment({
	id: "diagnosis",
	advances: [4.6667, 7, 11.2333],
	voiceover:
		"The ultra model plans three web searches, runs them through Tavily, and writes the root cause report. The report carries numbered citations that a reviewer can open.",

	async mount(el) {
		host = el;
		el.innerHTML = `
			<div class="mender-scene">
				<header data-beat="0">
					<div class="kicker">Root cause</div>
					<h1 class="headline">Search the web, then <em>cite it</em></h1>
				</header>
				<div class="stage narrow-wide">
					<div class="panel" data-beat="0">
						<div class="panel-title">Tavily web search</div>
						<div class="row">
							<div><div class="stat-value">3</div><div class="stat-label">queries</div></div>
							<div><div class="stat-value">15</div><div class="stat-label">sources</div></div>
						</div>
						<div class="query">"Kubernetes OOMKilled CrashLoopBackOff memory limit 64Mi insufficient startup cache 96Mi"</div>
					</div>
					<div class="panel accent" data-beat="1">
						<div class="panel-title">root cause report · ultra tier</div>
						<div class="report-title">checkout pod OOMKilled due to 64Mi memory limit below 96Mi startup cache requirement</div>
						<div class="row"><span class="chip accent">confidence 0.98</span></div>
						<div class="cites">${citations}</div>
					</div>
				</div>
				${pipeline(2)}
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
