// "Kelinlar" bo'limi: Lusion'dagi TEAM gologrammasi uslubida kelin portretlari.
// Har bir portret rasmdan o'qilib, minglab nuqtalarga (halftone) aylantiriladi: yorug' joyda nuqta katta va
// yorqin, soyada kichik va xira. Portretlar almashganda eskisining nuqtalari chapga sochilib so'nadi,
// yangisiniki o'ngdan uchib kelib yig'iladi. Kursor yaqinidagi nuqtalarni to'lqin bilan itaradi,
// vaqti-vaqti bilan gorizontal "glitch" chiziqlari o'tadi — gologramma hissi shundan.
// Tashqi kutubxona yo'q, WebGL1. WebGL bo'lmasa null qaytaradi.
//
//   const g = await gologrammaYarat(canvas, ['/kelinlar/1.jpg', ...])
//   g.tanla(i)   — i-portretga o'tish (animatsiya bilan)
//   g.yop()
// Uchinchi ixtiyoriy parametr `soni` — bitta obrazdagi nuqtalar soni (standart N=22000). Kichik kanvaslarda
// (masalan, guldasta avatarlarida) shuncha nuqta haddan tashqari zich bo'ladi — shu uchun kamaytiriladi.
// To'rtinchi ixtiyoriy parametr — { markaz: [x, y], masshtab }: figuraning kanvasdagi markazi (0..1 ulushda) va yarim
// o'lchami (kanvasning kichik tomonidan ulush). Standart qiymatlar «Kelinlar» bo'limi uchun. Kanvas figuradan ancha
// katta bo'lsa (masshtab kichik), almashish paytida sochilgan nuqtalar kanvas chetida kesilmaydi.

const N = 22000                     // bitta portretdagi nuqtalar soni (hamma portretda bir xil)
const r = Math.random

const VS = `
attribute vec3 aA; attribute vec3 aB; attribute vec2 aR;   // aA/aB: (x, y, yorug'lik) — eski va yangi portret
uniform float uT, uVaqt, uDpr, uOl; uniform vec2 uRes, uSich, uMarkaz; uniform float uMasshtab, uGlitch;
varying float vY, vA;
float hash(float n){ return fract(sin(n) * 43758.5453); }
void main(){
  float kech = aR.x * .45;                                  // har nuqta o'z vaqtida uchadi
  float t = smoothstep(kech, kech + .55, uT);
  // eski portret: chapga sochilib ketadi; yangi: o'ngdan yig'ilib keladi
  vec2 a = aA.xy + vec2(-t * (1.1 + aR.y * 1.4), (aR.y - .5) * t * .9);
  vec2 b = aB.xy + vec2((1. - t) * (1.1 + aR.x * 1.4), (aR.x - .5) * (1. - t) * .9);
  vec2 p = mix(a, b, step(.5, t));
  float yor = mix(aA.z, aB.z, step(.5, t));
  float ko = step(.5, t) * t + (1. - step(.5, t)) * (1. - t);   // ko'rinish: o'tishda pasayadi
  // nafas: nuqtalar yorug'ligiga qarab sekin chayqaladi (chuqurlik hissi)
  p += vec2(sin(uVaqt * .9 + p.y * 6.) , cos(uVaqt * .7 + p.x * 5.)) * .004 * yor;
  // glitch: ingichka gorizontal tasma bo'ylab siljish
  float tasma = step(.985, hash(floor((p.y + uVaqt * .3) * 40.) + floor(uVaqt * 8.)));
  p.x += tasma * uGlitch * (hash(p.y * 91.) - .5) * .12;
  vec2 s = (p * uMasshtab + uMarkaz);                       // ekran piksellarida
  vec2 d = s - uSich; float m = length(d);
  s += normalize(d + 1e-4) * exp(-m * m / (130. * 130. * uDpr * uDpr)) * 38. * uDpr;   // kursor to'lqini
  gl_Position = vec4(s / uRes * 2. - 1., 0., 1.); gl_Position.y *= -1.;
  gl_PointSize = uOl * uDpr * (.35 + yor * 1.25);
  vY = yor; vA = ko * (.25 + yor * .9);
}`

const FS = `
precision mediump float;
varying float vY, vA;
void main(){
  vec2 q = gl_PointCoord * 2. - 1.; float d = dot(q, q);
  if (d > 1.) discard;
  vec3 soya = vec3(.16, .25, .42), oq = vec3(.98, .95, .9), tilla = vec3(.89, .76, .59);
  vec3 c = mix(soya, mix(tilla, oq, smoothstep(.5, 1., vY)), smoothstep(.12, .7, vY));
  float a = vA * (1. - d * .55);
  gl_FragColor = vec4(c * a, a);
}`

// Rasmdan nuqtalar: yorug'likka mutanosib ehtimollik bilan tanlanadi, natija har doim N ta
// rasm: '/kelinlar/1.jpg' yoki { src, kesim: [x, y, w, h] } — kesim rasmning bir qismini (0..1 ulushda) oladi
async function nuqtalar(rasm, soni = N) {
  const { src, kesim = [0, 0, 1, 1] } = typeof rasm === 'string' ? { src: rasm } : rasm
  const im = new Image(); im.crossOrigin = 'anonymous'; im.src = src
  await im.decode()
  const sx = kesim[0] * im.width, sy = kesim[1] * im.height, sw = kesim[2] * im.width, sh = kesim[3] * im.height
  const W = 170, H = Math.round(W * sh / sw)
  const c = document.createElement('canvas'); c.width = W; c.height = H
  const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(im, sx, sy, sw, sh, 0, 0, W, H)
  const px = x.getImageData(0, 0, W, H).data
  const yor = new Float32Array(W * H)
  for (let i = 0; i < W * H; i++) {
    const l = (px[i * 4] * .3 + px[i * 4 + 1] * .59 + px[i * 4 + 2] * .11) / 255
    yor[i] = Math.pow(Math.max(0, l - .06) / .94, .8)
  }
  const out = new Float32Array(soni * 3)
  let k = 0, urinish = 0
  while (k < soni && urinish < soni * 60) {
    urinish++
    const ix = (r() * W) | 0, iy = (r() * H) | 0, l = yor[iy * W + ix]
    if (r() > l * 1.15 + .015) continue
    out[k * 3] = (ix + r() - W / 2) / (W / 2)               // -1..1
    out[k * 3 + 1] = (iy + r() - H / 2) / (H / 2) * 1.0   // bo'y bo'yicha -1..1 — to'liq bo'yli obraz ekranga sig'adi
    out[k * 3] *= W / H
    out[k * 3 + 2] = l
    k++
  }
  for (; k < soni; k++) { out[k * 3] = (r() - .5) * 2; out[k * 3 + 1] = (r() - .5) * 2; out[k * 3 + 2] = 0 }
  return out
}

export async function gologrammaYarat(canvas, rasmlar, soni = N, { markaz = [.46, .52], masshtab = .46 } = {}) {
  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false })
  if (!gl) return null
  const yig = (tur, m) => { const s = gl.createShader(tur); gl.shaderSource(s, m); gl.compileShader(s); return s }
  const p = gl.createProgram()
  gl.attachShader(p, yig(gl.VERTEX_SHADER, VS)); gl.attachShader(p, yig(gl.FRAGMENT_SHADER, FS))
  ;['aA', 'aB', 'aR'].forEach((n, i) => gl.bindAttribLocation(p, i, n))
  gl.linkProgram(p); gl.useProgram(p)
  const u = {}; ['uT', 'uVaqt', 'uDpr', 'uOl', 'uRes', 'uSich', 'uMarkaz', 'uMasshtab', 'uGlitch'].forEach((n) => { u[n] = gl.getUniformLocation(p, n) })

  const tasodif = new Float32Array(soni * 2); for (let i = 0; i < tasodif.length; i++) tasodif[i] = r()
  const bR = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bR); gl.bufferData(gl.ARRAY_BUFFER, tasodif, gl.STATIC_DRAW)
  gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 2, gl.FLOAT, false, 0, 0)

  const toplam = await Promise.all(rasmlar.map((rasm) => nuqtalar(rasm, soni)))
  const buf = toplam.map((d) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STATIC_DRAW); return b })
  const ula = (joy, b) => { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(joy); gl.vertexAttribPointer(joy, 3, gl.FLOAT, false, 0, 0) }

  gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
  let eni = 0, boyi = 0, dpr = 1, kadr = 0
  let eski = 0, yangi = 0, T = 1, glitch = 0
  const sich = { x: -9999, y: -9999, tx: -9999, ty: -9999 }
  const olcham = () => {
    dpr = Math.min(window.devicePixelRatio || 1, 2)
    const r0 = canvas.getBoundingClientRect(); eni = r0.width; boyi = r0.height
    canvas.width = eni * dpr; canvas.height = boyi * dpr; gl.viewport(0, 0, canvas.width, canvas.height)
  }
  const surildi = (e) => { const r0 = canvas.getBoundingClientRect(); sich.tx = (e.clientX - r0.left) * dpr; sich.ty = (e.clientY - r0.top) * dpr }
  olcham()

  let oldingi = performance.now()
  const chiz = (hozir) => {
    const dt = Math.min(.05, (hozir - oldingi) / 1000); oldingi = hozir
    T = Math.min(1, T + dt / 1.6)
    glitch = Math.max(0, glitch - dt * 1.5) + (Math.random() < .004 ? 1 : 0)   // goh-goh "titrash"
    sich.x += (sich.tx - sich.x) * .2; sich.y += (sich.ty - sich.y) * .2
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT)
    ula(0, buf[eski]); ula(1, buf[yangi])
    gl.uniform1f(u.uT, T); gl.uniform1f(u.uVaqt, hozir / 1000); gl.uniform1f(u.uDpr, dpr)
    gl.uniform1f(u.uOl, Math.max(1.6, Math.min(eni, boyi) * (masshtab / .46) / 380))   // nuqta o'lchami figuraga mutanosib
    gl.uniform2f(u.uRes, canvas.width, canvas.height); gl.uniform2f(u.uSich, sich.x, sich.y)
    gl.uniform2f(u.uMarkaz, canvas.width * markaz[0], canvas.height * markaz[1])
    gl.uniform1f(u.uMasshtab, Math.min(canvas.width, canvas.height) * masshtab)
    gl.uniform1f(u.uGlitch, Math.min(1, glitch))
    gl.drawArrays(gl.POINTS, 0, soni)
    kadr = requestAnimationFrame(chiz)
  }
  window.addEventListener('resize', olcham)
  // Kursor to'lqini (nuqtalarni aylana bo'ylab itarish) faqat sichqoncha bor qurilmada — mobil/teginishda chiroyli chiqmaydi.
  if (window.matchMedia('(pointer: fine)').matches) window.addEventListener('pointermove', surildi, { passive: true })
  kadr = requestAnimationFrame(chiz)

  return {
    soni: rasmlar.length,
    tanla: (i) => { if (i === yangi) return; eski = yangi; yangi = i; T = 0; glitch = 1 },
    yop: () => { cancelAnimationFrame(kadr); window.removeEventListener('resize', olcham); window.removeEventListener('pointermove', surildi) },
  }
}
