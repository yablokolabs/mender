import { defineScene, pipeline } from "../../components/scene.js";

// The three sources that the committed root-cause report cites as [1], [6] and [11].
const citations = [
	[
		"[1]",
		"devopsboys.com",
		"Kubernetes CrashLoopBackOff After Changing Resource Limits",
	],
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

export default defineScene({
	id: "diagnosis",
	advances: [4.7, 6.9667, 11.4333],
	voiceover:
		"The ultra model plans three web searches, runs them through Tavily, and writes the root cause report. The report carries numbered citations that a reviewer can open.",
	html: `
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
						<div><div class="stat-value">15</div><div class="stat-label">results</div></div>
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
	`,
});
