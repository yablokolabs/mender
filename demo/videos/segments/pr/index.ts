import { checkIcon, defineScene, pipeline } from "../../components/scene.js";

// The section headings of the committed pr-body.md, in order.
const sections = [
	"Root cause",
	"Mechanism",
	"Evidence relied on",
	"Change",
	"Sandbox test results",
	"Tavily sources used",
	"How this was verified",
]
	.map(
		(name) =>
			`<div class="pr-section" data-beat="0">${checkIcon}<span>${name}</span></div>`,
	)
	.join("");

export default defineScene({
	id: "pr",
	advances: [7.9833, 10.6167],
	voiceover:
		"Mender prepares the pull request: root cause, evidence, the diff, the test results, and the sources. A person reviews it and merges it.",
	html: `
		<div class="mender-scene">
			<header data-beat="0">
				<div class="kicker">Pull request</div>
				<h1 class="headline">Prepared for a <em>human</em></h1>
			</header>
			<div class="stage">
				<div class="panel" data-beat="0">
					<div class="panel-title">prepared pull request</div>
					<div class="pr-title">Fix checkout: checkout pod OOMKilled due to 64Mi memory limit below 96Mi startup cache ...</div>
					<div class="pr-sections">${sections}</div>
				</div>
				<div class="review" data-beat="1">Opened by Mender for human review. <em>Do not auto-merge.</em></div>
			</div>
			${pipeline(5)}
		</div>
	`,
});
