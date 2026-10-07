import { arrowIcon, defineScene, pipeline } from "../../components/scene.js";

// The signals and suspects are the triage output of the eval run (triage.json).
const list = (items: string[]) =>
	items.map((item) => `<li>${item}</li>`).join("");

const signals = list([
	"OOMKilled exit code 137",
	"CrashLoopBackOff",
	"memory limit 64Mi below required 512Mi",
	"container restarts 4",
]);
const suspects = list([
	"memory limit (64Mi)",
	"resource requests/limits",
	"container memory constraints",
]);

export default defineScene({
	id: "triage",
	advances: [2.2333, 10.1167],
	voiceover:
		"Mender collects the evidence. The nano model reads about eleven thousand tokens of logs and events, and returns a short list of signals and suspects.",
	html: `
		<div class="mender-scene">
			<header data-beat="0">
				<div class="kicker">Evidence and triage</div>
				<h1 class="headline">From noise to <em>signals</em></h1>
			</header>
			<div class="stage funnel">
				<div class="terminal" data-beat="0">
					<div class="panel-title">nano prompt · 11,020 tokens in</div>
					<div>Reason: OOMKilled</div>
					<div>Exit Code: 137</div>
					<div>Limits: memory: 64Mi</div>
					<div class="dim">starting checkout service</div>
					<div class="dim">  (..., cache=96Mi)</div>
				</div>
				<div class="funnel-arrow" data-beat="1" aria-hidden="true">${arrowIcon}</div>
				<div class="panel accent" data-beat="1">
					<div class="panel-title">nano tier · 666 tokens out</div>
					<div class="list-title">4 signals</div>
					<ul class="findings">${signals}</ul>
					<div class="list-title">3 suspects</div>
					<ul class="findings">${suspects}</ul>
					<div class="row">
						<span class="chip">2.8 s</span><span class="chip">$0.0008</span>
					</div>
				</div>
			</div>
			<div class="pipeline-stack">${pipeline(0)}${pipeline(1, 1)}</div>
		</div>
	`,
});
