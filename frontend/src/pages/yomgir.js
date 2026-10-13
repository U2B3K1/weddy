// Pastga oqayotgan tilla harflar — "Kelinlar" bo'limidagi fon ortidagi "raqamli yomg'ir".
// Kelinlar.jsx (bosh sahifa) va PlatformaFon.jsx (ichki platforma sahifalari) ikkalasi ham
// shu effektni ishlatadi, shuning uchun alohida faylga chiqarilgan.
export const BELGILAR = 'LIBOSAKELINLIBOSBRONZALOGQAYTARISH0123456789'

// Pastga oqayotgan harflar — tilla rangda, chetlarga yaqin quyuqroq (markazda xiraroq).
// Qaytarilgan funksiya — tozalash (cancelAnimationFrame + removeEventListener).
export function yomgirYarat(canvas) {
  const x = canvas.getContext('2d')
  let eni = 0, boyi = 0, ustunlar = [], kadr = 0
  const olcham = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    eni = canvas.clientWidth; boyi = canvas.clientHeight
    canvas.width = eni * dpr; canvas.height = boyi * dpr; x.setTransform(dpr, 0, 0, dpr, 0, 0)
    const n = Math.floor(eni / 26)
    ustunlar = Array.from({ length: n }, (_, i) => ({ x: i * 26 + 8, y: Math.random() * boyi, v: 30 + Math.random() * 90, uz: 8 + Math.random() * 22, s: Math.random() }))
  }
  let oldingi = performance.now()
  const chiz = (h) => {
    const dt = Math.min(.05, (h - oldingi) / 1000); oldingi = h
    x.clearRect(0, 0, eni, boyi); x.font = '11px monospace'
    for (const u of ustunlar) {
      u.y += u.v * dt; if (u.y - u.uz * 14 > boyi) { u.y = -Math.random() * 200; u.s = Math.random() }
      const chet = Math.abs(u.x / eni - .5) * 2                 // markazda xiraroq — kontent ochiq qolsin
      for (let j = 0; j < u.uz; j++) {
        const y = u.y - j * 14; if (y < -14 || y > boyi) continue
        const a = (1 - j / u.uz) * (.08 + chet * .32) * (j === 0 ? 2.2 : 1)
        x.fillStyle = `rgba(228, 205, 170, ${a})`
        x.fillText(BELGILAR[(Math.floor(h / 120 + u.x + j * 7)) % BELGILAR.length], u.x, y)
      }
    }
    kadr = requestAnimationFrame(chiz)
  }
  olcham(); window.addEventListener('resize', olcham); kadr = requestAnimationFrame(chiz)
  return () => { cancelAnimationFrame(kadr); window.removeEventListener('resize', olcham) }
}
