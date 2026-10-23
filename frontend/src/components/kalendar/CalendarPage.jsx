import { useEffect, useRef, useState } from 'react'
import { sanaMatni } from '../../api'
import CalendarGrid from './CalendarGrid'
import CalendarHeader from './CalendarHeader'
import { MAVZULAR } from './mavzular'
import { bugunIso, isoOch, kunlarSoni, oyQosh, oylarFarqi } from './sana'
import './kalendar.css'

// Yangi zakaz sanasi: 1-bosish — olib ketish, 2-bosish — qaytarish kuni.
// Fon — ko'rsatilayotgan oyning fotosi (mavzular.js), fasl va oyga qarab almashadi.
export default function CalendarPage({ dan, gacha, onTanla }) {
  const bugun = bugunIso()
  const [korinish, setKorinish] = useState(() => { const s = isoOch(dan || bugun); return { y: s.y, m: s.m } })
  const [yon, setYon] = useState(0) // animatsiya yo'nalishi
  const [fokus, setFokus] = useState(null)
  const klaviatura = useRef(false)

  // Qo'shni oylar fotosini oldindan yuklash — strelka bosilganda fon miltillamaydi
  useEffect(() => {
    for (const d of [-1, 1]) new Image().src = MAVZULAR[(korinish.m + d + 12) % 12].rasm
  }, [korinish.m])

  const almash = (n) => { if (!n) return; setYon(Math.sign(n)); setKorinish((k) => oyQosh(k, n)) }
  const bugunOy = isoOch(bugun)
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
    <section className="kuz" style={{ '--k-urgu': mavzu.urgu, '--k-parda': mavzu.parda }} aria-label="Sana tanlash kalendari">
      <img key={m} className="kuz-foto" src={mavzu.rasm} alt="" decoding="async" />
      <div className="kuz-parda" aria-hidden="true" />
      <div className="kuz-ichi">
        <CalendarHeader y={y} m={m} fasl={mavzu.nomi} onOy={almash} onYil={(n) => almash(n * 12)}
          onBugun={() => almash(oylarFarqi(korinish, bugunOy))} bugunOyida={y === bugunOy.y && m === bugunOy.m} />
        <CalendarGrid key={`${y}-${m}`} y={y} m={m} dan={dan} gacha={gacha} bugun={bugun} fokus={fokus}
          klaviatura={klaviatura} yon={yon} onTanla={tanla} onFokus={fokusla} />
        <p className="kuz-izoh">
          {!dan && 'Olib ketish kunini tanlang.'}
          {dan && !gacha && <>Olib ketish: <b>{sanaMatni(dan)}</b> — endi qaytarish kunini tanlang.</>}
          {dan && gacha && <>Olib ketish: <b>{sanaMatni(dan)}</b> · Qaytarish: <b>{sanaMatni(gacha)}</b> · {kunlarSoni(dan, gacha) + 1} kun</>}
        </p>
      </div>
    </section>
  )
}
