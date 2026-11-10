import { useCallback, useEffect, useState } from 'react'
import Halqa from '../components/Halqa'
import LibosSiluet from '../components/LibosSiluet'
import NavIkona from '../components/NavIkona'
import TushumChizigi from '../components/TushumChizigi'
import { dashbord, dashbordPanel, filiallar, som, xatoMatni, zakazlarSahifa } from '../api'
import { OYLAR, isoOch } from '../components/kalendar/sana'

// KPI va savol belgilari — ixcham stroke SVG (Lucide uslubi), yangi bog'liqlik talab qilmaydi.
const BELGILAR = {
  tushum: (<><path d="M22 7l-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>),
  zakaz: (<><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18M16 10a4 4 0 0 1-8 0" /></>),
  libos: (<><path d="M9 3c1 1.5 2 2 3 2s2-.5 3-2M9 3 8 6l2 6h4l2-6-1-3" /><path d="M10 12c-1 4-3 7-6 9 3 1 5 1.5 8 1.5s5-.5 8-1.5c-3-2-5-5-6-9" /></>),
  mijoz: (<><circle cx="9" cy="8" r="3.5" /><path d="M2 21a7 7 0 0 1 14 0" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 21a7 7 0 0 0-4-6.3" /></>),
  qalqon: (<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /></>),
  diqqat: (<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>),
  yorliq: (<><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8Z" /><path d="M7 7h.01" /></>),
  joy: (<><path d="M12 21s7-6.2 7-11.5a7 7 0 0 0-14 0C5 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></>),
  kassa: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></>),
}
const Ikona = ({ nom, className = 'kpi-ikon' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {BELGILAR[nom]}
  </svg>
)
// Qorong'i yuza uchun dataviz validatordan o'tgan tilla (bitta qator — legenda kerak emas, sarlavha nomlaydi)
const GRAFIK_RANG = '#F3BF70'  // shisha uslubi: yorqin tilla (to'q shisha ustida kontrast yetarli)
const DAVRLAR = [7, 30, 90]
const qisqaSumma = (n) => (Math.abs(n) >= 1e7 ? `${(n / 1e6).toLocaleString('uz-UZ', { maximumFractionDigits: 1 })} mln so'm` : som(n))
// «1–9 noy» (bir oy ichida) yoki «28 okt – 3 noy»
const davrQisqa = (dan, gacha) => { const a = isoOch(dan), b = isoOch(gacha); return a.m === b.m ? `${a.d}–${b.d} ${OYLAR[b.m].slice(0, 3).toLowerCase()}` : `${qisqaSana(dan)} – ${qisqaSana(gacha)}` }
const qisqaSana = (iso) => { const s = isoOch(iso); return `${s.d} ${OYLAR[s.m].slice(0, 3).toLowerCase()}` }

// Taqqoslash belgisi: oldingi teng davrga nisbatan. Oldingi davr 0 bo'lsa foiz ma'nosiz — «yangi».
function Trend({ foiz, oldingi }) {
  if (foiz == null) return oldingi === 0 ? <span className="trend-pill">yangi</span> : null
  const tur = foiz > 0 ? 'osish' : foiz < 0 ? 'tushish' : ''
  return (
    <span className={`trend-pill ${tur}`} title="Oldingi xuddi shuncha kunga nisbatan">
      {foiz > 0 ? '↑' : foiz < 0 ? '↓' : '='} {Math.abs(foiz)}%
    </span>
  )
}

function Kpi({ ikon, rang, nom, qiymat, trend, izoh, title }) {
  return (
    <div className="dash-kpi-karta" title={title}>
      <span className={`kpi-plitka ${rang}`}><Ikona nom={ikon} /></span>
      <div className="kpi-matn">
        <span className="kpi-nom">{nom}</span>
        <b>{qiymat}</b>
        <small>{izoh}</small>
      </div>
      {trend}
    </div>
  )
}

// Kanvas (MainShisha) 1-qator — egasining savollari: qancha ishladim, kassada kamomad bormi, xodimlar nima kutmoqda, kim qarzdor.
// Batafsili: Oylik foyda, Hisobotlar → «Kunlik kassa», qo'ng'iroqcha menyusidagi qarorlar, Umumiy hisobot → qarzdorlar.
function EgasiSavollari({ d }) {
  const n = d.nazorat
  const foyda = d.shu_oy.taxminiy_sof_foyda
  const oldF = d.oldingi_oy_foyda
  const foyz = oldF ? Math.round(((foyda - oldF) * 100) / Math.abs(oldF)) : null
  const t = d.tasdiq_kutmoqda
  const qarorlar = t.chegirmalar + t.xarajatlar + t.liboslar + t.otkazmalar
  const qarorIzoh = [t.chegirmalar && `${t.chegirmalar} ta chegirma so'rovi`, t.xarajatlar && `${t.xarajatlar} ta xarajat`,
    t.liboslar && `${t.liboslar} ta yangi libos`, t.otkazmalar && `${t.otkazmalar} ta o'tkazma`].filter(Boolean).join(', ')
  return (
    <section className="dash-kpi" aria-label="Egasining savollari">
      <Kpi ikon="tushum" rang="tilla" nom="Bu oy qancha ishladim" qiymat={qisqaSumma(foyda)}
        trend={foyz != null ? <Trend foiz={foyz} oldingi={oldF} /> : null}
        izoh={oldF != null ? `o'tgan oy: ${qisqaSumma(oldF)}` : 'sof foyda, kassa usulida'}
        title={`Shu oydagi sof foyda: ${som(foyda)}${oldF != null ? `; o'tgan oyning shu kunlarigacha: ${som(oldF)}` : ''}. Kassa usuli: kirgan pul minus xarajat va bonus — batafsili Hisobotlar → «Oylik foyda».`} />
      {n && (
        <Kpi ikon="qalqon" rang={n.kamomad ? 'qizil' : 'yashil'} nom="Kassada kamomad" qiymat={n.kamomad ? qisqaSumma(n.kamomad) : "Yo'q"}
          trend={<span className={`trend-pill ${n.kamomad ? 'tushish' : 'osish'}`}>{n.kun} kun</span>}
          izoh={n.kamomad_xodimlar.length ? n.kamomad_xodimlar.map((x) => `${x.ism} ${som(x.summa)}`).join(', ') : `oxirgi ${n.kun} kunda farq yo'q`}
          title={`Oxirgi ${n.kun} kunda xodimlar pulni topshirganda yoki smenani yopganda kam chiqqan naqd. Batafsil: Hisobotlar → «Kunlik kassa».`} />
      )}
      <Kpi ikon="diqqat" rang="sariq" nom="Xodimlar nazorati" qiymat={qarorlar ? `${qarorlar} ta qaror` : "Qaror yo'q"}
        trend={qarorlar ? <span className="trend-pill yangi">yangi</span> : null}
        izoh={qarorIzoh || 'tasdiq kutayotgan narsa yo\'q'}
        title="Rahbar qarori kerak: chegirma so'rovlari, xarajatlar, yangi liboslar, o'tkazmalar — qo'ng'iroqcha menyusida hal qilinadi." />
      <Kpi ikon="mijoz" rang="qizil" nom="Qarzdorlar" qiymat={d.qarz.jami ? qisqaSumma(d.qarz.jami) : "Yo'q"}
        izoh={d.qarz.soni ? `${d.qarz.soni} mijoz · ${d.qarz.eng_eski_kun} kun` : "qarz yo'q"}
        title="Libos qaytarilgandan keyin to'lanmagan jarima va zarar (Umumiy hisobot → qarzdorlar)." />
    </section>
  )
}

const bosHarflar = (ism) => (ism || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0]).join('').toUpperCase()

// Kanvas «Diqqat talab»: kechikkan zakazlar, tez bo'shab qoladigan avanssiz bronlar, «keldimi?» kutayotgan o'tkazmalar
function DiqqatTalab({ n, onZakaz, onBolim }) {
  const [q, setQ] = useState(null)
  const [hozir] = useState(() => Date.now())
  useEffect(() => {
    Promise.all([zakazlarSahifa({ holat: 'kechikkan', limit: 3, offset: 0 }), zakazlarSahifa({ holat: 'vaqtinchalik', limit: 20, offset: 0 })])
      .then(([k, v]) => setQ({ kech: k.natija, vaqt: v.natija.filter((z) => z.bron_muddati)
        .sort((a, b) => String(a.bron_muddati).localeCompare(String(b.bron_muddati))).slice(0, 2) }))
      .catch(() => setQ({ kech: [], vaqt: [] }))
  }, [])
  const bugun = new Date(new Date(hozir).toDateString()).getTime()
  const qatorlar = q ? [
    ...q.kech.map((z) => ({ id: z.id, nom: z.mijoz, izoh: `#${z.raqam} · ${z.liboslar[0] || 'libos'} kechikdi`, tur: 'qarz',
      belgi: `${Math.max(1, Math.round((bugun - new Date(z.qaytarish).getTime()) / 86400000))} kun` })),
    ...q.vaqt.map((z) => {
      const soat = Math.max(1, Math.ceil((new Date(z.bron_muddati).getTime() - hozir) / 3600000))
      return { id: z.id, nom: z.mijoz, izoh: `#${z.raqam} · ${z.liboslar[0] || 'libos'} · avans yo'q`, tur: 'vaqt', belgi: soat < 48 ? `${soat} soat` : `${Math.round(soat / 24)} kun` }
    }),
    ...(n?.otkazmalar ? [{ kalit: 'otkazma', nom: "O'tkazma tasdig'i", izoh: `${n.otkazmalar} ta to'lov «keldimi?» kutmoqda`, tur: 'kok', belgi: 'kassa', bolim: 'kassa' }] : []),
  ].slice(0, 4) : []
  return (
    <section className="blok dash-karta dash-bronlar dash-diqqat" aria-label="Diqqat talab">
      <KartaBosh nom="Diqqat talab" ikon="diqqat">
        <button type="button" className="havola" onClick={() => onBolim?.('zakazlar')}>Barchasi →</button>
      </KartaBosh>
      {q && qatorlar.length === 0 && <p className="malumot">Hammasi joyida: kechikkan zakaz ham, bo'shab qoladigan bron ham yo'q.</p>}
      {qatorlar.length > 0 && (
        <ul className="dash-bron-royxat">
          {qatorlar.map((x) => (
            <li key={x.id || x.kalit}>
              <button type="button" onClick={() => (x.id ? onZakaz?.(x.id) : onBolim?.(x.bolim))}>
                <span className="dash-avatar" aria-hidden="true">{x.id ? bosHarflar(x.nom) : <Ikona nom="kassa" />}</span>
                <span className="dash-bron-matn"><b>{x.nom}</b><small>{x.izoh}</small></span>
                <span className="dash-bron-ong"><span className={`holat-pill ${x.tur}`}>{x.belgi}</span></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

// «Liboslar joyidami?» (egasining savoli) — Liboslar holati kartasi ostida oxirgi sanoq natijasi
function Sanoq({ s }) {
  const muammo = !!s && (s.yoq > 0 || s.ortiqcha > 0)
  return (
    <p className={`dash-sanoq${muammo ? ' muammo' : ''}`} title="Oxirgi libos sanog'i: javonda bo'lishi kerak, lekin topilmagan liboslar. Liboslar → «Sanoq».">
      {!s ? 'Sanoq: hali sanalmagan' : `Oxirgi sanoq ${s.kun_oldin ? `${s.kun_oldin} kun oldin` : 'bugun'}: ${s.yoq ? `${s.yoq} ta yo'q` : 'hammasi joyida'}${s.ortiqcha ? `, ${s.ortiqcha} ta qaytgani kiritilmagan` : ''}`}
    </p>
  )
}

// Kanvas «Zakaz va mijoz»: davrdagi yangi zakazlar va mijozlar (oldingi teng davr bilan), o'rtacha chek
function ZakazVaMijoz({ p, d }) {
  const qatorlar = [
    ['Yangi zakazlar', p.zakazlar.soni, <Trend key="z" foiz={p.zakazlar.ozgarish_foiz} oldingi={p.zakazlar.oldingi} />],
    ['Yangi mijozlar', p.mijozlar.yangi, <Trend key="m" foiz={p.mijozlar.ozgarish_foiz} oldingi={p.mijozlar.oldingi_yangi} />],
    ["O'rtacha chek", som(d.shu_oy.ortacha_chek), null],
  ]
  return (
    <section className="blok dash-karta dash-zm" aria-label="Zakaz va mijoz">
      <KartaBosh nom="Zakaz va mijoz" ikon="zakaz"><span className="malumot">{p.kun} kun</span></KartaBosh>
      <ul className="dash-zm-royxat">
        {qatorlar.map(([nom, qiymat, trend]) => <li key={nom}><span>{nom}</span><b>{qiymat}</b>{trend}</li>)}
      </ul>
    </section>
  )
}

// Kanvas «Xodimlar»: davrda kim kassaga qancha pul qabul qildi (eng ko'pi — to'liq chiziq)
function XodimlarKassasi({ royxat, davr }) {
  const eng = Math.max(1, ...royxat.map((x) => x.summa))
  return (
    <section className="blok dash-karta dash-xodimlar" aria-label="Xodimlar">
      <KartaBosh nom="Xodimlar" ikon="mijoz"><span className="malumot">kassaga · {davr}</span></KartaBosh>
      {royxat.length === 0 ? <p className="malumot">Bu davrda kassaga pul qabul qilinmagan.</p> : (
        <ul className="dash-xodim-royxat">
          {royxat.map((x) => (
            <li key={x.ism}>
              <span>{x.ism}</span><b>{som(x.summa)}</b>
              <span className="dash-xodim-chiziq" aria-hidden="true"><span style={{ width: `${Math.round((x.summa * 100) / eng)}%` }} /></span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function KartaBosh({ nom, ikon, children }) {
  return (
    <div className="dash-karta-bosh">
      <h3>{ikon && <Ikona nom={ikon} className="dash-karta-ikon" />}{nom}</h3>
      {children}
    </div>
  )
}

const USUL = { naqd: 'Naqd', karta: 'Terminal', otkazma: "O'tkazma", click: 'Click', payme: 'Payme' }

// Bugun kassaga kirgan pul usullar bo'yicha va kassadagi naqd (tizim bo'yicha) — filiallar bo'lmagan salonda 3-qatorning birinchi kartasi
function KassaBugun({ b, onBolim }) {
  const usullar = Object.entries(b.tushum || {}).filter(([, s]) => s > 0)
  return (
    <section className="blok dash-karta dash-kassa" aria-label="Bugun kassada">
      <KartaBosh nom="Bugun kassada" ikon="kassa">
        <span className={`holat-pill ${b.smena_ochiq ? 'bron' : 'yopiq'}`}>{b.smena_ochiq ? 'smena ochiq' : 'smena yopiq'}</span>
      </KartaBosh>
      <div className="dash-kassa-jami"><b>{som(b.tushum_jami)}</b><small>kirdi</small></div>
      <ul className="dash-kassa-royxat">
        {usullar.length === 0 && <li><span>Bugun to'lov olinmagan</span></li>}
        {usullar.map(([u, s]) => <li key={u}><span>{USUL[u] || u}</span><b>{som(s)}</b></li>)}
        {b.qaytarilgan > 0 && <li className="qizil"><span>Mijozga qaytarildi</span><b>−{som(b.qaytarilgan)}</b></li>}
        {b.hisobdagi_qoldiq != null && <li><span>Kassadagi naqd</span><b>{som(b.hisobdagi_qoldiq)}</b></li>}
      </ul>
      <button type="button" className="havola dash-karta-oxir" onClick={() => onBolim?.('kassa:hisobot')}>Smena hisoboti →</button>
    </section>
  )
}

// 6.5: rahbar bosh sahifasi — ko'rsatkichlar (davr bilan halol taqqoslash), egasining uch savoli, `orta` (bugungi ishlar:
// qarorlar, bugun olib ketadi, qarzdorlar), keyin kartalar: tushum dinamikasi, eng ko'p ijaraga berilgan liboslar,
// yaqin bronlar, liboslar holati, filiallar va tezkor amallar. Ogohlantirishlar — yuqori paneldagi qo'ng'iroqchada.
export default function Dashbord({ orta = null, onBolim, onZakaz }) {
  const [d, setD] = useState(null)
  const [p, setP] = useState(null)
  const [kun, setKun] = useState(30)
  const [fil, setFil] = useState([])
  const [filial, setFilial] = useState('')
  const [xato, setXato] = useState('')
  const [tab, setTab] = useState('tushum')
  const [telefon, setTelefon] = useState(() => window.matchMedia('(max-width: 767px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(max-width: 767px)'); const h = (e) => setTelefon(e.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])

  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const yukla = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([dashbord('oy', filial), dashbordPanel(kun, filial)])
      setD(a); setP(b); setXato('')
    } catch (e) { setXato(xatoMatni(e)) }
  }, [kun, filial])
  useEffect(() => {
    yukla()
    const t = setInterval(yukla, 60000) // FT-19.1: har 1 daqiqada o'zi yangilanadi
    return () => clearInterval(t)
  }, [yukla])

  const davrNomi = p ? `${qisqaSana(p.dan)} – ${qisqaSana(p.gacha)}` : ''
  const lib = p?.liboslar
  const holatQismlari = lib ? [
    { nom: "Bo'sh", son: lib.bosh, rang: 'var(--h-bron)' },
    { nom: 'Mijozda', son: lib.mijozda, rang: 'var(--h-berildi)' },
    { nom: 'Tozalashda', son: lib.tozalashda, rang: 'var(--h-vaqt)' },
    { nom: "Ta'mirda", son: lib.tamirda, rang: 'var(--h-qarz)' },
  ] : []

  // Telefon (maket 2026-11-10): Tushum / Zakazlar / Liboslar tablari — bir ekranda bitta mavzu
  if (telefon) {
    if (!p || !d) return xato ? <p className="xato">{xato}</p> : <div className="dash-kpi dashbord-skelet skelet-kpi" aria-busy="true" />
    const tablar = [['tushum', 'Tushum', 'hisobotlar'], ['zakazlar', 'Zakazlar', 'kalendar'], ['liboslar', 'Liboslar', 'katalog']]
    return (
      <div className="tb">
        <div className="tb-tablar" role="tablist" aria-label="Rahbar paneli bo'limlari">
          {tablar.map(([id, nom, ikon]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'faol' : undefined} onClick={() => setTab(id)}>
              <NavIkona nom={ikon} />{nom}
            </button>
          ))}
        </div>
        {tab === 'tushum' && (
          <>
            <section className="blok tb-karta tb-tushum" aria-label="Tushum dinamikasi">
              <div className="tb-karta-bosh">
                <h3>Tushum</h3>
                <select className="tb-davr" value={kun} aria-label="Davr" title={davrNomi} onChange={(e) => setKun(Number(e.target.value))}>
                  {DAVRLAR.map((k) => <option key={k} value={k}>{k} kun</option>)}
                </select>
              </div>
              <div className="tb-tushum-jami"><b>{som(p.tushum.jami)}</b><Trend foiz={p.tushum.ozgarish_foiz} oldingi={p.tushum.oldingi_jami} /></div>
              <TushumChizigi kunlar={p.tushum.kunlar} rang={GRAFIK_RANG} past={160} />
              <p className="tb-legenda"><span><i className="joriy" aria-hidden="true" />Joriy davr ({p.kun} kun)</span><span><i className="otgan" aria-hidden="true" />O'tgan davr ({p.kun} kun)</span></p>
            </section>
            <div className="tb-juft">
              <section className="blok tb-karta tb-son" aria-label="Yangi zakazlar">
                <h3><NavIkona nom="kalendar" />Yangi zakazlar</h3>
                <div><b>{p.zakazlar.soni}</b><Trend foiz={p.zakazlar.ozgarish_foiz} oldingi={p.zakazlar.oldingi} /></div>
              </section>
              <section className="blok tb-karta tb-son" aria-label="Yangi mijozlar">
                <h3><NavIkona nom="mijozlar" />Yangi mijozlar</h3>
                <div><b>{p.mijozlar.yangi}</b><Trend foiz={p.mijozlar.ozgarish_foiz} oldingi={p.mijozlar.oldingi_yangi} /></div>
              </section>
            </div>
            <button type="button" className="blok tb-karta tb-qator" onClick={() => onBolim?.('zakazlar:kechikkan')}>
              <NavIkona nom="soat" /><span>Kechikkan qaytarishlar</span>
              <b className={d.bugun.kechikkan > 0 ? 'qizil' : undefined}>{d.bugun.kechikkan}</b><NavIkona nom="ong" className="nav-ikon tb-ong" />
            </button>
            <section className="blok tb-karta tb-holat" aria-label="Liboslar holati">
              <h3><NavIkona nom="katalog" />Liboslar holati</h3>
              <div className="tb-holat-chiziq" role="img" aria-label={holatQismlari.map((q) => `${q.nom}: ${q.son}`).join(', ')}>
                {holatQismlari.filter((q) => q.son > 0).map((q) => <i key={q.nom} style={{ flexGrow: q.son, background: q.rang }} />)}
              </div>
              <ul className="tb-holat-legenda">
                {holatQismlari.filter((q) => q.son > 0).map((q) => <li key={q.nom}><i style={{ background: q.rang }} aria-hidden="true" />{q.son} {q.nom.toLowerCase()}</li>)}
              </ul>
            </section>
            {/* egasining savollari — maketdagi birinchi ekrandan pastda (aylantirganda) */}
            <EgasiSavollari d={d} />
          </>
        )}
        {tab === 'zakazlar' && (
          <>
            <DiqqatTalab n={d.nazorat} onZakaz={onZakaz} onBolim={onBolim} />
            <ZakazVaMijoz p={p} d={d} />
            <KassaBugun b={d.bugun} onBolim={onBolim} />
            <XodimlarKassasi royxat={d.xodimlar_kassasi || []} davr={davrQisqa(d.davr.dan, d.davr.gacha)} />
            {orta}
          </>
        )}
        {tab === 'liboslar' && (
          <>
            <section className="blok dash-karta dash-holat" aria-label="Liboslar holati">
              <KartaBosh nom="Liboslar holati" ikon="yorliq" />
              <div className="dash-holat-ichi">
                <Halqa qismlar={holatQismlari} jami={lib.jami} izoh="faol libos" olcham={124} qalinlik={15} />
                <ul className="dash-legenda">
                  {holatQismlari.map((q) => (
                    <li key={q.nom}><i style={{ background: q.rang }} aria-hidden="true" /><span>{q.nom}</span><b>{q.son}</b>
                      <small>{lib.jami ? Math.round((q.son * 100) / lib.jami) : 0}%</small></li>
                  ))}
                </ul>
              </div>
              <Sanoq s={d.nazorat?.sanoq} />
            </section>
            <section className="blok dash-karta dash-mashhur" aria-label="Eng ko'p ijaraga berilgan liboslar">
              <KartaBosh nom="Eng ko'p ijaraga berilgan" ikon="libos">
                <button type="button" className="havola" onClick={() => onBolim?.('katalog')}>Barchasi →</button>
              </KartaBosh>
              {p.top_liboslar.length === 0 ? <p className="malumot">Hali ijaraga berilgan libos yo'q.</p> : (
                <ol className="dash-mashhur-tor">
                  {p.top_liboslar.slice(0, 3).map((l, i) => (
                    <li key={l.id}>
                      <div className="dash-mashhur-rasm">{l.rasm ? <img src={l.rasm} alt="" loading="lazy" /> : <LibosSiluet />}<span className="dash-orin">№{i + 1}</span></div>
                      <b>{l.nomi}</b><small>{l.ijara_soni} marta ijarada</small><span className="dash-mashhur-narx">{som(l.ijara_narxi)}</span>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </>
        )}
      </div>
    )
  }

  return (
    <>
      {!p || !d ? (xato ? <p className="xato">{xato}</p> : <div className="dash-kpi dashbord-skelet skelet-kpi" aria-busy="true" />) : (
        <EgasiSavollari d={d} />
      )}

      {orta}

      {p && (
        <div className="dash-tor">
          {/* Bloklar maketdagi proporsiyada: 2-qator 512 : 479 : 277, 3-qator 345 : 302 : 351 : 263 */}
          <div className="dash-qator dash-qator-2">
          <section className="blok dash-karta dash-tushum" aria-label="Tushum dinamikasi">
            {/* Davr (va filial) — maketdagidek kartaning o'zida ixcham tanlov; ko'rsatkichlar ham shu davr bo'yicha */}
            <KartaBosh nom="Tushum dinamikasi" ikon="tushum">
              <span className="dash-tanlovlar">
                {fil.length > 0 && (
                  <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
                    <option value="">Butun salon</option>
                    {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
                  </select>
                )}
                <select className="kichik-tanlov" value={kun} aria-label="Davr" title={davrNomi} onChange={(e) => setKun(Number(e.target.value))}>
                  {DAVRLAR.map((k) => <option key={k} value={k}>{k} kun</option>)}
                </select>
              </span>
            </KartaBosh>
            <div className="dash-tushum-jami">
              <b>{som(p.tushum.jami)}</b>
              <Trend foiz={p.tushum.ozgarish_foiz} oldingi={p.tushum.oldingi_jami} />
              <small className="malumot">{davrNomi} · uzuq chiziq — oldingi {p.kun} kun</small>
            </div>
            <TushumChizigi kunlar={p.tushum.kunlar} rang={GRAFIK_RANG} />
          </section>

          <section className="blok dash-karta dash-mashhur" aria-label="Eng ko'p ijaraga berilgan liboslar">
            <KartaBosh nom="Eng ko'p ijaraga berilgan" ikon="libos">
              <button type="button" className="havola" onClick={() => onBolim?.('katalog')}>Barchasi →</button>
            </KartaBosh>
            {p.top_liboslar.length === 0 ? <p className="malumot">Hali ijaraga berilgan libos yo'q.</p> : (
              <ol className="dash-mashhur-tor">
                {p.top_liboslar.slice(0, 3).map((l, i) => (
                  <li key={l.id}>
                    <div className="dash-mashhur-rasm">
                      {l.rasm ? <img src={l.rasm} alt="" loading="lazy" /> : <LibosSiluet />}
                      <span className="dash-orin">№{i + 1}</span>
                    </div>
                    <b>{l.nomi}</b>
                    <small>{l.ijara_soni} marta ijarada</small>
                    <span className="dash-mashhur-narx">{som(l.ijara_narxi)}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <DiqqatTalab n={d.nazorat} onZakaz={onZakaz} onBolim={onBolim} />
          </div>

          <div className="dash-qator dash-qator-3">
          <KassaBugun b={d.bugun} onBolim={onBolim} />

          <section className="blok dash-karta dash-holat" aria-label="Liboslar holati">
            <KartaBosh nom="Liboslar holati" ikon="yorliq" />
            <div className="dash-holat-ichi">
              <Halqa qismlar={holatQismlari} jami={lib.jami} izoh="faol libos" olcham={124} qalinlik={15} />
              <ul className="dash-legenda">
                {holatQismlari.map((q) => (
                  <li key={q.nom}>
                    <i style={{ background: q.rang }} aria-hidden="true" />
                    <span>{q.nom}</span>
                    <b>{q.son}</b>
                    <small>{lib.jami ? Math.round((q.son * 100) / lib.jami) : 0}%</small>
                  </li>
                ))}
              </ul>
            </div>
            <Sanoq s={d.nazorat?.sanoq} />
          </section>

          <ZakazVaMijoz p={p} d={d} />
          <XodimlarKassasi royxat={d.xodimlar_kassasi || []} davr={davrQisqa(d.davr.dan, d.davr.gacha)} />
          </div>
        </div>
      )}
    </>
  )
}
