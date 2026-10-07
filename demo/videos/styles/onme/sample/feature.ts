import { defineSegment } from "videowright";

let host: HTMLElement | null = null;

export default defineSegment({
	id: "onme-sample-feature",
	advances: [1.8, 3.6, 5.4, 7.0],
	voiceover:
		"Your face stays yours — identity, hair and skin tone are preserved. There are no prompts to write. And nothing is kept on the server when the request ends.",

	mount(el) {
		host = el;
		el.innerHTML = `
      <style>
        .onme-feature {
          position: relative;
          height: 100%;
          background: var(--color-bg);
          color: var(--color-fg);
          font-family: var(--font-body);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: var(--safe-y) var(--safe-x);
        }
        .onme-feature .halo {
          position: absolute;
          left: -260px;
          top: 40%;
          width: 1000px;
          height: 1000px;
          background: radial-gradient(circle, rgba(232, 96, 176, 0.12) 0%, rgba(232, 96, 176, 0) 60%);
          pointer-events: none;
        }
        .onme-feature .row {
          display: grid;
          grid-template-columns: 160px 1fr;
          align-items: baseline;
          gap: 40px;
          padding: 44px 0;
          border-bottom: 1px solid var(--color-border);
          width: 88%;
        }
        .onme-feature .row:last-of-type {
          border-bottom: none;
        }
        .onme-feature .num {
          font-family: var(--font-display);
          font-size: 56px;
          font-weight: 600;
          color: var(--color-accent);
        }
        .onme-feature .claim {
          font-family: var(--font-display);
          font-size: 62px;
          font-weight: 600;
          letter-spacing: -0.02em;
          line-height: 1.1;
          opacity: 0;
        }
        .onme-feature .detail {
          margin-top: 12px;
          font-size: 34px;
          color: var(--color-muted);
          opacity: 0;
        }
      </style>
      <div class="onme-feature">
        <div class="halo"></div>
        <div class="row">
          <div class="num">01</div>
          <div>
            <div class="claim" data-ref="claim-1">Your face stays yours.</div>
            <div class="detail" data-ref="detail-1">Identity, hair and skin tone preserved.</div>
          </div>
        </div>
        <div class="row">
          <div class="num">02</div>
          <div>
            <div class="claim" data-ref="claim-2">No prompts to write.</div>
            <div class="detail" data-ref="detail-2">Two photos and one tap.</div>
          </div>
        </div>
        <div class="row">
          <div class="num">03</div>
          <div>
            <div class="claim" data-ref="claim-3">Nothing kept on the server.</div>
            <div class="detail" data-ref="detail-3">Photos live for one request, then they are gone.</div>
          </div>
        </div>
      </div>
    `;
	},

	async play(ctx) {
		const ease = "cubic-bezier(0.22, 1, 0.36, 1)";

		const reveal = (index: number) => {
			const claim = host?.querySelector(`[data-ref="claim-${index}"]`) as HTMLElement;
			const detail = host?.querySelector(`[data-ref="detail-${index}"]`) as HTMLElement;
			claim.animate(
				[
					{ opacity: 0, transform: "translateY(28px)" },
					{ opacity: 1, transform: "translateY(0)" },
				],
				{ duration: 520, easing: ease, fill: "forwards" },
			);
			detail.animate([{ opacity: 0 }, { opacity: 1 }], {
				duration: 440,
				delay: 200,
				easing: ease,
				fill: "forwards",
			});
		};

		reveal(1);
		await ctx.waitForNext();
		reveal(2);
		await ctx.waitForNext();
		reveal(3);
		await ctx.waitForNext();
		await ctx.hold(400);
	},

	unmount() {
		host = null;
	},
});
