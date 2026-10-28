// Bosh kadrning interaktiv qatlami: video USTIDA turadigan shaffof WebGL tuval.
// Video (qasr.mp4) — "sahna": zal, nur, kamera chekinishi. Bu fayl — "jonli qism": gulbarglar girdobi,
// kursor ularni suyuqlikdek tarqatadi va ular yana o'z joyiga qaytadi (Lusion'dagi zarracha buluti kabi).
// Tashqi kutubxona yo'q. WebGL bo'lmasa `gulbargYarat` null qaytaradi — sahifa faqat video bilan qoladi.
//
// Ishlatish (Reklama.jsx yoki QasrVideo.jsx ichida):
//   const g = gulbargYarat(tuval)   // tuval — <canvas className="rk-gulbarg">
//   g.sur(p)                         // p: 0..1 — bosh kadrdagi aylantirish ulushi (video bilan bir xil qiymat)
//   g.yop()                          // komponent o'chganda

const TAU = Math.PI * 2
const r = Math.random

const VS = `
attribute vec2 aP; attribute float aOl, aBur, aShaf; attribute vec3 aRang;
uniform vec2 uRes;
varying float vBur, vShaf; varying vec3 vRang;
void main(){
  vec2 c = aP / uRes * 2. - 1.; c.y = -c.y;
  gl_Position = vec4(c, 0., 1.);
  gl_PointSize = aOl;
  vBur = aBur; vShaf = aShaf; vRang = aRang;
}`

// Har bir nuqta — gulbarg: burilgan, bir uchi ingichka tomchi shakli, chetlari yumshoq
const FS = `
precision mediump float;
varying float vBur, vShaf; varying vec3 vRang;
void main(){
  vec2 q = gl_PointCoord * 2. - 1.;
  float c = cos(vBur), s = sin(vBur);
  q = vec2(c * q.x - s * q.y, s * q.x + c * q.y);
  q.x *= 1. + q.y * .35;                       // tomchi: pastga torayadi
  float d = length(q * vec2(1.65, 1.));
  float a = smoothstep(1., .55, d) * vShaf;
  if (a < .01) discard;
  vec3 col = vRang * (.82 + .18 * (1. - d));   // o'rtasi sal yorqinroq
  gl_FragColor = vec4(col * a, a);             // premultiplied alpha
}`

export function gulbargYarat(canvas) {
  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false })
  if (!gl) return null
  const kichik = Math.min(window.innerWidth, window.innerHeight) < 700
  const N = kichik ? 600 : 1400

  const yig = (tur, manba) => { const s = gl.createShader(tur); gl.shaderSource(s, manba); gl.compileShader(s); return s }
  const p = gl.createProgram()
  gl.attachShader(p, yig(gl.VERTEX_SHADER, VS)); gl.attachShader(p, yig(gl.FRAGMENT_SHADER, FS))
  ;['aP', 'aOl', 'aBur', 'aShaf', 'aRang'].forEach((n, i) => gl.bindAttribLocation(p, i, n))
  gl.linkProgram(p); gl.useProgram(p)
  const uRes = gl.getUniformLocation(p, 'uRes')

  // Har gulbarg: girdobdagi "uy" joyi (burchak, radius, chuqurlik) + kursor siljitgan og'ish (o) va tezlik (v)
  const g = Array.from({ length: N }, () => {
    const yaqin = r() < 0.12                       // 12% — kameraga yaqin, katta va tez uchib o'tadiganlar
    return {
      th: r() * TAU, rad: Math.pow(r(), 0.6), z: yaqin ? 0.25 + r() * 0.25 : 0.6 + r() * 1.2,
      bur: r() * TAU, burT: (r() - 0.5) * 3, ol: 0.6 + r() * 0.8, yaqin,
      rang: r() < 0.35 ? [1, 0.86, 0.88] : [1, 0.97, 0.92],     // pushti yoki fil suyagi
      ox: 0, oy: 0, vx: 0, vy: 0,
    }
  })
  // Har gulbarg uchun 8 ta son: x, y | o'lcham | burilish | shaffoflik | rang (r, g, b) — bitta buferda ketma-ket
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  const QADAM = 8 * 4
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, QADAM, 0)
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 1, gl.FLOAT, false, QADAM, 8)
  gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 1, gl.FLOAT, false, QADAM, 12)
  gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 1, gl.FLOAT, false, QADAM, 16)
  gl.enableVertexAttribArray(4); gl.vertexAttribPointer(4, 3, gl.FLOAT, false, QADAM, 20)
  gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)   // premultiplied alpha bilan to'g'ri aralashtirish

  let eni = 0, boyi = 0, dpr = 1, kadr = 0, P = 0, maqsadP = 0
  const sich = { x: -9999, y: -9999, px: -9999, py: -9999, vx: 0, vy: 0 }
  const olcham = () => {
    dpr = Math.min(window.devicePixelRatio || 1, 2)
    eni = window.innerWidth; boyi = window.innerHeight
    canvas.width = eni * dpr; canvas.height = boyi * dpr
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.uniform2f(uRes, eni * dpr, boyi * dpr)
  }
  const surildi = (e) => { sich.x = e.clientX; sich.y = e.clientY }
  olcham()

  const data = new Float32Array(N * 8)

  let oldingi = performance.now()
  const chiz = (hozir) => {
    const dt = Math.min(0.05, (hozir - oldingi) / 1000); oldingi = hozir
    const t = hozir / 1000
    P = maqsadP   // silliqlashsiz: video va matnlar bilan bir xil aylantirish holatida turadi (QasrVideo.jsx)
    const e = 1 - Math.pow(1 - P, 3)                 // kamera chekinishi: boshida tez, oxirida sekin

    // Sichqoncha tezligi — gulbarglarga "shamol" shu tezlik yo'nalishida beriladi
    if (sich.px > -9000) { sich.vx = sich.x - sich.px; sich.vy = sich.y - sich.py }
    sich.px = sich.x; sich.py = sich.y

    // Girdob markazi va kattaligi videodagi bulutga mos: boshida butun ekran, oxirida zal tepasida kichkina
    const cx = eni * 0.5, cy = boyi * (0.5 - 0.08 * e)
    const R = Math.max(eni, boyi) * (0.75 - 0.62 * e)
    const ta = 140 * dpr                               // kursor ta'sir radiusi

    for (let i = 0; i < N; i++) {
      const q = g[i]
      const om = (0.25 + (1 - q.rad) * 1.1) * (1 - 0.5 * e)   // markazga yaqinlari tezroq aylanadi
      const a = q.th + t * om
      const s = 1 / q.z
      let x = cx + Math.cos(a) * q.rad * R * s * 0.9
      let y = cy + Math.sin(a) * q.rad * R * s * 0.55
      if (q.yaqin) {                                   // yaqin gulbarglar kamera chekinganda chetga uchib chiqib ketadi
        x = cx + (x - cx) * (1 + e * 2.5); y = cy + (y - cy) * (1 + e * 2.5)
      }

      // Kursor: yaqin turgan gulbargga sichqoncha harakati bo'yicha turtki, keyin prujina bilan uyga qaytish
      const dx = x + q.ox - sich.x, dy = y + q.oy - sich.y
      const d2 = dx * dx + dy * dy
      if (d2 < ta * ta) {
        const k = 1 - Math.sqrt(d2) / ta
        q.vx += (sich.vx * 0.9 + dx * 0.04) * k
        q.vy += (sich.vy * 0.9 + dy * 0.04) * k
        q.burT += (sich.vx + sich.vy) * 0.01 * k
      }
      q.vx += -q.ox * 2.2 * dt; q.vy += -q.oy * 2.2 * dt   // prujina
      q.vx *= 0.93; q.vy *= 0.93                           // so'nish
      q.ox += q.vx; q.oy += q.vy
      q.bur += q.burT * dt; q.burT *= 0.995

      const ol = (q.yaqin ? 46 : 14) * q.ol * s * (1 - 0.7 * e) * dpr
      const shaf = (q.yaqin ? 0.55 * (1 - e) : 0.9) * Math.min(1, 0.35 + q.rad)
      const j = i * 8
      data[j] = (x + q.ox) * dpr; data[j + 1] = (y + q.oy) * dpr
      data[j + 2] = Math.max(1, ol); data[j + 3] = q.bur; data[j + 4] = shaf
      data[j + 5] = q.rang[0]; data[j + 6] = q.rang[1]; data[j + 7] = q.rang[2]
    }

    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT)
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW)
    gl.drawArrays(gl.POINTS, 0, N)
    kadr = requestAnimationFrame(chiz)
  }

  window.addEventListener('resize', olcham)
  window.addEventListener('pointermove', surildi, { passive: true })
  kadr = requestAnimationFrame(chiz)

  return {
    sur: (p) => { maqsadP = p },
    yop: () => {
      cancelAnimationFrame(kadr)
      window.removeEventListener('resize', olcham)
      window.removeEventListener('pointermove', surildi)
    },
  }
}
