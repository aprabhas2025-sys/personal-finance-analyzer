(() => {
'use strict';
const $ = s => document.querySelector(s);
const cvs = $('#sky'), ctx = cvs.getContext('2d');
const form = $('#form'), email = $('#email'), pw = $('#password'), confirm = $('#confirm'), confirmField = $('#confirm-field'), eye = $('#toggle'), btn = $('#submit');
const title = $('#title'), subtitle = $('#subtitle'), switchCopy = $('#switch-copy');
let mode = 'signin';
const back = $('#back'), serverErr = $('#server-err'), signupLink = $('#signup');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
let W, H, DPR;

/* ---------- Canvas + starfield ---------- */
const stars = [];
function resize() {
  DPR = Math.min(devicePixelRatio || 1, 2); W = innerWidth; H = innerHeight;
  cvs.width = W * DPR; cvs.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  stars.length = 0;
  for (let i = 0, n = Math.round(W * H / 9000); i < n; i++)
    stars.push({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 1.1 + .2, z: Math.random() * .9 + .1, vx: (Math.random() - .5) * .06, p: Math.random() * 6.28, s: .4 + Math.random() * 1.4 });
}
function drawStars(t) {
  ctx.fillStyle = '#cfe0ff';
  for (const s of stars) {
    if (!reduce) { s.x += s.vx * (1 + starBoost * 40); if (s.x < 0) s.x = W; else if (s.x > W) s.x = 0; }
    const tw = reduce ? .6 : .45 + .35 * Math.sin(t * .001 * s.s + s.p);
    ctx.globalAlpha = tw * .75;
    ctx.beginPath(); ctx.arc(s.x - par.x * s.z * 26, s.y - par.y * s.z * 26, s.r, 0, 6.283); ctx.fill();
  }
  ctx.globalAlpha = 1;
  if (!reduce && t > nextMeteor) {            // rare shooting star
    nextMeteor = t + 7000 + Math.random() * 9000; const a = .5 + Math.random() * .3;
    meteors.push({ x: W * .2 + Math.random() * W * .8, y: Math.random() * H * .4, vx: -Math.cos(a) * 9, vy: Math.sin(a) * 9, l: 0 });
  }
  for (let i = meteors.length - 1; i >= 0; i--) {
    const m = meteors[i]; m.x += m.vx; m.y += m.vy; const f = ++m.l / 70;
    if (f >= 1) { meteors.splice(i, 1); continue; }
    ctx.strokeStyle = `rgba(200,225,255,${(1 - f) * .5})`; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(m.x, m.y); ctx.lineTo(m.x - m.vx * 7, m.y - m.vy * 7); ctx.stroke();
  }
}

/* ---------- Caret tracking via hidden mirror element ----------
   A hidden div copies the input's typography, padding, border and width.
   We fill it with the text before the caret (dots for password), append a
   zero-width marker span, and read the marker's offset. Then we subtract
   input.scrollLeft and add the input's viewport rect to get screen coords. */
const mirror = document.createElement('div');
const mark = document.createElement('span');
mark.textContent = '\u200b';
mirror.setAttribute('aria-hidden', 'true');
mirror.style.cssText = 'position:fixed;left:-9999px;top:0;visibility:hidden;white-space:pre;overflow:hidden;pointer-events:none';
document.body.appendChild(mirror);
const COPY = ['fontFamily','fontSize','fontWeight','fontStyle','fontVariant','fontStretch','letterSpacing','wordSpacing','textTransform','textIndent','textAlign','lineHeight',
  'paddingTop','paddingRight','paddingBottom','paddingLeft','borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth','borderTopStyle','borderLeftStyle','boxSizing'];
let caretKey = '', caretCache = null;
function caretPoint(input) {
  const r = input.getBoundingClientRect();
  const pos = input.selectionStart ?? input.value.length;
  const key = [input.value, pos, input.type, input.scrollLeft, r.left, r.top, r.width, r.height].join('|');
  if (key === caretKey && caretCache) return caretCache;
  const cs = getComputedStyle(input);
  COPY.forEach(p => mirror.style[p] = cs[p]);
  mirror.style.width = input.offsetWidth + 'px';
  mirror.style.height = input.offsetHeight + 'px';
  const before = input.value.slice(0, pos);
  mirror.textContent = input.type === 'password' ? '\u2022'.repeat(before.length) : before;
  mirror.appendChild(mark);
  const lh = mark.offsetHeight || parseFloat(cs.fontSize);
  // offsetLeft is measured from the mirror's padding edge, so padding is already included
  const x = r.left + input.clientLeft + mark.offsetLeft - input.scrollLeft;
  // text is vertically centred inside the input's content box by the browser
  const y = r.top + input.clientTop + (input.clientHeight - lh) / 2 + lh / 2;
  caretKey = key;
  return (caretCache = { x: clamp(x, r.left + 10, r.right - 48), y, h: lh });
}

/* ---------- Comet ---------- */
const head = { x: 0, y: 0, vx: 0, vy: 0 };
const TL = 72, trail = [], parts = [], MAXP = 220;
let focusEl = null, mouse = null, lap = null, nextLap = 0, ready = false;
let fly = null, hoverBtn = false, tailS = 0, str = 0, strS = 0, flare = 0, starBoost = 0, nextMeteor = 4000;
const par = { x: 0, y: 0 }, rings = [], meteors = [];

const rectOf = el => el.closest('.field').querySelector('input').getBoundingClientRect();

function target(t) {
  const o = reduce ? 0 : 1;
  if (mouse && !coarse) return { x: mouse.x, y: mouse.y, k: .045, d: .16 };   // cursor always wins on desktop
  if (fly && t < fly.until) return { x: fly.x, y: fly.y, k: .1, d: .28 };
  if (lap) {                                   // curved trail around the active input
    const r = rectOf(focusEl), p = (t - lap.t0) / lap.dur;
    if (p >= 1) { lap = null; }
    else {
      const a = -Math.PI / 2 + p * 6.283, c = Math.cos(a), s = Math.sin(a);
      const sg = v => Math.sign(v) * Math.pow(Math.abs(v), .55);
      return { x: r.left + r.width / 2 + sg(c) * (r.width / 2 + 16), y: r.top + r.height / 2 + sg(s) * (r.height / 2 + 14), k: .07, d: .26 };
    }
  }
  if (hoverBtn && !btn.classList.contains('loading')) {   // circle the button while hovered
    const r = btn.getBoundingClientRect();
    return { x: r.left + r.width / 2 + Math.cos(t * .005) * (r.width / 2 + 14) * o, y: r.top + r.height / 2 + Math.sin(t * .005) * (r.height / 2 + 12) * o, k: .06, d: .22 };
  }
  if (focusEl === pw) {                        // hover beside the caret
    const c = caretPoint(pw);
    return { x: c.x + Math.cos(t * .004) * 9 * o + 6, y: c.y - c.h * .9 + Math.sin(t * .005) * 7 * o, k: .05, d: .2 };
  }
  if (focusEl) {
    const r = rectOf(focusEl);
    return { x: r.left + r.width * .72 + Math.cos(t * .002) * 18 * o, y: r.top - 12 + Math.sin(t * .003) * 8 * o, k: .035, d: .17 };
  }
  if (mouse && t - mouse.t < (coarse ? 2500 : 3500)) return { x: mouse.x, y: mouse.y, k: .028, d: .13 };
  return { x: W / 2 + Math.cos(t * .00035) * W * .34, y: H * .5 + Math.sin(t * .0005) * H * .3 + Math.sin(t * .0011) * 30 * o, k: .016, d: .1 };
}

function step(t) {
  const g = target(t);
  head.vx += (g.x - head.x) * g.k - head.vx * g.d;
  head.vy += (g.y - head.y) * g.k - head.vy * g.d;
  head.x += head.vx; head.y += head.vy;
  tailS += (clamp(Math.hypot(head.vx, head.vy) / 5, 0, 1) - tailS) * .08;
  strS += (str - strS) * .05; flare *= .92; starBoost *= .96;
  par.x += ((mouse ? mouse.x / W : .5) - .5 - par.x) * .04; par.y += ((mouse ? mouse.y / H : .5) - .5 - par.y) * .04;
  trail.unshift({ x: head.x, y: head.y });
  if (trail.length > TL) trail.pop();
  if (focusEl && !lap && !reduce && t > nextLap) { lap = { t0: t, dur: 1700 }; nextLap = t + 5000 + Math.random() * 3000; }
  const sp = Math.hypot(head.vx, head.vy), n = reduce ? 1 : (sp > 3 ? 3 : 2);
  for (let i = 0; i < n && parts.length < MAXP; i++) {
    const a = Math.random() * 6.283, v = Math.random() * .5;
    parts.push({ x: head.x + (Math.random() - .5) * 6, y: head.y + (Math.random() - .5) * 6, vx: Math.cos(a) * v - head.vx * .05, vy: Math.sin(a) * v - head.vy * .05, l: 0, m: 50 + Math.random() * 70, r: Math.random() * 1.3 + .4 });
  }
  for (let i = parts.length - 1; i >= 0; i--) {
    const p = parts[i]; p.x += p.vx; p.y += p.vy; p.vx *= .985; p.vy *= .985;
    if (++p.l > p.m) { parts[i] = parts[parts.length - 1]; parts.pop(); }
  }
}

function drawComet(t) {
  ctx.globalCompositeOperation = 'lighter';
  const n = Math.min(trail.length, Math.round(26 + tailS * (TL - 26))), sc = `${Math.round(120 + strS * 70)},${Math.round(175 + strS * 70)},255`;
  if (n > 2) {
    const nx = new Float32Array(n), ny = new Float32Array(n);
    for (let i = 0; i < n; i++) {               // per-point normals from the path direction
      const a = trail[Math.max(0, i - 1)], b = trail[Math.min(n - 1, i + 1)];
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
      nx[i] = -dy / d; ny[i] = dx / d;
    }
    const STR = 7;
    for (let s = 0; s < STR; s++) {
      const k = (s - (STR - 1) / 2), core = s === 3;
      ctx.lineCap = 'round';
      for (let i = 1; i < n; i++) {
        const f = i / n, spread = k * (3.5 + tailS * 5) * f * (reduce ? .6 : 1) * (1 + .5 * Math.sin(i * .15 - t * .004 + s));
        const a = trail[i - 1], b = trail[i];
        const ax = a.x + nx[i - 1] * spread, ay = a.y + ny[i - 1] * spread, bx = b.x + nx[i] * spread, by = b.y + ny[i] * spread;
        ctx.strokeStyle = `rgba(${core ? '210,230,255' : sc},${Math.pow(1 - f, 1.7) * (core ? .85 : .32)})`;
        ctx.lineWidth = ((1 - f) * (core ? 3.2 : 1.3) + .2) * (1 + tailS * .5);
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
      }
    }
  }
  for (const p of parts) {                      // sparkling trail particles
    const f = p.l / p.m, tw = .6 + .4 * Math.sin(t * .02 + p.m);
    ctx.fillStyle = `rgba(${p.c || '190,220,255'},${(1 - f) * .85 * tw})`;
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r * (1 - f * .5), 0, 6.283); ctx.fill();
  }
  let g = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 170);   // moving ambient light
  g.addColorStop(0, 'rgba(80,130,255,.10)'); g.addColorStop(1, 'rgba(80,130,255,0)');
  ctx.fillStyle = g; ctx.fillRect(head.x - 170, head.y - 170, 340, 340);
  g = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 46 * (1 + flare * .6));        // head glow
  g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(.12, 'rgba(200,225,255,.7)'); g.addColorStop(.4, 'rgba(90,150,255,.22)'); g.addColorStop(1, 'rgba(90,150,255,0)');
  ctx.fillStyle = g; { const R = 46 * (1 + flare * .6); ctx.fillRect(head.x - R, head.y - R, 2 * R, 2 * R); }
  ctx.globalCompositeOperation = 'source-over';
  for (let i = rings.length - 1; i >= 0; i--) {           // click / success shockwaves
    const r = rings[i], p = (t - r.t0) / r.dur;
    if (p >= 1) { rings.splice(i, 1); continue; }
    ctx.strokeStyle = `rgba(150,200,255,${(1 - p) * .55})`; ctx.lineWidth = 2 * (1 - p) + .5;
    ctx.beginPath(); ctx.arc(r.x, r.y, r.R * (1 - Math.pow(1 - p, 3)), 0, 6.283); ctx.stroke();
  }
}

function spark(n, v, c) {
  for (let i = 0; i < n && parts.length < MAXP * 1.5; i++) {
    const a = Math.random() * 6.283, sp = v * (.4 + Math.random() * .8);
    parts.push({ x: head.x, y: head.y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, l: 0, m: 30 + Math.random() * 40, r: Math.random() * 1.4 + .5, c });
  }
  flare = 1;
}
function flyTo(el, ms, fx = .5) {
  const r = el.getBoundingClientRect();
  fly = { x: r.left + r.width * fx, y: r.top + r.height / 2, until: performance.now() + ms };
}
function strength(v) {
  return Math.min(1, (v.length >= 8 ? .25 : 0) + (v.length >= 12 ? .25 : 0) + (/[a-z]/.test(v) && /[A-Z]/.test(v) ? .2 : 0) + (/\d/.test(v) ? .15 : 0) + (/[^A-Za-z0-9]/.test(v) ? .15 : 0));
}
function burst() {
  for (let i = 0; i < 46; i++) {
    const a = Math.random() * 6.283, v = 1 + Math.random() * 3;
    parts.push({ x: head.x, y: head.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, l: 0, m: 40 + Math.random() * 40, r: Math.random() * 1.6 + .5 });
  }
}

function frame(t) {
  if (!ready) { head.x = W * .3; head.y = H * .35; ready = true; }
  ctx.clearRect(0, 0, W, H);
  drawStars(t); step(t); drawComet(t);
  requestAnimationFrame(frame);
}

/* ---------- Input events ---------- */
addEventListener('pointermove', e => { mouse = { x: e.clientX, y: e.clientY, t: performance.now() }; }, { passive: true });
addEventListener('pointerdown', e => {
  const now = performance.now(); mouse = { x: e.clientX, y: e.clientY, t: now };
  rings.push({ x: e.clientX, y: e.clientY, t0: now, dur: 700, R: 70 });
  if (!reduce) { head.vx += (e.clientX - head.x) * .012; head.vy += (e.clientY - head.y) * .012; }
}, { passive: true });
document.documentElement.addEventListener('pointerleave', () => { mouse = null; });
[email, pw, confirm].forEach(el => {
  el.addEventListener('focus', () => { focusEl = el; lap = null; nextLap = performance.now() + 2500; caretKey = ''; });
  el.addEventListener('blur', () => { setTimeout(() => { if (![email, pw, confirm].includes(document.activeElement)) { focusEl = null; lap = null; } }, 0); });
  el.addEventListener('input', () => { clearErr(el); serverErr.textContent = ''; caretKey = ''; spark(8, 2.2); if (el === pw) str = strength(pw.value); });
});
addEventListener('resize', () => { resize(); caretKey = ''; });
addEventListener('scroll', () => { caretKey = ''; }, { passive: true });
btn.addEventListener('pointerenter', () => { hoverBtn = true; });
btn.addEventListener('pointerleave', () => { hoverBtn = false; });

/* ---------- Password toggle ---------- */
eye.addEventListener('click', () => {
  flyTo(eye, 750); spark(14, 2.5);
  const show = pw.type === 'password', s = pw.selectionStart, e = pw.selectionEnd;
  pw.type = show ? 'text' : 'password';
  eye.setAttribute('aria-pressed', show); eye.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  pw.focus(); try { pw.setSelectionRange(s, e); } catch (_) {}
  caretKey = '';
});

/* ---------- Validation + submit ---------- */
function setErr(el, msg) {
  const id = el === email ? 'email-err' : el === pw ? 'pw-err' : 'confirm-err';
  $('#' + id).textContent = msg; el.setAttribute('aria-invalid', 'true');
}
function clearErr(el) {
  const id = el === email ? 'email-err' : el === pw ? 'pw-err' : 'confirm-err';
  $('#' + id).textContent = ''; el.removeAttribute('aria-invalid');
}
function attemptId() { return crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random(); }
form.addEventListener('submit', e => {
  e.preventDefault();
  let bad = null;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value.trim())) { setErr(email, 'Enter a valid email address.'); bad = email; } else clearErr(email);
  if (pw.value.length < 8 || pw.value.length > 128) { setErr(pw, pw.value.length < 8 ? 'Password must be at least 8 characters.' : 'Password must be at most 128 characters.'); bad = bad || pw; } else clearErr(pw);
  if (mode === 'signup' && confirm.value !== pw.value) { setErr(confirm, 'The two passwords do not match.'); bad = bad || confirm; } else clearErr(confirm);
  if (bad) { flyTo(bad, 1100, .8); spark(22, 3, '255,141,161'); form.classList.remove('shake'); void form.offsetWidth; form.classList.add('shake'); bad.focus(); return; }
  serverErr.textContent = '';
  btn.classList.add('loading'); btn.setAttribute('aria-busy', 'true'); flyTo(btn, 1e9); lap = null;
  componentMessage(mode, { attemptId: attemptId(), email: email.value.trim(), password: pw.value, confirm: confirm.value });
});
back.addEventListener('click', () => componentMessage('back', { attemptId: attemptId() }));
signupLink.addEventListener('click', event => { event.preventDefault(); componentMessage('switch', { attemptId: attemptId(), mode: mode === 'signin' ? 'signup' : 'signin' }); });
function componentMessage(action, fields = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: { action, ...fields }, dataType: 'json' }, '*');
}
function setComponentHeight() {
  window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: Math.max(document.documentElement.scrollHeight, innerHeight) }, '*');
}
window.addEventListener('message', event => {
  if (event.data?.type !== 'streamlit:render') return;
  const args = event.data.args || {};
  mode = args.mode === 'signup' ? 'signup' : 'signin';
  const signup = mode === 'signup';
  document.title = signup ? 'Finora — Create account' : 'Finora — Sign in';
  title.innerHTML = signup ? 'Create your <em>account</em>' : 'Welcome back';
  subtitle.textContent = signup ? 'Your statement stays private to this account.' : 'Sign in to return to your financial workspace.';
  confirmField.hidden = !signup;
  confirm.disabled = !signup;
  signupLink.textContent = signup ? 'Sign in' : 'Create an account';
  switchCopy.textContent = signup ? 'Already have an account?' : 'First time here?';
  btn.querySelector('.lbl').textContent = signup ? 'Create account' : 'Sign in';
  pw.autocomplete = signup ? 'new-password' : 'current-password';
  serverErr.textContent = args.error || '';
  btn.classList.remove('loading', 'success'); btn.removeAttribute('aria-busy');
  setComponentHeight();
});
window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1 }, '*');
resize();
if (reduce) {
  head.x = W * .3; head.y = H * .35; ready = true;
  ctx.clearRect(0, 0, W, H); drawStars(0); drawComet(0);
} else requestAnimationFrame(frame);
})();
