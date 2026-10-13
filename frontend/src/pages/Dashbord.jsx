import { useCallback, useEffect, useState } from 'react'
import { dashbord, filiallar, som, xatoMatni } from '../api'

const KUNLAR = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba']
const OYLAR = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']

// KPI karta belgilari — ixcham stroke SVG (Lucide uslubi), yangi bog'liqlik talab qilmaydi.
const BELGILAR = {
  tushum: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></>),
  daromad: (<><path d="M22 7l-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>),
  foyda: (<><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" /><path d="M3 5v14a2 2 0 0 0 2 2h16v-5" /><path d="M18 12a2 2 0 0 0 0 4h4v-4Z" /></>),
  bandlik: (<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>),
  soat: (<><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>),
  zakaz: (<><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></>),
}
const Ikona = ({ nom }) => (
  <svg className="kpi-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {BELGILAR[nom]}
  </svg>
)

// 6.5: rahbar dashbordi — faqat asosiy ko'rsatgichlar (KPI).
// Qolgan tafsilotlar (P&L, bildirishnomalar, grafik) «Hisobot» bo'limida.
export default function Dashbord({ onBolim }) {
  const [d, setD] = useState(null)
  const [davr, setDavr] = useState('oy') // FT-19.2: bugun, hafta, oy
  const [fil, setFil] = useState([])
  const [pnlFilial, setPnlFilial] = useState('')
  const [xato, setXato] = useState('')

  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const yukla = useCallback(async () => {
    try { setD(await dashbord(davr, pnlFilial)) } catch (e) { setXato(xatoMatni(e)) }
  }, [davr, pnlFilial])
  useEffect(() => {
    yukla()
    const t = setInterval(yukla, 60000) // FT-19.1: har 1 daqiqada o'zi yangilanadi
    return () => clearInterval(t)
  }, [yukla])

  if (!d) {
    if (xato) return <p className="xato">{xato}</p>
    return (
      <div className="dashbord-sahifa stack" aria-busy="true">
        <div className="dashbord-skelet skelet-bosh" />
        <div className="kpi-tor">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="kpi dashbord-skelet skelet-kpi" />)}
        </div>
      </div>
    )
  }
  const { bugun, shu_oy: oyb } = d
  const hozir = new Date()
  const bugunSana = `${KUNLAR[hozir.getDay()]}, ${hozir.getDate()}-${OYLAR[hozir.getMonth()]}`
  const DAVR = { bugun: 'Bugun', hafta: 'Shu hafta', oy: 'Shu oy' }

  return (
    <div className="dashbord-sahifa stack">
      {xato && <p className="xato">{xato}</p>}

      {/* Sarlavha va filtrlar — bir qatorda, professional ko'rinish */}
      <header className="dashbord-bosh">
        <div className="dashbord-sarlavha">
          <h1>Dashbord</h1>
          <span className="sana">{bugunSana}</span>
        </div>
        <div className="oraliq" />
        <div className="segment">
          {Object.entries(DAVR).map(([k, nom]) => (
            <button key={k} type="button" className={davr === k ? '' : 'ikkinchi'} onClick={() => setDavr(k)}>{nom}</button>
          ))}
        </div>
        {fil.length > 0 && (
          <select value={pnlFilial} aria-label="Filial" onChange={(e) => setPnlFilial(e.target.value)}>
            <option value="">Butun salon</option>
            {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
          </select>
        )}
      </header>
      {pnlFilial && <p className="malumot">Ko'rsatgichlar tanlangan filial bo'yicha.</p>}

      {/* Bugun — tezkor xulosa (Tushum, Smena, Olib/qaytar) — chap paneldan ko'chirildi */}
      <section className="bugun-widget">
        <button type="button" onClick={() => onBolim('hisobotlar')}>
          <span className="bugun-nom">Tushum</span>
          <b>{som(bugun.tushum_jami)}</b>
        </button>
        <button type="button" onClick={() => onBolim('kassa')}>
          <span className="bugun-nom">Smena</span>
          <b>{bugun.smena_ochiq ? 'ochiq' : 'yopiq'}</b>
        </button>
        <button type="button" onClick={() => onBolim('bosh')}>
          <span className="bugun-nom">Olib / qaytar</span>
          <b>{bugun.olib_ketiladi} / {bugun.qaytariladi}</b>
        </button>
      </section>

      <div className="kpi-tor">
        <div className="kpi kpi-asosiy">
          <span className="kpi-bosh"><Ikona nom="tushum" /><span className="kpi-nom">Bugun tushum</span></span>
          <span className="kpi-qiymat">{som(bugun.tushum_jami)}</span>
          <span className="kpi-izoh">{bugun.smena_ochiq ? 'kassa ochiq' : 'kassa yopiq'}</span>
        </div>
        <div className="kpi">
          <span className="kpi-bosh"><Ikona nom="daromad" /><span className="kpi-nom">Davr daromad</span></span>
          <span className="kpi-qiymat">{som(oyb.hozirgi_daromad)}</span>
          <span className="kpi-izoh">{DAVR[d.davr.kalit]}</span>
        </div>
        <div className="kpi">
          <span className="kpi-bosh"><Ikona nom="foyda" /><span className="kpi-nom">Sof foyda</span></span>
          <span className={`kpi-qiymat${oyb.taxminiy_sof_foyda < 0 ? ' qizil' : ''}`}>{oyb.taxminiy_sof_foyda !== null ? som(oyb.taxminiy_sof_foyda) : '—'}</span>
          <span className="kpi-izoh">{oyb.taxminiy_sof_foyda !== null ? 'taxminiy' : 'faqat oy boʻyicha'}</span>
        </div>
        <div className="kpi">
          <span className="kpi-bosh"><Ikona nom="bandlik" /><span className="kpi-nom">Bandlik</span></span>
          <span className="kpi-qiymat">{d.oldinda.bandlik_foiz}%</span>
          <span className="kpi-izoh">{d.oldinda.kunlar} kun oldinda</span>
        </div>
        <div className="kpi">
          <span className="kpi-bosh"><Ikona nom="soat" /><span className="kpi-nom">Kutilayotgan daromad</span></span>
          <span className="kpi-qiymat">{som(oyb.kutilayotgan_daromad)}</span>
          <span className="kpi-izoh">hali tushmagan</span>
        </div>
        <div className="kpi">
          <span className="kpi-bosh"><Ikona nom="zakaz" /><span className="kpi-nom">Zakazlar</span></span>
          <span className="kpi-qiymat">{oyb.zakazlar_soni}</span>
          <span className="kpi-izoh">o'rtacha chek {som(oyb.ortacha_chek)}</span>
        </div>
      </div>
    </div>
  )
}
