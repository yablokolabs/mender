import { defineSegment } from 'videowright';

export default defineSegment({
  id: 'fault',
  advances: [4.5],
  voiceover: "Then we inject a fault: a memory limit too low for the heap. Pods start OOM-killing.",

  mount(el, ctx) {
    el.innerHTML = `
      <div class="beat">
        <div class="eyebrow red">Step 2 — Inject a fault</div>
        <h2 class="head">low-memory-limit</h2>
        <div class="two">
          <div class="card bad"><div class="big">64 Mi</div><div class="lbl">container memory limit</div></div>
          <div class="card bad"><div class="big">96 Mi</div><div class="lbl">heap in practice</div></div>
        </div>
        <div class="code">$ python3 demo/inject.py low-memory-limit</div>
        <div class="alert">OOMKilled &rarr; CrashLoopBackOff</div>
      </div>
    `;
  },

  async play(ctx) {
    const head = el.querySelector('.head') as HTMLElement;
    const two = el.querySelector('.two') as HTMLElement;
    const code = el.querySelector('.code') as HTMLElement;
    const alert = el.querySelector('.alert') as HTMLElement;
    [head, two, code, alert].forEach((x) => { x!.style.opacity = '0'; x!.style.transform = 'translateY(16px)'; });

    head.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    head.style.opacity = '1'; head.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    two.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    two.style.opacity = '1'; two.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    code.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    code.style.opacity = '1'; code.style.transform = 'translateY(0)';
    await ctx.waitForNext();

    alert.style.transition = 'opacity 0.4s ease 0.2s, transform 0.4s ease 0.2s, background 0.4s';
    alert.style.opacity = '1'; alert.style.transform = 'translateY(0)';
    await ctx.waitForNext();
    await ctx.hold(900);
  },
});
