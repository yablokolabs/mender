import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'intro',
  advances: [4.5],
  voiceover: "Mender takes a broken Kubernetes service and returns a verified fix. Triage, root cause, patch, sandbox test, and a pull request a human reviews. Mender never merges anything itself.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="intro">
        <div class="logo-wrap"><img class="logo" src="/assets/mender-logo.png" alt="Mender"></div>
        <h1 class="title">Mender</h1>
        <p class="tagline">Kubernetes Incident-to-Fix Agent</p>
        <div class="pill">triage &rarr; root cause &rarr; patch &rarr; sandbox &rarr; PR</div>
        <div class="never">Mender never merges — a human reviews.</div>
      </div>
    `;
  },

  async play(ctx) {
    const host = el.querySelector('.intro') as HTMLElement;
    const logo = el.querySelector('.logo') as HTMLElement;
    const title = el.querySelector('.title') as HTMLElement;
    const tagline = el.querySelector('.tagline') as HTMLElement;
    const pill = el.querySelector('.pill') as HTMLElement;
    const never = el.querySelector('.never') as HTMLElement;
    const items = [logo, title, tagline, pill, never];
    items.forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(24px)'; });

    for (let i = 0; i < items.length; i++) {
      const el2 = items[i]!;
      el2.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      el2.style.opacity = '1';
      el2.style.transform = 'translateY(0)';
      await ctx.waitForNext();
    }
    await ctx.hold(1200);
  },
});
