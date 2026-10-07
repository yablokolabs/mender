import { defineSegment } from "videowright";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "onme-sample-cta",
	advances: [2.8, 4.6],
	voiceover: "Upload a photo, pick an outfit, and see it on you. OnMe — see it on you.",

	mount(el) {
		host = el;
		el.innerHTML = `
      <style>
        .onme-cta {
          position: relative;
          height: 100%;
          background: var(--color-bg);
          color: var(--color-fg);
          font-family: var(--font-display);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 40px;
        }
        .onme-cta .halo {
          position: absolute;
          left: 50%;
          top: 50%;
          width: 1500px;
          height: 1500px;
          transform: translate(-50%, -50%);
          background: radial-gradient(circle, rgba(232, 96, 176, 0.18) 0%, rgba(232, 96, 176, 0) 58%);
          pointer-events: none;
        }
        .onme-cta .headline {
          font-size: 150px;
          font-weight: 600;
          letter-spacing: -0.03em;
          opacity: 0;
        }
        .onme-cta .sub {
          font-family: var(--font-body);
          font-size: 40px;
          color: var(--color-muted);
          opacity: 0;
        }
        .onme-cta .pill-wrap {
          position: relative;
          margin-top: 12px;
          opacity: 0;
        }
        .onme-cta .pill {
          position: relative;
          padding: 30px 84px;
          border-radius: var(--radius-pill);
          background: var(--color-accent);
          color: var(--color-on-accent);
          font-size: 40px;
          font-weight: 600;
        }
        .onme-cta .pill-halo {
          position: absolute;
          inset: -36px;
          border-radius: var(--radius-pill);
          background: radial-gradient(ellipse, rgba(232, 96, 176, 0.42) 0%, rgba(232, 96, 176, 0) 70%);
          opacity: 0;
          pointer-events: none;
        }
        .onme-cta .url {
          font-family: var(--font-mono);
          font-size: 24px;
          color: var(--color-faint);
          opacity: 0;
        }
      </style>
      <div class="onme-cta">
        <div class="halo"></div>
        <div class="headline" data-ref="headline">See it on you.</div>
        <div class="sub" data-ref="sub">Upload a photo. Pick an outfit. That's it.</div>
        <div class="pill-wrap" data-ref="pill-wrap">
          <div class="pill-halo" data-ref="pill-halo"></div>
          <div class="pill">Get OnMe</div>
        </div>
        <div class="url" data-ref="url">onme-dl.yablokolabs.com/OnMe-1.0.0.apk</div>
      </div>
    `;
	},

	async play(ctx) {
		const ease = "cubic-bezier(0.22, 1, 0.36, 1)";
		const headline = host?.querySelector('[data-ref="headline"]') as HTMLElement;
		const sub = host?.querySelector('[data-ref="sub"]') as HTMLElement;
		const pillWrap = host?.querySelector('[data-ref="pill-wrap"]') as HTMLElement;
		const pillHalo = host?.querySelector('[data-ref="pill-halo"]') as HTMLElement;
		const url = host?.querySelector('[data-ref="url"]') as HTMLElement;

		headline.animate(
			[
				{ opacity: 0, transform: "translateY(30px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 620, easing: ease, fill: "forwards" },
		);

		sub.animate(
			[
				{ opacity: 0, transform: "translateY(20px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 520, delay: 240, easing: ease, fill: "forwards" },
		);

		pillWrap.animate(
			[
				{ opacity: 0, transform: "translateY(18px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 520, delay: 520, easing: ease, fill: "forwards" },
		);

		pillHalo.animate([{ opacity: 0 }, { opacity: 0.85 }, { opacity: 0.45 }], {
			duration: 1800,
			delay: 640,
			easing: ease,
			fill: "forwards",
		});

		url.animate([{ opacity: 0 }, { opacity: 1 }], {
			duration: 440,
			delay: 860,
			easing: ease,
			fill: "forwards",
		});

		await ctx.waitForNext();
		await ctx.hold(700);
	},

	unmount() {
		host = null;
	},
});
