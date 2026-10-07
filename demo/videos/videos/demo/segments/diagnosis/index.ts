import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'diagnosis',
  advances: [5.0],
  voiceover: "The ultra tier proposes web searches, runs them through Tavily, and writes a numbered root-cause report. Each citation is a real link a reviewer can check.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow">Step 4 — Root-cause diagnosis (ultra + Tavily)</div>
        <h2 class="head">root cause: OOMKilled by memory limit</h2>
        <div class="cites">
          <div class="cite"><span class="num">[1]</span><div class="ct"><div class="ct-title">CrashLoopBackOff — OOMKilled</div><div class="ct-url">docs.example/oom</div></div></div>
          <div class="cite"><span class="num">[2]</span><div class="ct"><div class="ct-title">Memory limits and OOM behavior</div><div class="ct-url">kubernetes.io/docs</div></div></div>
        </div>
        <div class="tier">ultra · root cause · Tavily citations [1] [2]</div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const cites = el.querySelector('.cites') as HTMLElement;
    const tier = el.querySelector('.tier') as HTMLElement;
    [head, cites, tier].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    cites.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    cites.style.opacity = '1'; cites.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    const cards = cites.querySelectorAll('.cite');
    for (const c of cards) {
      (c as HTMLElement).style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      (c as HTMLElement).style.transform = 'translateY(0)';
      (c as HTMLElement).style.opacity = '1';
      await ctx.waitForNext();
    }

    tier.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    tier.style.opacity = '1'; tier.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(800);
  },
});
