import type { PlayerContext } from "videowright";

const EASE_OUT = "cubic-bezier(0.22, 1, 0.36, 1)";
const REVEAL_MS = 500;
const STAGGER_MS = 90;

const FONT_FACES = [
	'400 36px "Inter"',
	'500 36px "Inter"',
	'600 36px "Inter"',
	'700 36px "Inter"',
	'400 32px "JetBrains Mono"',
	'500 32px "JetBrains Mono"',
];

const STAGES = [
	"Evidence",
	"Triage",
	"Root cause",
	"Patch",
	"Verify",
	"Pull request",
];

/** Resolves when each font face of the style is loaded, so no frame shows a fallback font. */
export function fontsReady(): Promise<unknown> {
	return Promise.all(FONT_FACES.map((face) => document.fonts.load(face)));
}

function revealBeat(root: HTMLElement, beat: number): void {
	const elements = root.querySelectorAll<HTMLElement>(`[data-beat="${beat}"]`);
	elements.forEach((element, index) => {
		// element.animate() is the only animation that the render clock drives.
		element.animate(
			[
				{ opacity: 0, transform: "translateY(24px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{
				duration: REVEAL_MS,
				delay: index * STAGGER_MS,
				easing: EASE_OUT,
				fill: "forwards",
			},
		);
	});
}

/**
 * Plays a scene whose elements carry `data-beat="0"`, `data-beat="1"` and so on.
 * Beat 0 shows at once. Each later beat waits for the next advance, so a scene with
 * beats 0 to N needs N + 1 entries in `advances`: N reveals and the end of the segment.
 */
export async function playBeats(
	ctx: PlayerContext,
	root: HTMLElement,
): Promise<void> {
	const beats = [...root.querySelectorAll<HTMLElement>("[data-beat]")].map(
		(element) => Number(element.dataset.beat),
	);
	revealBeat(root, 0);
	for (let beat = 1; beat <= Math.max(...beats); beat++) {
		await ctx.waitForNext();
		revealBeat(root, beat);
	}
}

/**
 * The six pipeline stages as a footer bar, with stage `active` (0 to 5) highlighted.
 * Two bars in one `.pipeline-stack` occupy the same place, so a later beat can move
 * the highlight.
 */
export function pipeline(active: number, beat = 0): string {
	const steps = STAGES.map((name, index) => {
		const state = index === active ? " active" : index < active ? " done" : "";
		return `<div class="step${state}">${name}</div>`;
	}).join("");
	return `<div class="pipeline" data-beat="${beat}">${steps}</div>`;
}

function icon(path: string): string {
	return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

export const checkIcon = icon("M4 12.5 9.5 18 20 6.5");
export const arrowIcon = icon("M3 12h17m-6-6.5 6.5 6.5-6.5 6.5");
