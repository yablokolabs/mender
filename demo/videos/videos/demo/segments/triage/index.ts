import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'triage',
  advances: [4.0],
  voiceover: "Mender collects the evidence and triage — the nano tier — cuts the noise down to signals and suspects.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow">Step 3 — Triage (nano tier)</div>
        <h2 class="head">signals &amp; suspects</h2>
        <div class="list">
          <div class="row"><span class="dot"></span> OOMKilled events in shop</div>
          <div class="row"><span class="dot"></span> restart count climbing</div>
          <div class="row"><span class="dot"></span> limit 64Mi under heap 96Mi</div>
        </div>
        <div class="tier">nano · triage · cheap &amp; high volume</div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const list = el.querySelector('.list') as HTMLElement;
    const tier = el.querySelector('.tier') as HTMLElement;
    [head, list, tier].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    const rows = list.querySelectorAll('.row');
    for (const row of rows) {
      (row as HTMLElement).style.transition = 'opacity 0.35s ease, transform 0.35s ease';
      (row as HTMLElement).style.opacity = '1';
      (row as HTMLElement).style.transform = 'translateX(0)';
      await ctx.waitForNext();
    }

    tier.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    tier.style.opacity = '1'; tier.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(800);
  },
});
