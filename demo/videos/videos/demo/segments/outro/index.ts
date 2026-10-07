import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'outro',
  advances: [4.5],
  voiceover: "Mender — from broken service to verified fix, in minutes, with evidence.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="outro">
        <div class="logo-wrap"><img class="logo" src="/assets/mender-logo.png" alt="Mender"></div>
        <h1 class="title">Mender</h1>
        <p class="tagline">from broken service to verified fix, with evidence</p>
        <div class="stats">
          <div class="stat"><div class="big">9/23</div><div class="lbl">root cause</div></div>
          <div class="stat"><div class="big">20/23</div><div class="lbl">fix passed</div></div>
          <div class="stat"><div class="big">33.8s</div><div class="lbl">median to PR</div></div>
        </div>
        <div class="never">Never merges — a human reviews.</div>
        <div class="repo">github.com/yablokolabs/mender</div>
      </div>
    `;
  },

  async play(ctx) {
    const host = el.querySelector('.outro') as HTMLElement;
    const logo = el.querySelector('.logo') as HTMLElement;
    const title = el.querySelector('.title') as HTMLElement;
    const tagline = el.querySelector('.tagline') as HTMLElement;
    const stats = el.querySelector('.stats') as HTMLElement;
    const never = el.querySelector('.never') as HTMLElement;
    const repo = el.querySelector('.repo') as HTMLElement;
    const items = [logo, title, tagline, stats, never, repo];
    items.forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(24px)'; });

    for (let i = 0; i < items.length; i++) {
      const e = items[i]!;
      e.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      e.style.opacity = '1';
      e.style.transform = 'translateY(0)';
      await ctx.waitForNext();
    }
    await ctx.hold(1400);
  },
});
