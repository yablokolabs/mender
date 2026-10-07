import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'sandbox',
  advances: [4.5],
  voiceover: "Before anything is committed, the patch is tested in an isolated Docker container with no network. The tests pass.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow green">Step 6 — Sandbox verification</div>
        <h2 class="head">docker run --rm --network none</h2>
        <div class="code">$ python3 demo/app/check.py<br><span class="ok">3 passed · 0 failed</span></div>
        <div class="badge">sandbox PASSED</div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const code = el.querySelector('.code') as HTMLElement;
    const badge = el.querySelector('.badge') as HTMLElement;
    [head, code, badge].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    code.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    code.style.opacity = '1'; code.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    badge.style.transition = 'opacity 0.4s ease, transform 0.4s ease, background 0.4s';
    badge.style.opacity = '1'; badge.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(900);
  },
});
