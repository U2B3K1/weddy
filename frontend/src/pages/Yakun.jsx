// Sahifaning yakuniy qismi — ikkita yopishqoq sahna, har biri aylantirishga bog'langan:
//   1) Chaqiriq — atlasmotion.com uslubida: fon — aylantirishga bog'langan bitta uzluksiz video
//      (public/yakun/osmon.mp4: kamera tilla bulutlar orasidan pastga tushib, saroyni ochadi).
//      Ustida yozuvlar ketma-ket chiqadi: kichik «Navbat sizda.», keyin
//      «Saloningiz Libosaga tayyormi?» — harflari pastdan birin-ketin ko'tariladi,
//      izoh so'zlari xiradan yorqinga o'tadi, oxirida a'zo bo'lish tugmasi.
//   2) Raqamlar — markazda ramkasiz gologramma guldasta (WebGL), raqamlar bitta-bitta yorishib almashadi:
//      8 bo'lim, 16 hisobot, 14 kun sinov, 3 bosqichli kirish.
//   (Uchinchi — faqat «Libosa» yozuvli to'liq ekran video — sahnasi foydalanuvchi so'rovi bilan olib tashlangan.)
//
// Yozuvlar harakati CSS da: Reklama.jsx har [data-sahna] blokka aylantirish ulushini (--p, 0..1) yozib turadi,
// yakun.css shu o'zgaruvchidan foydalanadi. Bu faylda faqat chaqiriq fon videosining vaqti, gologramma
// guldastaning almashishi va kirish videosining ijro etilishi bor.
import { useEffect, useRef } from 'react'
import { gologrammaYarat } from './gologramma'
import './yakun.css'

// --- Chaqiriq ---
const SAVOL = "Saloningiz Libosaga tayyormi?"
// sarlavha uch bo'lakda, har harf o'z tartib raqami bilan (harflar birin-ketin ko'tariladi). Keng ekranda ikkinchi va
// uchinchi bo'lak bir qatorda turadi, telefonda har biri alohida qatorda — aks holda «tayyormi?» ekranga sig'maydi.
const SARLAVHA = (() => { let i = 0; return ['Saloningiz', 'Libosaga', 'tayyormi?'].map((qator) => [...qator].map((h) => [h, i++])) })()
const HARF_SONI = SARLAVHA.flat().filter(([, i]) => i >= 0).length
const KICHIK = ['Navbat', 'sizda.']
const IZOH = "Bron, zakaz, kassa va hisobot bitta tizimda. 14 kun bepul sinab ko'ring.".split(' ')

// --- Raqamlar ---
const RAQAMLAR = [[8, "bo'lim bitta tizimda"], [16, 'tayyor hisobot'], [14, 'kun bepul sinov'], [3, 'bosqichli himoyalangan kirish']]
const GULLAR = ['/gullar/1.png', '/gullar/2.png', '/gullar/3.png', '/gullar/4.png']
const LENTA = ['BRON', 'ZAKAZ', 'ZALOG', 'KASSA', 'KATALOG', 'FOYDA', 'HISOBOT']

export function Yakun({ onAzo }) {
  const chaqiriq = useRef(null) // «Chaqiriq» sahnasi va uning fon videosi (vaqti aylantirishga bog'lanadi)
  const osmon = useRef(null)
  const gul = useRef(null)   // «Raqamlar» sahnasi: yagona gologramma guldasta canvasi
  const hol = useRef(null)   // gologramma obyekti ({ tanla, yop })
  const raqam = useRef(null) // «Raqamlar» sahna bloki (scroll ulushini o'lchash uchun)

  // Chaqiriq foni: video o'zi ijro etilmaydi — vaqti (currentTime) aylantirishga bog'langan (QasrVideo.jsx dagi usul).
  // Bo'lim ekranga pastdan kira boshlaganda 0, yopishqoq sahna tugaganda — video oxiri.
  useEffect(() => {
    const B = chaqiriq.current, v = osmon.current
    if (!B || !v || matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined
    let maqsad = 0, joriy = 0, kadr = 0, korinadi = false
    const olch = () => {
      const r = B.getBoundingClientRect()
      maqsad = Math.min(1, Math.max(0, (window.innerHeight - r.top) / r.height))
    }
    const sil = () => {
      joriy += (maqsad - joriy) * 0.12
      // oldingi kadrga o'tish tugamaguncha yangisini so'ramaymiz — aks holda video sakrab yuradi
      if (v.duration && !v.seeking) {
        const t = joriy * (v.duration - 0.05)
        if (Math.abs(v.currentTime - t) > 0.03) v.currentTime = t
      }
      kadr = korinadi ? requestAnimationFrame(sil) : 0
    }
    const kuzat = new IntersectionObserver(([y]) => {
      korinadi = y.isIntersecting
      if (korinadi && !kadr) { olch(); kadr = requestAnimationFrame(sil) }
    })
    kuzat.observe(B)
    window.addEventListener('scroll', olch, { passive: true })
    window.addEventListener('resize', olch)
    return () => { cancelAnimationFrame(kadr); kuzat.disconnect(); window.removeEventListener('scroll', olch); window.removeEventListener('resize', olch) }
  }, [])

  // Raqamlar: yagona katta, ramkasiz guldasta gologrammasi — aylantirish ulushiga qarab faol guldastani almashadi.
  useEffect(() => {
    let tirik = true
    const tanlaIndeks = () => {
      const blok = raqam.current; if (!blok || !hol.current) return
      const r = blok.getBoundingClientRect(); const yol = r.height - window.innerHeight
      const xom = yol > 0 ? -r.top / yol : (window.innerHeight - r.top) / (window.innerHeight + r.height)
      const p = Math.min(1, Math.max(0, xom))
      const q = Math.min(1, Math.max(0, (p - .04) / .92))
      hol.current.tanla(Math.min(GULLAR.length - 1, Math.floor(q * GULLAR.length)))
    }
    gologrammaYarat(gul.current, GULLAR, undefined, { markaz: [.5, .5], masshtab: .19 }).then((g) => {
      if (tirik) { hol.current = g; tanlaIndeks() } else g?.yop()
    })
    const aylan = () => requestAnimationFrame(tanlaIndeks)
    window.addEventListener('scroll', aylan, { passive: true })
    window.addEventListener('resize', aylan)
    tanlaIndeks()
    return () => { tirik = false; window.removeEventListener('scroll', aylan); window.removeEventListener('resize', aylan); hol.current?.yop() }
  }, [])

  return (
    <div className="rk-yk">
      {/* 1-sahna: Chaqiriq — aylantirishga bog'langan fon videosi ustida yozuvlar ketma-ket chiqadi */}
      <div className="rk-yk-yol rk-yk-chaqiriq" data-sahna data-kir data-t="5" ref={chaqiriq} style={{ '--harf': HARF_SONI, '--soz': IZOH.length }}>
        <div className="rk-yk-pin">
          <video ref={osmon} className="rk-yk-osmon" src="/yakun/osmon.mp4" poster="/yakun/osmon.jpg" muted playsInline preload="auto" aria-hidden="true" />
          <p className="rk-yk-kichik" aria-hidden="true">{KICHIK.map((soz, i) => <i key={soz} style={{ '--i': i }}>{soz}</i>)}</p>
          <div className="rk-yk-savol">
            <h2 aria-label={SAVOL}>
              {SARLAVHA.map((qator, k) => (
                <span key={k} aria-hidden="true">
                  {qator.map(([h, i], n) => (i < 0 ? ' ' : <i key={n} style={{ '--i': i }}>{h}</i>))}
                </span>
              ))}
            </h2>
          </div>
          <div className="rk-yk-past">
            <p className="rk-yk-izoh" aria-label={IZOH.join(' ')}>
              {IZOH.map((soz, i) => <i key={i} aria-hidden="true" style={{ '--i': i }}>{soz} </i>)}
            </p>
            <a className="rk-tugma rk-tugma-katta" href="#azo" onClick={onAzo} data-magnit><span>A'zo bo'lish</span></a>
          </div>
        </div>
      </div>

      {/* 2-sahna: markazda ramkasiz gologramma guldasta, raqamlar bitta-bitta yorishib almashadi */}
      <div className="rk-yk-yol rk-yk-raqam" data-sahna data-kir ref={raqam}>
        <div className="rk-yk-pin">
          <img className="rk-yk-fon" src="/tashvish/fon-1.jpg" alt="" loading="lazy" />
          <p className="rk-ustki rk-yk-yorliq">Libosa raqamlarda</p>
          <span className="rk-yk-raqam-son" aria-hidden="true">
            {RAQAMLAR.map((_, i) => <i key={i} style={{ '--i': i }} />)}
          </span>
          <div className="rk-yk-yol-raqam">
            {RAQAMLAR.map(([son, matn], i) => (
              <div key={matn} className="rk-yk-son" style={{ '--i': i }}><b>{son}</b><span>{matn}</span></div>
            ))}
          </div>
          <div className="rk-yk-lenta" aria-hidden="true">
            <div>{[0, 1, 2].map((n) => <span key={n}>{LENTA.map((s) => <b key={s}>{s}<i>✦</i></b>)}</span>)}</div>
          </div>
          <div className="rk-yk-gul-qator" aria-hidden="true">
            <canvas ref={gul} />
          </div>
        </div>
      </div>
    </div>
  )
}
