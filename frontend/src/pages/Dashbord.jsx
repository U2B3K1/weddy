import { useCallback, useEffect, useState } from 'react'
import Halqa from '../components/Halqa'
import LibosSiluet from '../components/LibosSiluet'
import NavIkona from '../components/NavIkona'
import TushumChizigi from '../components/TushumChizigi'
import { dashbord, dashbordPanel, filiallar, som, xatoMatni } from '../api'
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
const GRAFIK_RANG = '#B9833A'
const DAVRLAR = [7, 30, 90]
const qisqaSana = (iso) => { const s = isoOch(iso); return `${s.d} ${OYLAR[s.m].slice(0, 3).toLowerCase()}` }
const mln = (n) => (Math.abs(n) >= 1e6 ? `${(n / 1e6).toLocaleString('uz-UZ', { maximumFractionDigits: 1 })} mln` : som(n))
const bosHarf = (ism) => (ism || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0]).join('').toUpperCase()
const HOLAT = { bron: ['Bron', 'bron'], vaqtinchalik: ['Avanssiz', 'vaqt'], chegirma_kutilmoqda: ['Chegirma kutilmoqda', 'vaqt'] }

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

// Egasining uch savoli (oxirgi 7 kun): kassada kamomad bormi, nima diqqat talab qiladi, liboslar joyidami.
// Har karta «hammasi joyida» yoki aniq kim/qancha — batafsili Hisobot → «Kunlik kassa» / «Xodimlar nazorati» va Liboslar → «Sanoq».
function Nazorat({ n }) {
  const diqqat = [
    n.topshiriqlar > 0 && `${n.topshiriqlar} ta pul topshirig'i tasdiqlanmagan`,
    n.otkazmalar > 0 && `${n.otkazmalar} ta o'tkazma «keldimi?» kutmoqda`,
    n.kelmadi_soni > 0 && `${n.kelmadi_soni} ta o'tkazma kelmadi (${som(n.kelmadi_summa)})`,
    n.terminal_farq !== 0 && `terminal farqi ${som(n.terminal_farq)}`,
  ].filter(Boolean)
  const s = n.sanoq
  const libosMuammo = !!s && (s.yoq > 0 || s.ortiqcha > 0)
  const savollar = [
    { nom: 'Kassada kamomad', ikon: 'qalqon', muammo: !!n.kamomad, javob: n.kamomad ? som(n.kamomad) : "Yo'q",
      izoh: n.kamomad_xodimlar.length ? n.kamomad_xodimlar.map((x) => `${x.ism} ${som(x.summa)}`).join(', ') : `oxirgi ${n.kun} kunda hammasi to'g'ri topshirilgan`,
      title: `Oxirgi ${n.kun} kunda xodimlar pulni topshirganda yoki smenani yopganda kam chiqqan naqd. Batafsil: Hisobotlar → «Kunlik kassa».` },
    { nom: 'Diqqat', ikon: 'diqqat', muammo: diqqat.length > 0, javob: diqqat.length ? `${diqqat.length} ta` : 'Hammasi joyida',
      izoh: diqqat.length ? diqqat.join('; ') : "tasdiqlanmagan pul va farq yo'q",
      title: "Rahbar qarori yoki tekshiruvi kerak bo'lgan pul harakatlari. Tasdiqlar — Kassa bo'limida va Telegramda." },
    { nom: 'Liboslar joyidami', ikon: 'yorliq', muammo: libosMuammo, javob: !s ? 'Sanalmagan' : s.yoq > 0 ? `${s.yoq} ta yo'q` : 'Joyida',
      izoh: !s ? 'Liboslar → «Sanoq»da istalgan vaqtda tekshiring' : `oxirgi sanoq ${s.kun_oldin ? `${s.kun_oldin} kun oldin` : 'bugun'}${s.ortiqcha ? `, ${s.ortiqcha} ta qaytgani kiritilmagan` : ''}`,
      title: "Oxirgi libos sanog'i natijasi: javonda bo'lishi kerak bo'lgan, lekin topilmagan liboslar — zakazsiz ijara yoki yo'qolgan." },
  ]
  return (
    <div className="dash-nazorat" role="region" aria-label={`Nazorat, oxirgi ${n.kun} kun`}>
      {savollar.map((q) => (
        <div key={q.nom} className={`dash-savol${q.muammo ? ' muammo' : ''}`} title={q.title}>
          <span className="dash-savol-nom"><Ikona nom={q.ikon} />{q.nom}</span>
          <b>{q.javob}</b>
          <small>{q.izoh}</small>
        </div>
      ))}
    </div>
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

  return (
    <>
      {!p || !d ? (xato ? <p className="xato">{xato}</p> : <div className="dash-kpi dashbord-skelet skelet-kpi" aria-busy="true" />) : (
        <section className="dash-kpi" aria-label="Bugungi holat">
          <Kpi ikon="tushum" rang="tilla" nom="Tushum" qiymat={mln(p.tushum.jami)}
            trend={<Trend foiz={p.tushum.ozgarish_foiz} oldingi={p.tushum.oldingi_jami} />}
            izoh={<>bugun kassaga {mln(d.bugun.tushum_jami)}{d.bugun.smena_ochiq ? '' : ' · kassa yopiq'}</>}
            title={`Kirgan pul (avans va qoldiq), mijozga qaytarilgani ayirilgan — «Oylik foyda»dagi tushum bilan bir xil ta'rif. Oldingi ${p.kun} kunda: ${som(p.tushum.oldingi_jami)}.`} />
          <Kpi ikon="zakaz" rang="yashil" nom="Yangi zakazlar" qiymat={p.zakazlar.soni}
            trend={<Trend foiz={p.zakazlar.ozgarish_foiz} oldingi={p.zakazlar.oldingi} />}
            izoh={<>olinadigan qoldiq {mln(d.shu_oy.qolgan_summa)}</>}
            title={`Birinchi to'lovi shu davrda olingan zakazlar. Oldingi ${p.kun} kunda: ${p.zakazlar.oldingi}. Pastda — bronlarning hali to'lanmagan qoldig'i.`} />
          <Kpi ikon="libos" rang="kok" nom="Bo'sh liboslar" qiymat={<>{lib.bosh}<span className="kpi-jami"> / {lib.jami}</span></>}
            izoh={<>{lib.mijozda} tasi mijozda · keyingi 30 kun {d.oldinda.bandlik_foiz}% band</>}
            title="Hozir ijaraga berish mumkin bo'lgan liboslar (mijozda, tozalashda va ta'mirdagilar kirmaydi)." />
          <Kpi ikon="mijoz" rang="pushti" nom="Mijozlar" qiymat={p.mijozlar.jami}
            trend={<Trend foiz={p.mijozlar.ozgarish_foiz} oldingi={p.mijozlar.oldingi_yangi} />}
            izoh={<>{p.mijozlar.yangi} ta yangi mijoz</>}
            title={`Birinchi zakazi shu davrda ochilgan mijozlar. Oldingi ${p.kun} kunda: ${p.mijozlar.oldingi_yangi}.`} />
        </section>
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
              <button type="button" className="havola" onClick={() => onBolim?.('hisobotlar')}>Hisobot →</button>
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

          <section className="blok dash-karta dash-bronlar" aria-label="Yaqin bronlar">
            <KartaBosh nom="Yaqin bronlar" ikon="zakaz">
              <button type="button" className="havola" aria-label={`Barcha zakazlar, ${p.yaqin_bronlar.jami} ta yaqin bron`}
                onClick={() => onBolim?.('zakazlar')}>{p.yaqin_bronlar.jami} ta →</button>
            </KartaBosh>
            {p.yaqin_bronlar.royxat.length === 0 ? <p className="malumot">Kelgusi bron yo'q.</p> : (
              <ul className="dash-bron-royxat">
                {p.yaqin_bronlar.royxat.slice(0, 5).map((b) => {
                  const [hnom, hsinf] = HOLAT[b.holat] || [b.holat, '']
                  return (
                    <li key={b.id}>
                      <button type="button" onClick={() => onZakaz?.(b.id)}>
                        <span className="dash-avatar" aria-hidden="true">{bosHarf(b.mijoz)}</span>
                        <span className="dash-bron-matn">
                          <b>{b.mijoz}</b>
                          <small>#{b.raqam} · {b.libos || '—'}{b.qoldiq > 0 ? ` · qoldiq ${mln(b.qoldiq)}` : ''}</small>
                        </span>
                        <span className="dash-bron-ong">
                          <em>{qisqaSana(b.olib_ketish)}</em>
                          <span className={`holat-pill ${hsinf}`}>{hnom}</span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
          </div>

          <div className="dash-qator dash-qator-3">
          {p.filiallar.length > 0 ? (
            <section className="blok dash-karta dash-filiallar" aria-label="Filiallar bo'yicha">
              <KartaBosh nom="Filiallar bo'yicha" ikon="joy" />
              <ul className="dash-filial-royxat">
                {p.filiallar.map((f) => (
                  <li key={f.id}>
                    <Ikona nom="joy" className="dash-filial-ikon" />
                    <span>{f.nomi}</span>
                    <small>{f.zakazlar} zakaz</small>
                    <b>{mln(f.tushum)}</b>
                    <Trend foiz={f.ozgarish_foiz} oldingi={null} />
                  </li>
                ))}
              </ul>
            </section>
          ) : <KassaBugun b={d.bugun} onBolim={onBolim} />}

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
          </section>

          {d.nazorat && (
            <section className="blok dash-karta dash-nazorat-karta" aria-label="Egasining savollari">
              <KartaBosh nom="Nazorat" ikon="qalqon"><span className="malumot">oxirgi {d.nazorat.kun} kun</span></KartaBosh>
              <Nazorat n={d.nazorat} />
            </section>
          )}

          <section className="blok dash-karta dash-tez" aria-label="Tezkor amallar">
            <KartaBosh nom="Tezkor amallar" />
            <div className="dash-tez-tor">
              {[['kassa:yangi', 'yangi', 'Yangi zakaz'], ['kassa:tolov', 'kassa', "To'lov qabul"],
                ['libos:qosh', 'katalog', "Libos qo'shish"], ['hisobotlar', 'hisobotlar', 'Hisobotlar']].map(([b, ikon, nom]) => (
                <button key={b} type="button" className="dash-tez-tugma" onClick={() => onBolim?.(b)}>
                  <NavIkona nom={ikon} /><span>{nom}</span>
                </button>
              ))}
            </div>
          </section>
          </div>
        </div>
      )}
    </>
  )
}
