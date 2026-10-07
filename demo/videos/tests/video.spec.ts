// These tests drive the real videowright player in a browser. `videowright render`
// exits 0 even when a segment throws, so the render alone cannot prove the video.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, type Page, test } from "@playwright/test";
import type { AudioTrack } from "videowright";

declare global {
	interface Window {
		__VW_PLAYER_READY__: boolean;
		__VW_SEGMENT_ADVANCES__: Record<string, number[]>;
	}
}

const projectRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const videoFolder = join(projectRoot, "videos", "demo");
const trackModule = join(videoFolder, "audio", "tracks", "v1", "track.ts");
const renderedVideo = join(projectRoot, "..", "mender-demo.mp4");
const segmentIds = readdirSync(join(projectRoot, "segments"), {
	withFileTypes: true,
})
	.filter((entry) => entry.isDirectory())
	.map((entry) => entry.name);

const MIN_FONT_PX = 20;

async function loadTrack(): Promise<AudioTrack> {
	expect(
		existsSync(trackModule),
		`audio track is missing: ${trackModule}`,
	).toBe(true);
	const module = (await import(trackModule)) as { default: AudioTrack };
	return module.default;
}

function timelineSeconds(track: AudioTrack): number {
	return Object.values(track.timing.perSegment).reduce(
		(total, advances) => total + (advances?.at(-1) ?? 0),
		0,
	);
}

function probe(file: string): {
	duration: number;
	streams: Record<string, string>[];
} {
	const output = execFileSync("ffprobe", [
		"-v",
		"error",
		"-show_entries",
		"format=duration:stream=codec_type,codec_name,width,height",
		"-of",
		"json",
		file,
	]);
	const result = JSON.parse(output.toString()) as {
		format: { duration: string };
		streams: Record<string, string>[];
	};
	return { duration: Number(result.format.duration), streams: result.streams };
}

function collectProblems(page: Page): string[] {
	const problems: string[] = [];
	page.on("pageerror", (error) =>
		problems.push(`page error: ${error.message}`),
	);
	page.on("console", (message) => {
		if (message.type() === "error")
			problems.push(`console error: ${message.text()}`);
	});
	page.on("requestfailed", (request) =>
		problems.push(`request failed: ${request.url()}`),
	);
	page.on("response", (response) => {
		if (response.status() >= 400)
			problems.push(`HTTP ${response.status()}: ${response.url()}`);
	});
	return problems;
}

function playerStatus(page: Page): Promise<string> {
	return page.evaluate(
		() => `${document.body.dataset.vwSegment}:${document.body.dataset.vwState}`,
	);
}

async function animationsToFinish(page: Page): Promise<void> {
	await page.evaluate(() =>
		Promise.all(
			document
				.getAnimations()
				.map((animation) => animation.finished.catch(() => null)),
		),
	);
}

/** Looks at the segment that is on the frame and reports what a viewer cannot read. */
function inspectFrame(page: Page, minFontPx: number) {
	return page.evaluate((minFont) => {
		const frame = document.getElementById("player-host") as HTMLElement;
		const bounds = frame.getBoundingClientRect();
		const slot = [...document.querySelectorAll<HTMLElement>(".vw-slot")].find(
			(candidate) => candidate.style.visibility !== "hidden",
		);
		const label = (element: Element) =>
			`<${element.tagName.toLowerCase()} class="${element.getAttribute("class") ?? ""}"> ` +
			(element.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 50);
		const invisible: string[] = [];
		const outsideFrame: string[] = [];
		const clipped: string[] = [];
		const tooSmall: string[] = [];
		const elements =
			slot?.querySelectorAll<HTMLElement>(".vw-slot-content *") ?? [];
		for (const element of elements) {
			if (
				element.tagName === "STYLE" ||
				element.closest("[aria-hidden='true']")
			)
				continue;
			const style = getComputedStyle(element);
			if (
				style.opacity === "0" ||
				style.visibility === "hidden" ||
				style.display === "none"
			) {
				invisible.push(label(element));
				continue;
			}
			const box = element.getBoundingClientRect();
			if (box.width === 0 || box.height === 0) continue;
			if (
				box.left < bounds.left - 1 ||
				box.top < bounds.top - 1 ||
				box.right > bounds.right + 1 ||
				box.bottom > bounds.bottom + 1
			) {
				outsideFrame.push(label(element));
			}
			if (
				style.overflow !== "visible" &&
				(element.scrollWidth > element.clientWidth + 1 ||
					element.scrollHeight > element.clientHeight + 1)
			) {
				clipped.push(label(element));
			}
			const hasOwnText = [...element.childNodes].some(
				(node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim(),
			);
			if (hasOwnText && Number.parseFloat(style.fontSize) < minFont) {
				tooSmall.push(`${label(element)} (${style.fontSize})`);
			}
		}
		return {
			elementCount: elements.length,
			invisible,
			outsideFrame,
			clipped,
			tooSmall,
		};
	}, minFontPx);
}

for (const id of segmentIds) {
	test(`${id}: every beat plays and all content can be read on the frame`, async ({
		page,
	}) => {
		const problems = collectProblems(page);
		await page.goto(`/video/demo?hideHud=1#/${id}/0`);
		await page.waitForFunction(() => window.__VW_PLAYER_READY__ === true);
		await animationsToFinish(page);
		expect(await playerStatus(page)).toBe(`${id}:playing`);

		const advances = await page.evaluate(() => window.__VW_SEGMENT_ADVANCES__);
		const order = Object.keys(advances);
		const presses = advances[id].length;
		const track = await loadTrack();
		expect(
			track.timing.perSegment[id],
			"audio track timing and segment advances",
		).toEqual(advances[id]);

		for (let press = 1; press < presses; press++) {
			await page.keyboard.press("ArrowRight");
			await animationsToFinish(page);
			expect(
				await playerStatus(page),
				`after press ${press} of ${presses}`,
			).toBe(`${id}:playing`);
		}

		const frame = await inspectFrame(page, MIN_FONT_PX);
		expect(frame.elementCount, "elements on the frame").toBeGreaterThan(0);
		expect(
			frame.invisible,
			"content that is still invisible at the last beat",
		).toEqual([]);
		expect(frame.outsideFrame, "content outside the 1920x1080 frame").toEqual(
			[],
		);
		expect(frame.clipped, "content cut off by its container").toEqual([]);
		expect(frame.tooSmall, `text smaller than ${MIN_FONT_PX}px`).toEqual([]);

		await page.keyboard.press("ArrowRight");
		const next = order[order.indexOf(id) + 1];
		await expect
			.poll(() => playerStatus(page), {
				message: `press ${presses} must end the segment`,
			})
			.toBe(next ? `${next}:playing` : `${id}:ended`);
		expect(problems).toEqual([]);
	});
}

test("the timeline is as long as the narration, so no words are cut", async () => {
	const track = await loadTrack();
	const narration = probe(join(videoFolder, track.audio_file)).duration;
	const timeline = timelineSeconds(track);
	expect(timeline).toBeGreaterThanOrEqual(narration);
	expect(timeline).toBeLessThanOrEqual(narration + 1);
});

test("the committed MP4 is the 1080p render of this timeline, with the narration", async () => {
	const video = probe(renderedVideo);
	const kinds = video.streams.map((stream) => stream.codec_type);
	expect(kinds).toContain("audio");
	expect(
		video.streams.find((stream) => stream.codec_type === "video"),
	).toMatchObject({
		width: 1920,
		height: 1080,
	});
	expect(video.duration).toBeCloseTo(timelineSeconds(await loadTrack()), 1);
});
