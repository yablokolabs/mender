import { defineScene, pipeline } from "../../components/scene.js";

export default defineScene({
	id: "setup",
	advances: [4.0667, 6.5],
	voiceover:
		"We start with a healthy checkout service on a local cluster. All twenty-one checks pass.",
	html: `
		<div class="mender-scene">
			<header data-beat="0">
				<div class="kicker">The starting point</div>
				<h1 class="headline">A <em>healthy</em> service</h1>
			</header>
			<div class="stage split">
				<div class="panel" data-beat="0">
					<div class="panel-title">kind cluster</div>
					<div class="facts">
						<span class="dim">namespace</span><span class="mono">shop</span>
						<span class="dim">service</span><span class="mono">checkout</span>
						<span class="dim">memory limit</span><span class="mono">512Mi</span>
						<span class="dim">pods</span><span class="mono ok">Running</span>
					</div>
				</div>
				<div class="terminal" data-beat="1">
					<div class="prompt">python3 demo/app/check.py</div>
					<div class="dim">PASS check_memory_limit</div>
					<div class="dim">PASS check_cpu_limit_present</div>
					<div class="dim">PASS check_cpu_request_sane</div>
					<div class="dim">... 18 more</div>
					<div class="ok strong">21/21 checks passed</div>
				</div>
			</div>
			${pipeline(-1)}
		</div>
	`,
});
