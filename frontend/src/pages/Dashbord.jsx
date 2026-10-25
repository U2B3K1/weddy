import { useCallback, useEffect, useState } from 'react'
import Olchagich from '../components/Olchagich'
import OylikGrafik from '../components/OylikGrafik'
import { dashbord, filiallar, oylikQator, som, xatoMatni } from '../api'

// KPI karta belgilari — ixcham stroke SVG (Lucide uslubi), yangi bog'liqlik talab qilmaydi.
const BELGILAR = {
  tushum: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></>),
  daromad: (<><path d="M22 7l-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>),
  soat: (<><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>),
}
const Ikona = ({ nom }) => (
  <svg className="kpi-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {BELGILAR[nom]}
  </svg>
)
const DAVR = { bugun: 'Bugun', hafta: 'Shu hafta', oy: 'Shu oy' }
// Qorong'i yuza uchun dataviz validatordan o'tgan bitta rang (bitta qator — legenda kerak emas, sarlavha nomlaydi)
const GRAFIK_RANG = '#B9833A'

// 6.5: rahbar bosh sahifasining yuqori qismi — Point uslubidagi panel: 3 ta KPI karta (filtr o'z kartasida),
// ostida ikkita grafik karta. Qaror kutayotganlar, qarzdorlar va bugungi ishlar — pastdagi jadval panelida;
// ogohlantirishlar — yuqori paneldagi qo'ng'iroqchada.
export default function Dashbord() {
  const [d, setD] = useState(null)
  const [davr, setDavr] = useState('oy') // FT-19.2: bugun, hafta, oy
  const [fil, setFil] = useState([])
  const [filial, setFilial] = useState('')
  const [oylik, setOylik] = useState(null)
  const [xato, setXato] = useState('')

  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const yukla = useCallback(async () => {
    try { setD(await dashbord(davr, filial)) } catch (e) { setXato(xatoMatni(e)) }
  }, [davr, filial])
  useEffect(() => {
    yukla()
    const t = setInterval(yukla, 60000) // FT-19.1: har 1 daqiqada o'zi yangilanadi
    return () => clearInterval(t)
  }, [yukla])
  useEffect(() => { oylikQator(filial).then(setOylik).catch(() => setOylik([])) }, [filial])

  if (!d) {
    if (xato) return <p className="xato">{xato}</p>
    return (
      <div className="kpi-qator" aria-busy="true">
        {[0, 1, 2].map((i) => <div key={i} className="kpi dashbord-skelet skelet-kpi" />)}
      </div>
    )
  }
  const { bugun, shu_oy: oyb } = d

  return (
    <>
      {fil.length > 0 && (
        <div className="filial-qator">
          <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
            <option value="">Butun salon</option>
            {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
          </select>
        </div>
      )}
      <div className="kpi-qator">
        <div className="kpi">
          <div className="kpi-bosh"><Ikona nom="tushum" /><span className="kpi-nom">Bugun tushum</span></div>
          <span className="kpi-qiymat">{som(bugun.tushum_jami)}</span>
          <span className="kpi-izoh">{bugun.smena_ochiq ? 'Kassa ochiq' : 'Kassa yopiq'}</span>
        </div>
        <div className="kpi">
          <div className="kpi-bosh">
            <Ikona nom="daromad" /><span className="kpi-nom">Daromad</span>
            {/* Filtr o'zi ta'sir qiladigan kartada (Point uslubi) */}
            <select className="kichik-tanlov karta-tanlov" value={davr} aria-label="Daromad davri" onChange={(e) => setDavr(e.target.value)}>
              {Object.entries(DAVR).map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
            </select>
          </div>
          <span className="kpi-qiymat">{som(oyb.hozirgi_daromad)}</span>
          <span className="kpi-izoh">
            {oyb.zakazlar_soni} ta to'langan zakaz
            {oyb.taxminiy_sof_foyda !== null && <> · sof foyda <b className={oyb.taxminiy_sof_foyda < 0 ? 'qizil' : ''}>{som(oyb.taxminiy_sof_foyda)}</b></>}
          </span>
        </div>
        <div className="kpi">
          <div className="kpi-bosh"><Ikona nom="soat" /><span className="kpi-nom">Kutilayotgan daromad</span></div>
          <span className="kpi-qiymat">{som(oyb.kutilayotgan_daromad)}</span>
          <span className="kpi-izoh">Bron qilingan, hali tushmagan</span>
        </div>
      </div>

      <div className="grafik-qator">
        <section className="blok grafik-karta">
          <div className="karta-sarlavha"><h3>Bandlik</h3><span className="malumot">{d.oldinda.kunlar} kun oldinda</span></div>
          <Olchagich foiz={d.oldinda.bandlik_foiz} izoh="libos-kunlar band" rang={GRAFIK_RANG} />
        </section>
        <section className="blok grafik-karta">
          <div className="karta-sarlavha"><h3>Tushum</h3><span className="malumot">oxirgi 12 oy</span></div>
          {oylik === null ? <div className="dashbord-skelet skelet-kpi" /> : (
            <OylikGrafik sarlavha="Tushum" qator={oylik} kalit="tushum" rang={GRAFIK_RANG} yashirinSarlavha />
          )}
        </section>
      </div>
    </>
  )
}
