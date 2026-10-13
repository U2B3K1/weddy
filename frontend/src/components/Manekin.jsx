import { useRef, useState } from 'react'
import { xatoMatni } from '../api'

const W = 800
const H = 1200
const MIN = 0.05
const MAKS = 3
const chegara = (v, a, b) => Math.min(b, Math.max(a, v))

// FT-5.1: bitta standart 2D manekin (ayol qomati, old tomondan); gavda turi tanlanmaydi.
const MANEKIN_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="#faf7fb"/>
<g fill="#e4dce6" stroke="#cfc4d2" stroke-width="3">
<ellipse cx="400" cy="1150" rx="150" ry="22"/>
<rect x="390" y="800" width="20" height="350"/>
<ellipse cx="400" cy="135" rx="60" ry="76"/>
<path d="M372 205 L372 250 C330 262 268 268 246 304 C230 340 238 430 262 480 C282 528 300 560 300 606 C298 668 262 724 252 800 C300 830 500 830 548 800 C538 724 502 668 500 606 C500 560 518 528 538 480 C562 430 570 340 554 304 C532 268 470 262 428 250 L428 205 Z"/>
</g></svg>`
const MANEKIN_URL = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(MANEKIN_SVG)}`

const rasmYukla = (src, cors) => new Promise((hal, rad) => {
  const img = new Image()
  if (cors) img.crossOrigin = 'anonymous'
  img.onload = () => hal(img)
  img.onerror = () => rad(new Error('Rasmni yuklab bo\'lmadi.'))
  img.src = src
})

// 4.5: manekin ustida qatlamlar — libos, ustidan fata va toj kabi aksessuarlar (FT-5.2).
// Har bir qatlam: { kalit, nomi, rasm, x, y, kattalik, saqla(body), standart? }. Tanlangan qatlam barmoq yoki sichqoncha bilan suriladi va
// kattalashtiriladi; to'g'rilangan holat saqlanadi va keyingi safar o'zi qo'yiladi (FT-5.3).
export default function Manekin({ sarlavha, faylNomi = 'manekin', qatlamlar, onYopish, onSaqlandi }) {
  const [h, setH] = useState(() => qatlamlar.map((q) => ({ x: q.x, y: q.y, k: q.kattalik })))
  const [asl, setAsl] = useState(() => qatlamlar.map((q) => ({ x: q.x, y: q.y, k: q.kattalik })))
  const [faol, setFaol] = useState(0)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const sahna = useRef(null)
  const barmoqlar = useRef(new Map())
  const boshi = useRef(null)

  const ozgarganlar = h.map((v, i) => v.x !== asl[i].x || v.y !== asl[i].y || v.k !== asl[i].k)
  const yangila = (fn) => setH((s) => s.map((v, i) => (i === faol ? fn(v) : v)))

  const bosildi = (e) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    barmoqlar.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    const p = [...barmoqlar.current.values()]
    boshi.current = { ...h[faol], p0: p[0], masofa: p.length > 1 ? Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) : null }
  }
  const surildi = (e) => {
    if (!barmoqlar.current.has(e.pointerId) || !boshi.current) return
    barmoqlar.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    const p = [...barmoqlar.current.values()]
    const b = boshi.current
    const r = sahna.current.getBoundingClientRect()
    if (p.length > 1 && b.masofa) { // ikki barmoq — kattalashtirish
      const m = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y)
      yangila((s) => ({ ...s, k: chegara(b.k * (m / b.masofa), MIN, MAKS) }))
    } else {
      yangila((s) => ({ ...s, x: chegara(b.x + (p[0].x - b.p0.x) / r.width, -1, 1), y: chegara(b.y + (p[0].y - b.p0.y) / r.height, -1, 1) }))
    }
  }
  const qoyildi = (e) => {
    barmoqlar.current.delete(e.pointerId)
    const p = [...barmoqlar.current.values()]
    boshi.current = p.length ? { ...h[faol], p0: p[0], masofa: null } : null
  }
  const gildirak = (e) => yangila((s) => ({ ...s, k: chegara(s.k * (e.deltaY < 0 ? 1.05 : 0.95), MIN, MAKS) }))

  const saqla = async () => {
    setXabar({ turi: '', matn: '' })
    try {
      for (let i = 0; i < qatlamlar.length; i += 1) {
        if (ozgarganlar[i]) await qatlamlar[i].saqla({ x: h[i].x, y: h[i].y, kattalik: h[i].k })
      }
      setAsl(h)
      setXabar({ turi: 'ok', matn: 'Joylashuv saqlandi — keyingi safar shu holatda ochiladi.' })
      onSaqlandi?.(h.map((v, i) => ({ kalit: qatlamlar[i].kalit, x: v.x, y: v.y, kattalik: v.k })))
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }

  // FT-5.4: manekin rasmini saqlash; qurilmada «ulashish» bo'lsa, mijozga Telegram orqali shu yerdan yuboriladi
  const rasmga = async () => {
    setXabar({ turi: '', matn: '' })
    try {
      const [fon, ...rasmlar] = await Promise.all([rasmYukla(MANEKIN_URL), ...qatlamlar.map((q) => rasmYukla(q.rasm, true))])
      const c = document.createElement('canvas')
      c.width = W; c.height = H
      const g = c.getContext('2d')
      g.drawImage(fon, 0, 0, W, H)
      rasmlar.forEach((img, i) => {
        g.save()
        g.translate(W / 2 + h[i].x * W, H / 2 + h[i].y * H)
        g.scale(h[i].k, h[i].k)
        g.drawImage(img, -W / 2, -H / 2, W, H)
        g.restore()
      })
      const blob = await new Promise((hal) => c.toBlob(hal, 'image/png'))
      const nom = `${faylNomi}-manekin.png`
      const fayl = new File([blob], nom, { type: 'image/png' })
      if (navigator.canShare?.({ files: [fayl] })) {
        await navigator.share({ files: [fayl], title: sarlavha })
      } else {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = nom
        a.click()
        URL.revokeObjectURL(a.href)
        setXabar({ turi: 'ok', matn: 'Rasm yuklab olindi — mijozga Telegram orqali yuborishingiz mumkin.' })
      }
    } catch (e) {
      if (e?.name !== 'AbortError') setXabar({ turi: 'xato', matn: e.message || "Rasmni tayyorlab bo'lmadi." })
    }
  }

  return (
    <div className="manekin-oyna" role="dialog" aria-label={`${sarlavha} — manekinda`}>
      <div className="manekin-ichki stack">
        <div className="qator manekin-sarlavha">
          <b>{sarlavha}</b>
          <button type="button" className="ikkinchi kichik" onClick={onYopish}>Yopish</button>
        </div>
        <div ref={sahna} className="manekin-sahna suriladi" style={{ backgroundImage: `url("${MANEKIN_URL}")` }}
          onPointerDown={bosildi} onPointerMove={surildi} onPointerUp={qoyildi} onPointerCancel={qoyildi} onWheel={gildirak}>
          {qatlamlar.map((q, i) => (
            <img key={q.kalit} src={q.rasm} alt={q.nomi} draggable={false} className={i === faol && qatlamlar.length > 1 ? 'faol' : ''}
              style={{ transform: `translate(${h[i].x * 100}%, ${h[i].y * 100}%) scale(${h[i].k})` }} />
          ))}
        </div>
        {qatlamlar.length > 1 && (
          <div className="qator manekin-qatlamlar" role="group" aria-label="Suriladigan qatlam">
            {qatlamlar.map((q, i) => (
              <button key={q.kalit} type="button" className={`kichik ${i === faol ? '' : 'ikkinchi'}`} aria-pressed={i === faol} onClick={() => setFaol(i)}>
                {q.nomi}{ozgarganlar[i] ? ' •' : ''}
              </button>
            ))}
          </div>
        )}
        <label>Kattalik ({qatlamlar[faol].nomi}): {Math.round(h[faol].k * 100)}%
          <input type="range" min={MIN} max={MAKS} step="0.01" value={h[faol].k} onChange={(e) => yangila((s) => ({ ...s, k: Number(e.target.value) }))} />
        </label>
        <p className="malumot">
          {qatlamlar.length > 1 ? 'Qatlamni tanlang, so\'ng ' : ''}barmoq yoki sichqoncha bilan suring; ikki barmoq yoki g'ildirak bilan kattalashtiring.
        </p>
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <div className="qator">
          <button type="button" disabled={!ozgarganlar.some(Boolean)} onClick={saqla}>Joylashuvni saqlash</button>
          <button type="button" className="ikkinchi" onClick={() => yangila(() => qatlamlar[faol].standart || { x: 0, y: 0, k: 1 })}>Standart holat</button>
          <button type="button" className="ikkinchi" onClick={rasmga}>Rasmni saqlash / yuborish</button>
        </div>
      </div>
    </div>
  )
}
