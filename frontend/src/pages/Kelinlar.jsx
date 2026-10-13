// "Kelinlar" bo'limi — Lusion'dagi TEAM bo'limi uslubida: qorong'i gotik qasr fonida 5 ta kelin obrazi
// nuqtali gologramma bo'lib almashadi. Bo'lim ekranga "yopishib" turadi (sticky), aylantirganda obrazlar
// birin-ketin almashadi; portret ustini bossangiz keyingisiga o'tadi.
//
// Qatlamlar (pastdan yuqoriga):
//   1) .rk-kel-fon     — qorong'i qasr rasmi (xira, ko'k)
//   2) .rk-kel-yomgir  — pastga oqayotgan yaltiroq harflar ustunlari (2D canvas)
//   3) .rk-kel-tuval   — gologramma: portret nuqtalari (gologramma.js, WebGL)
//   4) HUD va matnlar  — [[ 001 ]] hisoblagich, shkala, sarlavha, obraz nomi, katta harf, izoh
//
// Qayerga: src/pages/Kelinlar.jsx (gologramma.js va kelinlar.css shu papkada).
// Reklama.jsx da: kartalar bo'limidan oldin —  <Kelinlar />  keyin  <Kartalar />  (kino bo'limi o'rnida).
import { useEffect, useRef, useState } from 'react'
import { gologrammaYarat } from './gologramma'
import { yomgirYarat } from './yomgir'
import './kelinlar.css'

const OBRAZLAR = [
  ['/kelinlar/1.jpg', 'Sirena', "Atlas, ochiq yelka, tanaga yopishgan siluet"],
  ['/kelinlar/2.jpg', 'Malika', "Hajmli tyul etak, yaltiroq bezak"],
  ['/kelinlar/3.jpg', "Nafis to'r", "To'r bilan qoplangan A-siluet"],
  ['/kelinlar/4.jpg', 'Zamonaviy', 'Minimal krep, uzun plash'],
  ['/kelinlar/5.jpg', 'Orzu', "Shaffof to'r yeng, uzun fata"],
]
// Katta tartib raqami (1–5) — gologramma: kvadratchalardan yig'ilgan, tilla-oq ranglarda, skaner chiziqlari bilan.
// Raqam katta (14×18) katakli to'rda, serif shriftda (tekis raqamli — Times) chiziladi — kichik to'rdagidek qo'pol chiqmaydi.
function Harf({ h }) {
  const ref = useRef(null)
  useEffect(() => {
    const c = ref.current; if (!c) return
    const W = 14, H = 18, k = c.width / W, z = c.getContext('2d')
    const t = document.createElement('canvas'); t.width = W; t.height = H
    const tx = t.getContext('2d', { willReadFrequently: true })
    tx.fillStyle = '#fff'; tx.font = `bold ${H - 2}px "Times New Roman", Times, serif`
    tx.textAlign = 'center'; tx.textBaseline = 'alphabetic'
    const m = tx.measureText(h), asc = m.actualBoundingBoxAscent || H * .7, desc = m.actualBoundingBoxDescent || 0
    tx.fillText(h, W / 2, (H + asc - desc) / 2)      // raqamni to'rning o'rtasiga joylaymiz
    const px = tx.getImageData(0, 0, W, H).data
    z.clearRect(0, 0, c.width, c.height)
    for (let i = 0; i < W * H; i++) {
      const a = px[i * 4 + 3] / 255; if (a < .4) continue
      const y = Math.floor(i / W), q = y / H
      // tepadan pastga: fil suyagidan tillaga
      z.fillStyle = `rgba(${Math.round(251 - q * 23)}, ${Math.round(246 - q * 53)}, ${Math.round(238 - q * 88)}, ${.7 + a * .3})`
      z.fillRect((i % W) * k + 1, y * k + 1, k - 2, k - 2)
    }
  }, [h])
  return <canvas ref={ref} className="rk-kel-harf" width={280} height={360} aria-hidden="true" />
}

export function Kelinlar() {
  const bolim = useRef(null), tuval = useRef(null), yomgir = useRef(null), g = useRef(null)
  const [i, setI] = useState(0)

  useEffect(() => {
    let yop = () => {}, tirik = true
    gologrammaYarat(tuval.current, OBRAZLAR.map((o) => o[0])).then((x) => { if (tirik) g.current = x; else x?.yop() })
    yop = yomgirYarat(yomgir.current)
    // Aylantirish: bo'lim ichidagi yo'lni 5 ga bo'lib, qaysi obraz ko'rinishini aniqlaymiz
    const olch = () => {
      const r = bolim.current.getBoundingClientRect(), yol = r.height - window.innerHeight
      // yol 0 bo'lsa (oyna o'lchamsiz — masalan, yig'ib qo'yilgan) bo'linma NaN beradi va OBRAZLAR[NaN] sahifani qulatadi
      const p = yol > 0 ? Math.min(.999, Math.max(0, -r.top / yol)) : 0
      const n = Math.floor(p * OBRAZLAR.length)
      setI(n); g.current?.tanla(n)
      bolim.current.style.setProperty('--kel-p', ((p * OBRAZLAR.length) % 1).toFixed(3))
    }
    window.addEventListener('scroll', olch, { passive: true }); olch()
    return () => { tirik = false; yop(); g.current?.yop(); window.removeEventListener('scroll', olch) }
  }, [])

  // Portretni bosish — keyingi obrazning aylantirish nuqtasiga silliq o'tish
  const keyingi = () => {
    const r = bolim.current.getBoundingClientRect(), yol = r.height - window.innerHeight
    const top = window.scrollY + r.top + yol * ((i + 1) % OBRAZLAR.length + .05) / OBRAZLAR.length
    window.scrollTo({ top, behavior: 'smooth' })
  }

  const [, nom, izoh] = OBRAZLAR[i]
  return (
    <div className="rk-kelinlar" ref={bolim} id="kelinlar" data-sahna data-kir>
      <div className="rk-kel-yopishqoq">
        <img className="rk-kel-fon" src="/kelinlar/saroy.jpg" alt="" aria-hidden="true" />
        <i className="rk-kel-aura" aria-hidden="true" />
        <canvas className="rk-kel-yomgir" ref={yomgir} aria-hidden="true" />
        <canvas className="rk-kel-tuval" ref={tuval} onClick={keyingi} aria-label="Keyingi obraz" />

        <div className="rk-kel-hud" aria-hidden="true">
          <span className="rk-kel-raqam">[[&nbsp;&nbsp;&nbsp;{String(i + 1).padStart(3, '0')}&nbsp;&nbsp;&nbsp;]]</span>
          <span className="rk-kel-shkala" /><span className="rk-kel-nuqtalar" />
        </div>
        <h2 className="rk-kel-sarlavha">Obrazlar</h2>

        <div className="rk-kel-ism" key={i}>
          <p><b>::</b> {nom}</p>
          <small>Libos uslubi<br />{izoh}</small>
          <i className="rk-kel-chiziq" />
        </div>
        <Harf key={`harf${i}`} h={String(i + 1)} />
        <p className="rk-kel-matn">
          Har bir libosning o'z obrazi bor. Libosa katalogida har biri rasmi, o'lchami, narxi
          va bandlik kalendari bilan saqlanadi — mijozga to'g'ri obrazni bir zumda topasiz.
        </p>
      </div>
    </div>
  )
}
