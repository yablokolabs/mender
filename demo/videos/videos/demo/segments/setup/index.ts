import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'setup',
  advances: [4.5],
  voiceover: "We start from a kind cluster running the sample checkout service — 21 invariant checks pass.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow">Step 1 — Healthy baseline</div>
        <h2 class="head">kind cluster · checkout service · shop namespace</h2>
        <div class="grid">
          <div class="card"><div class="big">21</div><div class="lbl">invariant checks</div></div>
          <div class="card"><div class="big">3</div><div class="lbl">Nemotron tiers</div></div>
          <div class="card"><div class="big">23</div><div class="lbl">fault cases</div></div>
        </div>
        <div class="code">$ mender run --service checkout --namespace shop --pr-mode prepare</div>
      `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const grid = el.querySelector('.grid') as HTMLElement;
    const code = el.querySelector('.code') as HTMLElement;
    head.style.opacity = '0';
    grid.style.opacity = '0';
    code.style.opacity = '0';
    head.style.transform = 'translateY(16px)';
    grid.style.transform = 'translateY(16px)';
    code.style.transform = 'translateY(16px)';

    head.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
    head.style.opacity = '1';
    head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    grid.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
    grid.style.opacity = '1';
    grid.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    code.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
    code.style.opacity = '1';
    code.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(1000);
  },
});
