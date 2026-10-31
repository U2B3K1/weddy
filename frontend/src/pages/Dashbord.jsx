import { useCallback, useEffect, useState } from 'react'
import Olchagich from '../components/Olchagich'
import OylikGrafik from '../components/OylikGrafik'
import { dashbord, filiallar, oylikQator, som, xatoMatni } from '../api'

// KPI karta belgilari — ixcham stroke SVG (Lucide uslubi), yangi bog'liqlik talab qilmaydi.
const BELGILAR = {
  tushum: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></>),
  daromad: (<><path d="M22 7l-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>),
  soat: (<><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>),
  qalqon: (<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /></>),
  diqqat: (<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>),
  yorliq: (<><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8Z" /><path d="M7 7h.01" /></>),
}
const Ikona = ({ nom }) => (
  <svg className="kpi-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {BELGILAR[nom]}
  </svg>
)
const DAVR = { bugun: 'Bugun', hafta: 'Shu hafta', oy: 'Shu oy', yil: 'Shu yil' }
// Qorong'i yuza uchun dataviz validatordan o'tgan bitta rang (bitta qator — legenda kerak emas, sarlavha nomlaydi)
const GRAFIK_RANG = '#B9833A'

// Egasining uch savoli (oxirgi 7 kun): kassada kamomad bormi, nima diqqat talab qiladi, liboslar joyidami.
// Har karta «hammasi joyida» yoki aniq kim/qancha — batafsili Hisobot → «Kunlik kassa» / «Xodimlar nazorati» va Katalog → «Sanoq».
function Nazorat({ n }) {
  const diqqat = [
    n.topshiriqlar > 0 && `${n.topshiriqlar} ta pul topshirig'i tasdiqlanmagan`,
    n.otkazmalar > 0 && `${n.otkazmalar} ta o'tkazma «keldimi?» kutmoqda`,
    n.kelmadi_soni > 0 && `${n.kelmadi_soni} ta o'tkazma kelmadi (${som(n.kelmadi_summa)})`,
    n.terminal_farq !== 0 && `terminal farqi ${som(n.terminal_farq)}`,
  ].filter(Boolean)
  const s = n.sanoq
  const libosMuammo = !!s && (s.yoq > 0 || s.ortiqcha > 0)
  return (
    <div className="kpi-qator" role="region" aria-label={`Nazorat, oxirgi ${n.kun} kun`}>
      <div className="kpi" title={`Oxirgi ${n.kun} kunda xodimlar pulni topshirganda yoki smenani yopganda kam chiqqan naqd. Batafsil: Hisobot → «Kunlik kassa».`}>
        <div className="kpi-bosh"><Ikona nom="qalqon" /><span className="kpi-nom">Kassada kamomad</span></div>
        <span className={`kpi-qiymat${n.kamomad ? ' qizil' : ''}`}>{n.kamomad ? som(n.kamomad) : "Yo'q"}</span>
        <span className="kpi-izoh">
          {n.kamomad_xodimlar.length ? n.kamomad_xodimlar.map((x) => `${x.ism} ${som(x.summa)}`).join(' · ') : `oxirgi ${n.kun} kunda hammasi to'g'ri topshirilgan`}
        </span>
      </div>
      <div className="kpi" title="Rahbar qarori yoki tekshiruvi kerak bo'lgan pul harakatlari. Tasdiqlar — Kassa bo'limida va Telegramda.">
        <div className="kpi-bosh"><Ikona nom="diqqat" /><span className="kpi-nom">Diqqat</span></div>
        <span className={`kpi-qiymat${diqqat.length ? ' qizil' : ''}`}>{diqqat.length ? `${diqqat.length} ta` : 'Hammasi joyida'}</span>
        <span className="kpi-izoh">{diqqat.length ? diqqat.join(' · ') : "tasdiqlanmagan pul va farq yo'q"}</span>
      </div>
      <div className="kpi" title="Oxirgi libos sanog'i natijasi: javonda bo'lishi kerak bo'lgan, lekin topilmagan liboslar — zakazsiz ijara yoki yo'qolgan. Sanoqni istalgan vaqtda o'tkazasiz: Katalog → «Sanoq».">
        <div className="kpi-bosh"><Ikona nom="yorliq" /><span className="kpi-nom">Liboslar joyidami</span></div>
        <span className={`kpi-qiymat${libosMuammo ? ' qizil' : ''}`}>
          {!s ? 'Sanalmagan' : s.yoq > 0 ? `${s.yoq} ta yo'q` : 'Joyida'}
        </span>
        <span className="kpi-izoh">
          {!s ? "Katalog → «Sanoq» — istalgan vaqtda tekshiring" : `oxirgi sanoq ${s.kun_oldin ? `${s.kun_oldin} kun oldin` : 'bugun'}${s.ortiqcha ? ` · ${s.ortiqcha} ta qaytgani kiritilmagan` : ''}`}
        </span>
      </div>
    </div>
  )
}

// 6.5: rahbar bosh sahifasining yuqori qismi — Point uslubidagi panel: 3 ta KPI karta (filtr o'z kartasida),
// ostida ikkita grafik karta. Qaror kutayotganlar, qarzdorlar va bugungi ishlar — pastdagi jadval panelida;
// ogohlantirishlar — yuqori paneldagi qo'ng'iroqchada.
export default function Dashbord() {
  const [d, setD] = useState(null)
  const [davr, setDavr] = useState('oy') // FT-19.2: bugun, hafta, oy, yil
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
        <div className="kpi" title="Bugun qabul qilingan barcha to'lovlar: avans, qoldiq va jarima. Daromaddan farqi — hali to'liq to'lanmagan zakazlarning avanslari ham kiradi.">
          <div className="kpi-bosh"><Ikona nom="tushum" /><span className="kpi-nom">Bugun kassaga kirdi</span></div>
          <span className="kpi-qiymat">{som(bugun.tushum_jami)}</span>
          <span className="kpi-izoh">
            {bugun.smena_ochiq ? 'Kassa ochiq' : 'Kassa yopiq'}
            {bugun.qaytarilgan > 0 && <> · shundan <b className="qizil">{som(bugun.qaytarilgan)}</b> qaytarildi</>}
          </span>
        </div>
        <div className="kpi" title="Davrda kirgan pul (avans va qoldiq), bekor qilingan zakazlarga qaytarilgani ayirilgan. Sof foyda — shundan tasdiqlangan xarajatlar (ijara, oylik va boshqalar) ayirilib, jarimalar qo'shilgan.">
          <div className="kpi-bosh">
            <Ikona nom="daromad" /><span className="kpi-nom">Tushum</span>
            {/* Filtr o'zi ta'sir qiladigan kartada (Point uslubi) */}
            <select className="kichik-tanlov karta-tanlov" value={davr} aria-label="Daromad davri" onChange={(e) => setDavr(e.target.value)}>
              {Object.entries(DAVR).map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
            </select>
          </div>
          <span className="kpi-qiymat">{som(oyb.hozirgi_daromad)}</span>
          <span className="kpi-izoh">
            xarajat {som(oyb.xarajatlar)} · sof foyda <b className={oyb.taxminiy_sof_foyda < 0 ? 'qizil' : ''}>{som(oyb.taxminiy_sof_foyda)}</b>
            {oyb.zakazlar_soni > 0 && <> · {oyb.zakazlar_soni} ta yangi zakaz</>}
            {oyb.tasdiqlanmagan_xarajat > 0 && <> · <span className="qizil">{som(oyb.tasdiqlanmagan_xarajat)} xarajat tasdiq kutmoqda (foydaga kirmagan)</span></>}
          </span>
        </div>
        <div className="kpi" title="Bron qilingan zakazlarning hali to'lanmagan qoldig'i. Pastda — libosi hali berilmagan zakazlardan olingan pul: tushumga kirgan, lekin zakaz bekor bo'lsa qaytarilishi mumkin.">
          <div className="kpi-bosh"><Ikona nom="soat" /><span className="kpi-nom">Hali olinadigan pul</span></div>
          <span className="kpi-qiymat">{som(oyb.qolgan_summa)}</span>
          <span className="kpi-izoh">Bronlar qoldig'i{oyb.kelgusi_avanslar > 0 && <> · olingan avanslar {som(oyb.kelgusi_avanslar)} (to'y hali o'tmagan)</>}</span>
        </div>
      </div>

      {d.nazorat && <Nazorat n={d.nazorat} />}

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
