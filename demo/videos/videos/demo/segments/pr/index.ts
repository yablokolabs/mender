import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'pr',
  advances: [5.5],
  voiceover: "Mender opens a pull request: root cause, evidence, the diff, the test results, and the Tavily sources. A human reviews and merges. Mender never merges.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow">Step 7 — Prepared PR</div>
        <h2 class="head">Fix checkout: OOMKilled by memory limit</h2>
        <div class="prbody">
          <div class="block"><div class="bh">## Root cause</div><div>limit 64Mi below heap 96Mi [1]</div></div>
          <div class="block"><div class="bh">## Sandbox test results</div><div>**PASSED** in 1 attempt(s)</div></div>
          <div class="block"><div class="bh">## Tavily sources used</div><div>[1] CrashLoopBackOff — OOMKilled</div><div>[2] Memory limits and OOM behavior</div></div>
          <div class="block review">Opened by Mender for human review. Do not auto-merge.</div>
        </div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const prbody = el.querySelector('.prbody') as HTMLElement;
    [head, prbody].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    prbody.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    prbody.style.opacity = '1'; prbody.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    const blocks = prbody.querySelectorAll('.block');
    for (const b of blocks) {
      (b as HTMLElement).style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      (b as HTMLElement).style.transform = 'translateX(0)';
      (b as HTMLElement).style.opacity = '1';
      await ctx.waitForNext();
    }
    await ctx.hold(900);
  },
});
