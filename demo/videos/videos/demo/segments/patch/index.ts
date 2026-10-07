import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'patch',
  advances: [4.5],
  voiceover: "The super tier writes a patch to the one file Mender is allowed to change.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow">Step 5 — Patch (super tier)</div>
        <h2 class="head">patch deploy.yaml — memory: 512Mi</h2>
        <div class="code"><span class="minus">-  memory: 64Mi</span><span class="plus">+  memory: 512Mi</span></div>
        <div class="rule">only files in the allowed set may change</div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const code = el.querySelector('.code') as HTMLElement;
    const rule = el.querySelector('.rule') as HTMLElement;
    [head, code, rule].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    code.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    code.style.opacity = '1'; code.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    rule.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    rule.style.opacity = '1'; rule.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(900);
  },
});
