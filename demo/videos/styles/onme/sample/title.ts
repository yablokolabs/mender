import { defineSegment } from "videowright";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "onme-sample-title",
	advances: [2.6, 4.2],
	voiceover:
		"OnMe — see the outfit on you. Your photo, your outfit, and the result keeps your face, your hair and your light exactly as they are.",

	mount(el) {
		host = el;
		el.innerHTML = `
      <style>
        .onme-title {
          position: relative;
          height: 100%;
          background: var(--color-bg);
          color: var(--color-fg);
          font-family: var(--font-display);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: var(--safe-y) var(--safe-x);
        }
        .onme-title .halo {
          position: absolute;
          right: -240px;
          top: 50%;
          width: 1100px;
          height: 1100px;
          transform: translateY(-50%);
          background: radial-gradient(circle, rgba(232, 96, 176, 0.16) 0%, rgba(232, 96, 176, 0) 62%);
          pointer-events: none;
        }
        .onme-title .eyebrow {
          font-family: var(--font-body);
          font-size: 26px;
          font-weight: 500;
          letter-spacing: 0.32em;
          text-transform: uppercase;
          color: var(--color-faint);
          opacity: 0;
        }
        .onme-title h1 {
          margin: 36px 0 0;
          font-size: 168px;
          font-weight: 600;
          letter-spacing: -0.03em;
          line-height: 1.02;
          opacity: 0;
        }
        .onme-title .underline {
          margin-top: 22px;
          width: 340px;
          height: 10px;
          border-radius: var(--radius-pill);
          background: var(--color-accent);
          box-shadow: var(--halo);
          transform: scaleX(0);
          transform-origin: left center;
        }
        .onme-title .tagline {
          margin-top: 40px;
          font-family: var(--font-body);
          font-size: 42px;
          font-weight: 400;
          color: var(--color-muted);
          opacity: 0;
        }
      </style>
      <div class="onme-title">
        <div class="halo"></div>
        <div class="eyebrow" data-ref="eyebrow">OnMe</div>
        <h1 data-ref="headline">See it on you.</h1>
        <div class="underline" data-ref="underline"></div>
        <div class="tagline" data-ref="tagline">Your photo. Your outfit. Your face — unchanged.</div>
      </div>
    `;
	},

	async play(ctx) {
		const ease = "cubic-bezier(0.22, 1, 0.36, 1)";
		const eyebrow = host?.querySelector('[data-ref="eyebrow"]') as HTMLElement;
		const headline = host?.querySelector('[data-ref="headline"]') as HTMLElement;
		const underline = host?.querySelector('[data-ref="underline"]') as HTMLElement;
		const tagline = host?.querySelector('[data-ref="tagline"]') as HTMLElement;

		eyebrow.animate([{ opacity: 0 }, { opacity: 1 }], {
			duration: 420,
			easing: ease,
			fill: "forwards",
		});

		headline.animate(
			[
				{ opacity: 0, transform: "translateY(32px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 600, delay: 160, easing: ease, fill: "forwards" },
		);

		underline.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], {
			duration: 480,
			delay: 680,
			easing: ease,
			fill: "forwards",
		});

		tagline.animate(
			[
				{ opacity: 0, transform: "translateY(20px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 520, delay: 900, easing: ease, fill: "forwards" },
		);

		await ctx.waitForNext();
		await ctx.hold(800);
	},

	unmount() {
		host = null;
	},
});
