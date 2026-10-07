import { defineSegment } from "videowright";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "onme-sample-ui-showcase",
	advances: [3.0, 4.8],
	voiceover:
		"The app is two photos and one button. Your photo on the left, the outfit on the right, and Style me does the rest — no prompts, no sliders.",

	mount(el) {
		host = el;
		el.innerHTML = `
      <style>
        .onme-ui {
          position: relative;
          height: 100%;
          background: var(--color-bg);
          color: var(--color-fg);
          font-family: var(--font-body);
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .onme-ui .halo {
          position: absolute;
          left: 50%;
          top: 50%;
          width: 1300px;
          height: 1300px;
          transform: translate(-50%, -50%);
          background: radial-gradient(circle, rgba(232, 96, 176, 0.14) 0%, rgba(232, 96, 176, 0) 60%);
          pointer-events: none;
        }
        .onme-ui .phone {
          position: relative;
          width: 520px;
          height: 960px;
          border-radius: 48px;
          border: 2px solid var(--color-border-strong);
          background: var(--color-bg-elevated);
          box-shadow: var(--shadow-panel), var(--halo-soft);
          padding: 40px 36px;
          display: flex;
          flex-direction: column;
          opacity: 0;
        }
        .onme-ui .wordmark {
          font-family: var(--font-display);
          font-size: 34px;
          font-weight: 600;
          color: var(--color-fg);
        }
        .onme-ui .screen-title {
          margin-top: 10px;
          font-family: var(--font-display);
          font-size: 44px;
          font-weight: 600;
          letter-spacing: -0.02em;
        }
        .onme-ui .cards {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-top: 34px;
        }
        .onme-ui .card {
          border-radius: var(--radius-lg);
          border: 1.5px dashed var(--color-border-strong);
          background: var(--color-bg-element);
          aspect-ratio: var(--portrait-ratio);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 14px;
          opacity: 0;
        }
        .onme-ui .card .plus {
          width: 64px;
          height: 64px;
          border-radius: var(--radius-pill);
          background: var(--color-bg-selected);
          color: var(--color-accent-strong);
          font-size: 44px;
          line-height: 64px;
          text-align: center;
          font-weight: 400;
        }
        .onme-ui .card .label {
          font-size: 26px;
          color: var(--color-muted);
        }
        .onme-ui .cta {
          position: relative;
          margin-top: auto;
          height: 108px;
          border-radius: var(--radius-pill);
          background: var(--color-accent);
          color: var(--color-on-accent);
          font-family: var(--font-display);
          font-size: 38px;
          font-weight: 600;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
        }
        .onme-ui .cta-halo {
          position: absolute;
          inset: -28px;
          border-radius: var(--radius-pill);
          background: radial-gradient(ellipse, rgba(232, 96, 176, 0.38) 0%, rgba(232, 96, 176, 0) 70%);
          opacity: 0;
          pointer-events: none;
        }
        .onme-ui .hint {
          margin-top: 22px;
          text-align: center;
          font-size: 24px;
          color: var(--color-faint);
          opacity: 0;
        }
        .onme-ui .lower-third {
          position: absolute;
          left: var(--safe-x);
          bottom: var(--safe-y);
          font-size: 24px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          color: var(--color-faint);
          opacity: 0;
        }
      </style>
      <div class="onme-ui">
        <div class="halo"></div>
        <div class="phone" data-ref="phone">
          <div class="wordmark">OnMe</div>
          <div class="screen-title">See it on you</div>
          <div class="cards">
            <div class="card" data-ref="card-a">
              <div class="plus">+</div>
              <div class="label">Your photo</div>
            </div>
            <div class="card" data-ref="card-b">
              <div class="plus">+</div>
              <div class="label">The outfit</div>
            </div>
          </div>
          <div class="cta" data-ref="cta">
            <div class="cta-halo" data-ref="cta-halo"></div>
            Style me
          </div>
          <div class="hint" data-ref="hint">No prompts. No settings.</div>
        </div>
        <div class="lower-third" data-ref="lower-third">The app — two photos, one button</div>
      </div>
    `;
	},

	async play(ctx) {
		const ease = "cubic-bezier(0.22, 1, 0.36, 1)";
		const phone = host?.querySelector('[data-ref="phone"]') as HTMLElement;
		const cardA = host?.querySelector('[data-ref="card-a"]') as HTMLElement;
		const cardB = host?.querySelector('[data-ref="card-b"]') as HTMLElement;
		const cta = host?.querySelector('[data-ref="cta"]') as HTMLElement;
		const ctaHalo = host?.querySelector('[data-ref="cta-halo"]') as HTMLElement;
		const hint = host?.querySelector('[data-ref="hint"]') as HTMLElement;
		const lowerThird = host?.querySelector('[data-ref="lower-third"]') as HTMLElement;

		phone.animate(
			[
				{ opacity: 0, transform: "translateY(36px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 620, easing: ease, fill: "forwards" },
		);

		lowerThird.animate([{ opacity: 0 }, { opacity: 1 }], {
			duration: 480,
			delay: 300,
			easing: ease,
			fill: "forwards",
		});

		for (const [i, card] of [cardA, cardB].entries()) {
			card.animate(
				[
					{ opacity: 0, transform: "translateY(24px)" },
					{ opacity: 1, transform: "translateY(0)" },
				],
				{ duration: 480, delay: 420 + i * 140, easing: ease, fill: "forwards" },
			);
		}

		cta.animate(
			[
				{ opacity: 0, transform: "translateY(20px)" },
				{ opacity: 1, transform: "translateY(0)" },
			],
			{ duration: 520, delay: 800, easing: ease, fill: "forwards" },
		);

		ctaHalo.animate([{ opacity: 0 }, { opacity: 0.9 }, { opacity: 0.5 }], {
			duration: 1600,
			delay: 900,
			easing: ease,
			fill: "forwards",
		});

		hint.animate([{ opacity: 0 }, { opacity: 1 }], {
			duration: 420,
			delay: 1150,
			easing: ease,
			fill: "forwards",
		});

		await ctx.waitForNext();
		await ctx.hold(600);
	},

	unmount() {
		host = null;
	},
});
