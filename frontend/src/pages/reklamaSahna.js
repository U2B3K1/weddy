// Bosh sahifa foni: WebGL'da oqayotgan atlas mato va nur zarrachalaridan yig'ilgan shakllar.
// Zarrachalar aylantirishga qarab bir shakldan boshqasiga oqib o'tadi: toj → kalendar → uzuklar → o'sish grafigi → chang → libos.
// Tashqi kutubxona yo'q; WebGL bo'lmasa `sahnaYarat` null qaytaradi va sahifa oddiy gradient fonda qoladi.

const TAU = Math.PI * 2
const r = Math.random

// --- Shakllar: har biri N ta nuqta (x, y, z), taxminan [-1.3 .. 1.3] oralig'ida ---

function libos(N) {
  const a = new Float32Array(N * 3)
  const soni = { etak: 0.52, hoshiya: 0.07, korset: 0.1, fata: 0.14, qomat: 0.1, toj: 0.03 }
  const etakR = (u, th) => (0.15 + 0.9 * u ** 0.8) * (1 + 0.085 * u * Math.sin(th * 11 + u * 4) + 0.03 * u * Math.sin(th * 23))
  let k = 0
  const qoy = (x, y, z) => { a[k++] = x; a[k++] = y; a[k++] = z }
  const shleyf = (z, u) => (z < 0 ? z * (1 + 0.42 * u * u) : z)   // orqaga cho'zilgan etak
  for (let i = 0; i < N; i++) {
    const q = i / N
    const th = r() * TAU
    if (q < soni.etak) {
      const u = r() ** 0.62
      const rad = etakR(u, th)
      qoy(rad * Math.cos(th), 0.05 - 1.3 * u, shleyf(rad * Math.sin(th), u))
    } else if (q < soni.etak + soni.hoshiya) {
      const rad = etakR(1, th) * (1.0 + r() * 0.02)
      qoy(rad * Math.cos(th), -1.25 + 0.035 * Math.sin(th * 22) + r() * 0.02, shleyf(rad * Math.sin(th), 1))
    } else if (q < soni.etak + soni.hoshiya + soni.korset) {
      const v = r()
      const rx = 0.145 + 0.055 * Math.sin(Math.PI * (v * 0.85 + 0.08)) + 0.02 * v     // bel ingichka, ko'krak kengroq
      const tepa = 0.55 - 0.07 * Math.max(0, Math.cos(th * 2)) * (Math.sin(th) > 0 ? 1 : 0.3)  // «yurak» bo'yin o'yig'i
      qoy(rx * Math.cos(th), Math.min(0.05 + 0.52 * v, tepa), rx * 0.7 * Math.sin(th))
    } else if (q < soni.etak + soni.hoshiya + soni.korset + soni.fata) {
      const v = r() ** 0.8
      const phi = (r() - 0.5) * Math.PI * 1.15
      const rad = (0.13 + 0.92 * v ** 0.9) * (1 + 0.05 * Math.sin(phi * 9 + v * 6))
      qoy(rad * Math.sin(phi), 1.03 - 2.05 * v, -rad * Math.cos(phi) - 0.03)
    } else if (q < soni.etak + soni.hoshiya + soni.korset + soni.fata + soni.qomat) {
      const t = r()
      if (t < 0.22) {            // bosh
        const u = r() * 2 - 1, s = Math.sqrt(1 - u * u)
        qoy(0.115 * s * Math.cos(th), 0.9 + 0.14 * u, 0.115 * s * Math.sin(th))
      } else if (t < 0.3) {      // bo'yin
        qoy(0.045 * Math.cos(th), 0.6 + r() * 0.17, 0.045 * Math.sin(th))
      } else if (t < 0.42) {     // yelka chizig'i
        const s = (r() * 2 - 1)
        qoy(s * 0.27, 0.63 - 0.09 * Math.abs(s) ** 1.6 + r() * 0.015, (r() - 0.5) * 0.08)
      } else if (t < 0.74) {     // qo'llar: yelkadan tirsakka, tirsakdan oldinda tutilgan guldastaga
        const yon = r() < 0.5 ? -1 : 1, s = r(), e = 0.022
        const [ax, ay, az, bx, by, bz] = s < 0.5 ? [0.27, 0.57, 0, 0.3, 0.22, 0.04] : [0.3, 0.22, 0.04, 0.07, 0.06, 0.24]
        const f = (s < 0.5 ? s : s - 0.5) * 2
        qoy(yon * (ax + (bx - ax) * f) + (r() - 0.5) * e * 2, ay + (by - ay) * f + (r() - 0.5) * e * 2, az + (bz - az) * f + (r() - 0.5) * e * 2)
      } else {                   // guldasta: belda, oldinda
        const u = r() * 2 - 1, s = Math.sqrt(1 - u * u), rad = 0.12 * r() ** 0.4
        qoy(rad * s * Math.cos(th), 0.03 + rad * u * 0.9, 0.27 + rad * s * Math.sin(th) * 0.7)
      }
    } else if (q < soni.etak + soni.hoshiya + soni.korset + soni.fata + soni.qomat + soni.toj) {
      qoy(0.125 * Math.cos(th), 1.03 + 0.07 * Math.max(0, Math.sin(th * 7)) * (Math.sin(th) > -0.2 ? 1 : 0), 0.125 * Math.sin(th))
    } else {                     // atrofdagi uchqunlar
      const rad = 0.9 + r() * 0.9
      qoy(rad * Math.cos(th), (r() - 0.5) * 2.6, rad * Math.sin(th))
    }
  }
  return a
}

function kalendar(N) {
  const a = new Float32Array(N * 3)
  const W = 2.3, H = 1.55, cw = W / 7, ch = H / 5, ich = 0.1
  const band = [[2, 2], [3, 2], [4, 2], [5, 3], [1, 4]]   // band kunlar: uch kunlik ijara va ikkita alohida bron
  for (let i = 0; i < N; i++) {
    const q = i / N
    let x, y, z = (r() - 0.5) * 0.04
    if (q < 0.5) {               // kataklar chizig'i
      const c = (r() * 7) | 0, row = (r() * 5) | 0
      const x0 = -W / 2 + c * cw + cw * ich, y0 = H / 2 - 0.25 - row * ch - ch * ich
      const w = cw * (1 - 2 * ich), h = ch * (1 - 2 * ich), p = r() * (w + h) * 2
      if (p < w) { x = x0 + p; y = y0 } else if (p < w + h) { x = x0 + w; y = y0 - (p - w) } else if (p < 2 * w + h) { x = x0 + (p - w - h); y = y0 - h } else { x = x0; y = y0 - (p - 2 * w - h) }
    } else if (q < 0.86) {       // band kataklar to'ldirilgan va oldinga chiqqan
      const [c, row] = band[(r() * band.length) | 0]
      x = -W / 2 + c * cw + cw * (ich + r() * (1 - 2 * ich))
      y = H / 2 - 0.25 - row * ch - ch * (ich + r() * (1 - 2 * ich))
      z = 0.12 + r() * 0.05
    } else if (q < 0.96) {       // sarlavha chizig'i va ilgak halqalari
      if (r() < 0.6) { x = (r() - 0.5) * W; y = H / 2 - 0.08 + (r() - 0.5) * 0.03 } else {
        const th = r() * TAU, cx = (r() < 0.5 ? -1 : 1) * W * 0.3
        x = cx + 0.07 * Math.cos(th); y = H / 2 + 0.02 + 0.1 * Math.sin(th)
      }
    } else { x = (r() - 0.5) * 3.4; y = (r() - 0.5) * 2.6; z = (r() - 0.5) * 1.6 }
    a[i * 3] = x; a[i * 3 + 1] = y - 0.05; a[i * 3 + 2] = z
  }
  return a
}

function uzuklar(N) {
  const a = new Float32Array(N * 3)
  const tor = (i, cx, cy, egX, egZ, R, t) => {
    const u = r() * TAU, v = r() * TAU
    let x = (R + t * Math.cos(v)) * Math.cos(u), y = (R + t * Math.cos(v)) * Math.sin(u), z = t * Math.sin(v)
    let c = Math.cos(egX), s = Math.sin(egX); [y, z] = [c * y - s * z, s * y + c * z]
    c = Math.cos(egZ); s = Math.sin(egZ); [x, z] = [c * x + s * z, -s * x + c * z]
    a[i * 3] = x + cx; a[i * 3 + 1] = y + cy; a[i * 3 + 2] = z
  }
  for (let i = 0; i < N; i++) {
    const q = i / N
    if (q < 0.4) tor(i, -0.3, -0.12, 0.35, 0.5, 0.62, 0.06)
    else if (q < 0.8) tor(i, 0.34, 0.02, -0.3, -0.6, 0.58, 0.055)
    else if (q < 0.94) {         // birinchi uzukdagi tosh: ikki konus
      const h = r() * 2 - 1, rad = 0.17 * (1 - Math.abs(h)), th = ((r() * 8) | 0) / 8 * TAU + (r() - 0.5) * 0.25
      a[i * 3] = -0.3 + rad * Math.cos(th); a[i * 3 + 1] = 0.62 + (h > 0 ? h * 0.1 : h * 0.2) + 0.1; a[i * 3 + 2] = rad * Math.sin(th) + 0.2
    } else { a[i * 3] = (r() - 0.5) * 3.2; a[i * 3 + 1] = (r() - 0.5) * 2.4; a[i * 3 + 2] = (r() - 0.5) * 1.8 }
  }
  return a
}

function grafik(N) {
  const a = new Float32Array(N * 3)
  const boy = [0.32, 0.52, 0.46, 0.82, 1.08, 1.5], eni = 0.24, asos = -0.82
  const xi = (j) => -1.05 + j * 0.42
  for (let i = 0; i < N; i++) {
    const q = i / N
    let x, y, z
    if (q < 0.74) {              // ustunlar — baland ustunga ko'proq nuqta
      let j = 0, t = r() * 4.7
      while (j < 5 && t > boy[j]) { t -= boy[j]; j++ }
      const h = boy[j], yuz = r()
      if (yuz < 0.82) {          // yon devorlar
        const p = r() * 4; y = asos + r() * h
        if (p < 1) { x = xi(j) + (p - 0.5) * eni; z = eni / 2 } else if (p < 2) { x = xi(j) + (p - 1.5) * eni; z = -eni / 2 } else if (p < 3) { x = xi(j) + eni / 2; z = (p - 2.5) * eni } else { x = xi(j) - eni / 2; z = (p - 3.5) * eni }
      } else { x = xi(j) + (r() - 0.5) * eni; z = (r() - 0.5) * eni; y = asos + h }
    } else if (q < 0.9) {        // o'sish chizig'i va o'q uchi
      const t = r()
      if (t < 0.82) {
        const s = r() * 5, j = Math.min(4, s | 0), f = s - j
        x = xi(j) + f * 0.42; y = asos + boy[j] + (boy[j + 1] - boy[j]) * f + 0.22; z = 0.02
      } else {
        const f = r(), yon = r() < 0.5 ? 1 : -1
        x = xi(5) + 0.1 - f * 0.2 * (yon > 0 ? 1 : 0.25); y = asos + boy[5] + 0.3 - f * 0.2 * (yon > 0 ? 0.3 : 1); z = 0.02
      }
    } else if (q < 0.96) { x = (r() - 0.5) * 2.7; y = asos - 0.02; z = (r() - 0.5) * 0.3 } else { x = (r() - 0.5) * 3.4; y = (r() - 0.5) * 2.6; z = (r() - 0.5) * 1.8 }
    a[i * 3] = x; a[i * 3 + 1] = y - 0.12; a[i * 3 + 2] = z
  }
  return a
}

function chang(N) {
  const a = new Float32Array(N * 3)
  for (let i = 0; i < N; i++) {
    const th = r() * TAU, u = r() * 2 - 1, s = Math.sqrt(1 - u * u), rad = 1.1 + r() ** 0.7 * 2.1
    a[i * 3] = rad * s * Math.cos(th) * 1.5; a[i * 3 + 1] = rad * u * 0.75; a[i * 3 + 2] = rad * s * Math.sin(th) * 0.8
  }
  return a
}

// Toj (bosh kadr): gardish, toshlar, baland-past tishlar, tepada birlashuvchi yoylar va shar. Atrofida nur ustunidagi chang.
function toj(N) {
  const a = new Float32Array(N * 3)
  const R = 0.62, past = -0.5, bel = -0.28
  let k = 0
  const qoy = (x, y, z) => { a[k++] = x; a[k++] = y + 0.05; a[k++] = z }
  for (let i = 0; i < N; i++) {
    const q = i / N, th = r() * TAU
    if (q < 0.2) {                 // gardish: ikki zich halqa va ular orasi
      const t = r(), y = t < 0.3 ? past + r() * 0.012 : t < 0.6 ? bel - r() * 0.012 : past + r() * (bel - past)
      qoy(R * Math.cos(th), y, R * Math.sin(th))
    } else if (q < 0.27) {         // gardishdagi sakkizta tosh
      const g = ((r() * 8) | 0) / 8 * TAU, u = r() * 2 - 1, s = 0.045 * (1 - Math.abs(u)), f = r() * TAU
      qoy((R + 0.02 + s * 0.4) * Math.cos(g + s * Math.cos(f)), (past + bel) / 2 + u * 0.07, (R + 0.02 + s * 0.4) * Math.sin(g + s * Math.cos(f)))
    } else if (q < 0.6) {          // sakkizta tish: to'rttasi baland (uchida marvarid), to'rttasi past
      const n = (r() * 8) | 0, baland = n % 2 === 0, h = baland ? 0.6 : 0.3, eni = (TAU / 16) * 0.92
      const tur = r()
      if (baland && tur < 0.14) {  // marvarid
        const u = r() * 2 - 1, s = Math.sqrt(1 - u * u), f = r() * TAU, rr = R * 1.2
        qoy(rr * Math.cos(n / 8 * TAU) + 0.05 * s * Math.cos(f), bel + h + 0.05 + 0.05 * u, rr * Math.sin(n / 8 * TAU) + 0.05 * s * Math.sin(f))
      } else {
        const s = r() * 2 - 1, chet = 1 - Math.abs(s) ** 1.5
        const t = tur < 0.7 ? chet : chet * r()            // ko'pi kontur, qolgani ichi
        const rr = R * (1 + 0.2 * t * (h / 0.6)), g = n / 8 * TAU + s * eni
        qoy(rr * Math.cos(g), bel + h * t, rr * Math.sin(g))
      }
    } else if (q < 0.74) {         // to'rtta yoy: baland tishlardan tepadagi sharga
      const n = ((r() * 4) | 0) * 2, u = r(), g = n / 8 * TAU
      const rr = R * 1.2 * Math.cos(u * Math.PI / 2) ** 0.75 + (r() - 0.5) * 0.012, y = bel + 0.62 + 0.36 * Math.sin(u * Math.PI / 2)
      qoy(rr * Math.cos(g), y, rr * Math.sin(g))
    } else if (q < 0.79) {         // tepadagi shar va xoch
      if (r() < 0.7) { const u = r() * 2 - 1, s = Math.sqrt(1 - u * u); qoy(0.075 * s * Math.cos(th), 0.78 + 0.075 * u, 0.075 * s * Math.sin(th)) } else {
        const t = r(); if (t < 0.6) qoy((r() - 0.5) * 0.02, 0.86 + r() * 0.2, 0); else qoy((r() - 0.5) * 0.13, 0.99 + (r() - 0.5) * 0.02, 0)
      }
    } else {                       // nur ustunida muallaq chang
      const rad = r() ** 0.6 * 1.25
      qoy(rad * Math.cos(th), (r() - 0.5) * 3.2, rad * Math.sin(th) * 0.7)
    }
  }
  return a
}

// --- Sheyderlar ---

const VS_FON = 'attribute vec2 aPos; void main(){ gl_Position = vec4(aPos, 0., 1.); }'

const fsFon = (okt) => `precision highp float;
uniform vec2 uRes; uniform float uTime; uniform vec2 uSich; uniform vec3 uA, uB, uC; uniform vec2 uMarkaz; uniform float uQora, uNur;
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y); }
float fbm(vec2 p){ float v = 0., a = .5; for (int i = 0; i < ${okt}; i++) { v += a * noise(p); p = p * 2.03 + vec2(17.1, 9.7); a *= .5; } return v; }
void main(){
  vec2 p = (gl_FragCoord.xy - .5 * uRes) / uRes.y;
  float nisbat = uRes.x / uRes.y, t = uTime * .05;
  // Tuman: sekin suzadi, nurni «ko'rinadigan» qiladi
  vec2 q = vec2(fbm(p * 1.1 + vec2(0., t)), fbm(p * 1.1 + vec2(5.2, 1.3 - t)));
  float tuman = fbm(p * 1.3 + 1.8 * q + vec2(t * .7, -t * .4));
  vec3 c = mix(uA, uB, smoothstep(.25, .85, tuman) * .55 + smoothstep(-.6, .7, p.y) * .25);
  // Nur manbai ekrandan yuqorida, shakl tepasida; nur shakl tomon tushadi va kursorga qarab biroz og'adi
  vec2 nishon = vec2(uMarkaz.x * nisbat * .5, uMarkaz.y * .5);
  vec2 manba = vec2(nishon.x + .16, .78);
  vec2 d = p - manba; float uz = length(d);
  float burchak = atan(d.x, -d.y);                                   // 0 — tik pastga
  float ogish = atan(nishon.x - manba.x, manba.y - nishon.y) + (uSich.x - .5) * .22;
  float konus = smoothstep(.5, .0, abs(burchak - ogish));
  float tola = fbm(vec2(burchak * 11., t * 1.6)) * .62 + fbm(vec2(burchak * 27. + 4., -t * 1.1)) * .38;   // nur tolalari
  tola = smoothstep(.3, .72, tola);
  float nur = konus * (.3 + .7 * tola) * exp(-uz * .62) * (.55 + .8 * tuman);
  vec3 tilla = mix(vec3(1., .8, .54), uC, .35);
  c += tilla * nur * 1.25 * uNur;
  // Nur tushgan joyda poldagi yorug' dog'
  vec2 pol = (p - vec2(nishon.x, -.47)) * vec2(1., 3.4);
  c += tilla * exp(-dot(pol, pol) * 2.6) * .22 * uNur;
  vec2 sp = (gl_FragCoord.xy / uRes * 2. - 1. - uMarkaz) * vec2(nisbat, 1.);   // shakl ortida fon qorayadi — zarrachalar ajralib turadi
  c *= mix(1. - uQora * .5, 1., smoothstep(.1, 1.15, length(sp)));
  c *= mix(.42, 1., smoothstep(1.35, .25, length(p * vec2(.8, 1.))));
  c += (hash(gl_FragCoord.xy + uTime) - .5) * .02;
  gl_FragColor = vec4(c, 1.);}`

const VS_ZARRA = `attribute vec3 aP0, aP1, aP2, aP3, aP4, aP5; attribute vec4 aR;
uniform float uT, uTime, uBurA, uBurB, uMasshtab, uNisbat, uOlcham, uShaffof;
uniform vec2 uSurilish, uSich, uEgilish;
varying float vA; varying vec3 vRang;
vec3 shakl(float i){ if (i < .5) return aP5; if (i < 1.5) return aP1; if (i < 2.5) return aP2; if (i < 3.5) return aP3; if (i < 4.5) return aP4; return aP0; }
vec3 burY(vec3 p, float a){ float c = cos(a), s = sin(a); return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z); }
vec3 burX(vec3 p, float a){ float c = cos(a), s = sin(a); return vec3(p.x, c * p.y - s * p.z, s * p.y + c * p.z); }
void main(){
  float seg = clamp(uT, 0., 5.); float i = min(floor(seg), 4.); float fr = seg - i;
  float kech = aR.x * .4; float tt = smoothstep(kech, kech + .6, fr);
  vec3 p = mix(burY(shakl(i), uBurA), burY(shakl(i + 1.), uBurB), tt);
  float yoy = sin(tt * 3.14159);                                     // o'tish paytida zarrachalar girdobga sochiladi
  p += yoy * vec3(sin(aR.y * 40. + uTime * .9), cos(aR.z * 37. + uTime * .7), sin(aR.w * 51. + uTime * .8)) * .55;
  p.y += sin(uTime * .8 + aR.z * 6.283) * .012;
  p = burY(burX(p, uEgilish.y), uEgilish.x);
  float pz = 1. / (3.4 - p.z);
  vec2 n = p.xy * pz * uMasshtab * 2.2; n.x /= uNisbat; n += uSurilish;
  vec2 d = (n - uSich) * vec2(uNisbat, 1.); float itar = smoothstep(.3, 0., length(d));   // kursor zarrachalarni itaradi
  n += normalize(d + 1e-4) / vec2(uNisbat, 1.) * itar * .085;
  gl_Position = vec4(n, 0., 1.);
  float milt = .6 + .4 * sin(uTime * (1.5 + aR.w * 3.) + aR.y * 30.);
  gl_PointSize = uOlcham * (.45 + aR.w * 1.25) * pz * 3.4 * (1. + itar * 1.6) * mix(1., 1.5, yoy);
  vA = uShaffof * milt * (.5 + .5 * aR.z);
  vRang = aR.y < .4 ? vec3(1., .96, .9) : (aR.y < .88 ? vec3(1., .78, .5) : vec3(.78, .86, 1.));
}`

const FS_ZARRA = `precision mediump float; varying float vA; varying vec3 vRang;
void main(){ float d = length(gl_PointCoord - .5) * 2.; float a = smoothstep(1., 0., d); a *= a; gl_FragColor = vec4(vRang * a * vA, a * vA); }`

// Har sahna uchun fon ranglari (A, B, C) — EZAZ to'q ko'ki va tillasi, oq matn o'qiladigan chuqurlikda
const hex = (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255]
const PALITRA = [
  ['#060b15', '#1a2c47', '#e0b27c'],   // toj
  ['#070d18', '#1c3050', '#cc9866'],   // kalendar
  ['#080f1c', '#223a5e', '#e4c196'],   // uzuklar
  ['#070d18', '#1e3354', '#d8a56c'],   // grafik
  ['#060b15', '#182a44', '#b89a78'],   // chang
  ['#070d18', '#1f3556', '#e0b27c'],   // libos (yakun)
].map((p) => p.map(hex))
const BURILISH = [0.55, 0, 1, 0, 0.15, 0]   // >0 — aylanadi (tezligi), 0 — faqat u yoqdan bu yoqqa tebranadi
const NUR = [1, 0.55, 0.7, 0.6, 0.35, 0.9]  // nur ustunining kuchi har sahnada
// 0-sahna (bosh kadr): nur ustunida muallaq toj
const KENG = { sur: [[0.4, 0.14], [0.42, 0], [0.42, 0], [0.42, 0], [0, 0], [0, 0]], mas: [0.78, 0.95, 1, 0.95, 1.45, 0.8], shaf: [1, 1, 1, 1, 0.38, 0.45] }
const TOR = { sur: [[0, 0.36], [0, 0.42], [0, 0.42], [0, 0.42], [0, 0], [0, 0.3]], mas: [0.56, 0.58, 0.6, 0.58, 1.15, 0.5], shaf: [1, 1, 1, 1, 0.38, 0.4] }
function dastur(gl, vs, fs, joylar = []) {
  const yig = (tur, manba) => {
    const s = gl.createShader(tur); gl.shaderSource(s, manba); gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s))
    return s
  }
  const p = gl.createProgram()
  gl.attachShader(p, yig(gl.VERTEX_SHADER, vs)); gl.attachShader(p, yig(gl.FRAGMENT_SHADER, fs))
  joylar.forEach((nom, i) => gl.bindAttribLocation(p, i, nom))
  gl.linkProgram(p)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p))
  const u = {}
  for (let i = 0, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS); i < n; i++) { const nom = gl.getActiveUniform(p, i).name; u[nom] = gl.getUniformLocation(p, nom) }
  return { p, u }
}

export function sahnaYarat(canvas) {
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false, powerPreference: 'high-performance' })
  if (!gl) return null
  const kichik = Math.min(window.innerWidth, window.innerHeight) < 700
  const N = kichik ? 9000 : 22000
  let fon, zarra
  try {
    fon = dastur(gl, VS_FON, fsFon(kichik ? 3 : 4), ['aPos'])
    zarra = dastur(gl, VS_ZARRA, FS_ZARRA, ['aP0', 'aP1', 'aP2', 'aP3', 'aP4', 'aP5', 'aR'])
  } catch { return null }

  const bufer = (malumot) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, malumot, gl.STATIC_DRAW); return b }
  const uchburchak = bufer(new Float32Array([-1, -1, 3, -1, -1, 3]))
  // toj (bosh kadr) va kalendar (1-kadr) o'rniga chang: bosh kadrda qasr videosi, 1-kadrda libos videosi turadi
  const shakllar = [libos(N), chang(N), uzuklar(N), grafik(N), chang(N), chang(N)].map(bufer)
  const tasodif = new Float32Array(N * 4)
  for (let i = 0; i < tasodif.length; i++) tasodif[i] = r()
  const tasodifBuf = bufer(tasodif)

  let eni = 0, boyi = 0, dpr = 1, kadr = 0, maqsad = 0, T = 0
  const sich = { x: 0.5, y: 0.5, mx: 0.5, my: 0.5 }
  const olcham = () => {
    dpr = Math.min(window.devicePixelRatio || 1, kichik ? 1.25 : 1.5)
    eni = Math.round(window.innerWidth * dpr); boyi = Math.round(window.innerHeight * dpr)
    canvas.width = eni; canvas.height = boyi
    gl.viewport(0, 0, eni, boyi)
  }
  olcham()

  const orali = (jadval, t) => { const i = Math.min(4, Math.floor(t)), f = t - i; return jadval[i] + (jadval[i + 1] - jadval[i]) * f }
  // Libos to'liq aylanmaydi: old tomondan ko'rinishi tanish, shuning uchun kengroq tebranadi
  const TEBRANISH = [0.5, 0.2, 0, 0.22, 0, 0.5]
  const burchak = (i, vaqt) => (BURILISH[i] > 0 ? vaqt * 0.28 * BURILISH[i] : Math.sin(vaqt * 0.38) * TEBRANISH[i])
  const bosh = performance.now()

  const chiz = (hozir) => {
    kadr = requestAnimationFrame(chiz)
    const vaqt = (hozir - bosh) / 1000
    T += (maqsad - T) * 0.07
    sich.x += (sich.mx - sich.x) * 0.08; sich.y += (sich.my - sich.y) * 0.08
    const t = Math.min(5, Math.max(0, T)), i = Math.min(4, Math.floor(t)), f = t - i
    const nisbat = eni / boyi, j = nisbat < 1.1 ? TOR : KENG
    const surX = j.sur[i][0] + (j.sur[i + 1][0] - j.sur[i][0]) * f, surY = j.sur[i][1] + (j.sur[i + 1][1] - j.sur[i][1]) * f

    gl.disable(gl.BLEND)
    gl.useProgram(fon.p)
    gl.bindBuffer(gl.ARRAY_BUFFER, uchburchak)
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    for (let k = 1; k < 7; k++) gl.disableVertexAttribArray(k)
    gl.uniform2f(fon.u.uRes, eni, boyi); gl.uniform1f(fon.u.uTime, vaqt); gl.uniform2f(fon.u.uSich, sich.x, sich.y)
    ;['uA', 'uB', 'uC'].forEach((nom, k) => {
      const a = PALITRA[i][k], b = PALITRA[i + 1][k]
      gl.uniform3f(fon.u[nom], a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)
    })
    gl.uniform2f(fon.u.uMarkaz, surX, surY); gl.uniform1f(fon.u.uQora, orali(j.shaf, t) * 0.62); gl.uniform1f(fon.u.uNur, orali(NUR, t))
    gl.drawArrays(gl.TRIANGLES, 0, 3)

    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE)
    gl.useProgram(zarra.p)
    shakllar.forEach((b, k) => { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(k); gl.vertexAttribPointer(k, 3, gl.FLOAT, false, 0, 0) })
    gl.bindBuffer(gl.ARRAY_BUFFER, tasodifBuf); gl.enableVertexAttribArray(6); gl.vertexAttribPointer(6, 4, gl.FLOAT, false, 0, 0)
    const u = zarra.u
    gl.uniform1f(u.uT, t); gl.uniform1f(u.uTime, vaqt)
    gl.uniform1f(u.uBurA, burchak(i, vaqt)); gl.uniform1f(u.uBurB, burchak(i + 1, vaqt))
    gl.uniform1f(u.uMasshtab, orali(j.mas, t)); gl.uniform1f(u.uNisbat, nisbat)
    gl.uniform1f(u.uOlcham, (kichik ? 2.6 : 3.3) * dpr); gl.uniform1f(u.uShaffof, orali(j.shaf, t))
    gl.uniform2f(u.uSurilish, surX, surY)
    gl.uniform2f(u.uSich, sich.x * 2 - 1, 1 - sich.y * 2)
    gl.uniform2f(u.uEgilish, (sich.x - 0.5) * 0.5, (sich.y - 0.5) * 0.3)
    gl.drawArrays(gl.POINTS, 0, N)
  }

  const surildi = (e) => { sich.mx = e.clientX / window.innerWidth; sich.my = e.clientY / window.innerHeight }
  window.addEventListener('resize', olcham)
  window.addEventListener('pointermove', surildi, { passive: true })
  kadr = requestAnimationFrame(chiz)

  return {
    sahnaga: (t) => { maqsad = t },
    darhol: (t) => { maqsad = T = t },   // silliqlashsiz — sinov uchun
    holat: () => ({ maqsad, T }),
    yop: () => {
      cancelAnimationFrame(kadr)
      window.removeEventListener('resize', olcham); window.removeEventListener('pointermove', surildi)
    },
  }
}
