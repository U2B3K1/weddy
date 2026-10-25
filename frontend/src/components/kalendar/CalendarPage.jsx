import { useEffect, useRef, useState } from 'react'
import CalendarGrid from './CalendarGrid'
import CalendarHeader from './CalendarHeader'
import { MAVZULAR } from './mavzular'
import { bugunIso, isoOch, oyQosh, oylarFarqi } from './sana'
import TanlovPaneli from './TanlovPaneli'
import './kalendar.css'

// Yangi zakaz sanasi: 1-bosish — olib ketish, 2-bosish — qaytarish kuni.
// Fon — ko'rsatilayotgan oy faslining oltin chiziqli rasmi (mavzular.js); u kalendar turgan blokning (Sana) o'ziga xira yoyiladi.
export default function CalendarPage({ dan, gacha, onTanla }) {
  const bugun = bugunIso()
  const [korinish, setKorinish] = useState(() => { const s = isoOch(dan || bugun); return { y: s.y, m: s.m } })
  const [yon, setYon] = useState(0) // animatsiya yo'nalishi
  const [fokus, setFokus] = useState(null)
  const klaviatura = useRef(false)

  // Qo'shni oylar rasmini oldindan yuklash — strelka bosilganda fon miltillamaydi
  useEffect(() => {
    for (const d of [-1, 1]) new Image().src = MAVZULAR[(korinish.m + d + 12) % 12].rasm
  }, [korinish.m])

  const almash = (n) => { if (!n) return; setYon(Math.sign(n)); setKorinish((k) => oyQosh(k, n)) }
  const fokusla = (kun) => {
    almash(oylarFarqi(korinish, isoOch(kun)))
    setFokus(kun)
  }
  const tanla = (kun) => {
    // Oraliq tayyor bo'lsa yoki boshidan oldingi kun bosilsa — yangi tanlov boshlanadi
    if (!dan || gacha || kun < dan) onTanla(kun, '')
    else onTanla(dan, kun)
  }

  const { y, m } = korinish
  const mavzu = MAVZULAR[m]

  return (
    <>
    <img key={mavzu.fasl} className="kalendar-fon" src={mavzu.rasm} alt="" decoding="async" />
    <section className="kuz" aria-label="Sana tanlash kalendari">
      <div className="kuz-ichi">
        <CalendarHeader y={y} m={m} onOy={almash} onYil={(n) => almash(n * 12)} />
        <CalendarGrid key={`${y}-${m}`} y={y} m={m} dan={dan} gacha={gacha} bugun={bugun} fokus={fokus}
          klaviatura={klaviatura} yon={yon} onTanla={tanla} onFokus={fokusla} />
        <TanlovPaneli dan={dan} gacha={gacha} onTozala={(k) => (k === 'dan' ? onTanla('', '') : onTanla(dan, ''))} />
      </div>
    </section>
    </>
  )
}
