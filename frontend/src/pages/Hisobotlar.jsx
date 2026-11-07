import { Fragment, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import NavIkona from '../components/NavIkona'
import Xarajatlar from '../components/Xarajatlar'
import OylikGrafik from '../components/OylikGrafik'
import OyTanlash from '../components/OyTanlash'
import Tasdiq from '../components/Tasdiq'
import {
  bankHolati, bankKirit, bonusHisobot, filiallar, hisobot, hisobotTafsilot, hisobotlarRoyxati, kategoriyalar,
  oylikQator, oyniOch, oyniYop, pnl, pnlTafsilot, som, xatoMatni, xodimlarBoshqaruv,
  sanaMatni,
} from '../api'
import SummaInput from '../components/SummaInput'
import KpiFiltr from '../components/KpiFiltr'

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const korsat = (v, tur) => {
  if (v === null || v === undefined || v === '') return '—'
  if (tur === 'pul') return som(v)
  if (tur === 'foiz') return `${v}%`
  if (tur === 'sana') return sanaMatni(v)
  return String(v)
}

// FT-18.1: tayyor davrlar — oy, chorak, yil (ixtiyoriy oraliq pastdagi sana maydonlarida)
const DAVRLAR = [
  ['Shu oy', (d) => [new Date(d.getFullYear(), d.getMonth(), 1), d]],
  ["O'tgan oy", (d) => [new Date(d.getFullYear(), d.getMonth() - 1, 1), new Date(d.getFullYear(), d.getMonth(), 0)]],
  ['Shu chorak', (d) => [new Date(d.getFullYear(), Math.floor(d.getMonth() / 3) * 3, 1), d]],
  ['Shu yil', (d) => [new Date(d.getFullYear(), 0, 1), d]],
]

// Oldingi teng davr bilan taqqoslash belgisi (rangsiz: xarajat o'sishi yaxshi emas, tushum o'sishi — yaxshi; hukm — o'quvchida)
function Taqqos({ hozir, oldin, nomi }) {
  if (typeof hozir !== 'number' || typeof oldin !== 'number') return null
  if (!oldin) return hozir > 0 ? <span className="trend-pill" title={nomi}>yangi</span> : null  // manfiy (farq, zarar) — «yangi» emas
  const f = Math.round(((hozir - oldin) / Math.abs(oldin)) * 100)
  return <span className="trend-pill" title={nomi}>{f > 0 ? '↑' : f < 0 ? '↓' : '='} {Math.abs(f)}%</span>
}
const kunQosh = (s, n) => { const d = new Date(`${s}T00:00:00`); d.setDate(d.getDate() + n); return iso(d) }

// Hisobot tepasida (maket uslubi) — jami qatoridagi pul va son ustunlari, ko'pi bilan 4; oldingi teng davr bilan taqqoslanadi
const KPI_RANG = ['tilla', 'yashil', 'kok', 'pushti']
function HisobotKorsatkichlari({ h, oldingi, kunlar }) {
  const ustunlar = h.ustunlar.map((u, j) => ({ ...u, j }))
    .filter((u) => ['pul', 'son'].includes(u.tur) && typeof h.jami?.[u.j] === 'number').slice(0, 4)
  if (ustunlar.length < 2) return null  // bitta raqam — jadval jami qatorining o'zi yetadi
  return (
    <section className="dash-kpi kpi-filtrlar hisobot-kpi" aria-label="Hisobot ko'rsatkichlari">
      {ustunlar.map((u, i) => {
        const oldin = oldingi?.jami?.[u.j]
        return (
          <KpiFiltr key={u.nom} nom={u.nom} son={korsat(h.jami[u.j], u.tur)} ikon={u.tur === 'pul' ? 'kassa' : 'son'} rang={KPI_RANG[i]}
            izoh={typeof oldin === 'number' ? `oldingi ${kunlar} kunda ${korsat(oldin, u.tur)}` : 'davr bo\'yicha jami'}
            trend={<Taqqos hozir={h.jami[u.j]} oldin={oldin} nomi={`Oldingi ${kunlar} kunga nisbatan`} />} />
        )
      })}
    </section>
  )
}

// Hisobot turlari egasining 3 savoli bo'yicha guruhlanadi («qancha ishladim», «kassada kamomad bormi»,
// «xodim aldamayaptimi») — 16 ta tur bitta tartibsiz ro'yxatda emas. Ro'yxatda yo'q yangi kalit oxirgi guruhga tushadi.
const GURUHLAR = [
  ['Pul va foyda', ['pul-oqimi', 'kelgusi', 'bekor', 'kechikish']],
  ['Kassa va xodimlar', ['kassa', 'nazorat', 'sotuvchi', 'chegirma', 'zalog']],
  ['Liboslar va mijozlar', ['libos', 'kategoriya', 'bandlik', 'bosh-liboslar', 'manba', 'salonchi']],
]
// Keng hisobotlarda standart holatda asosiy ustunlar; qolganlari «Batafsil» bilan (ustun nomi bo'yicha, shu tartibda)
// C-11: seyf farqi ham asosiy — smenalar orasida seyfdan kamaygan pul
const ASOSIY_USTUNLAR = { kassa: ['Sana', 'Xodim', "Kassada bo'lishi kerak", 'Sanaldi', 'Farq', 'Seyf farqi'] }
// Jadvaldagi summa zakaz/ijara narxi bo'yicha — salonning rasmiy tushumi emas (u faqat «Oylik foyda»da)
const TUSHUM_EMAS = new Set(['libos', 'kategoriya', 'sotuvchi', 'salonchi', 'manba', 'bosh-liboslar', 'pul-oqimi', 'nazorat'])

// 6.6: hisobotlar faqat rahbarga va faqat sahifada ko'rsatiladi — fayl sifatida yuklab olinmaydi (FT-18.3, FT-20.2).
// Bo'limlar: umumiy hisobot, oylik foyda (12 oylik grafik bilan), xarajatlar, sotuvchi bonusi, bank solishtirish.
// Bitta bo'lim — bitta nom (QA-07): nav, sahifa sarlavhasi va havolalarda «Oylik foyda».
// Avvalgi «Grafik» bo'limi olib tashlandi (Dashboard grafigini takrorlardi): «grafik» chaqirilsa — Oylik foyda,
// sahifa grafikka suriladi. `onBolim` (ixtiyoriy) — boshqa bo'limga o'tish («Ko'rsatish» havolalari uchun).
export default function Hisobotlar({ bolim, onZakaz, onBolim }) {
  if (bolim === 'pnl' || bolim === 'grafik') return <PnlBolim grafikka={bolim === 'grafik'} onBolim={onBolim} />
  if (bolim === 'xarajat') return <div className="stack hisobot-sahifa"><Xarajatlar /></div>
  if (bolim === 'bonus') return <div className="stack hisobot-sahifa"><Bonus onBolim={onBolim} /></div>
  if (bolim === 'bank') return <div className="stack hisobot-sahifa"><Bank onZakaz={onZakaz} /></div>
  return <HisobotBolim onZakaz={onZakaz} onBolim={onBolim} />
}

// «Oylik foyda» ga o'tish qatori: jadvaldagi summa tushum emasligini eslatadi (B-01)
function TushumEslatma({ onBolim }) {
  return (
    <p className="malumot r2-tushum-eslatma">
      Salonning tushumi (pul kirgan kun bo'yicha) — «Oylik foyda» bo'limida.
      {onBolim && <> <button type="button" className="havola" onClick={() => onBolim('hisobotlar:pnl')}>Ochish</button></>}
    </p>
  )
}

// Asosiy davr bo'yicha hisobot — turli jadvallar va qator tafsiloti.
function HisobotBolim({ onZakaz, onBolim }) {
  const [bugun] = useState(() => new Date())
  const [royxat, setRoyxat] = useState([])
  const [kalit, setKalit] = useState('pul-oqimi')
  const [dan, setDan] = useState(() => { const d = new Date(); d.setDate(1); return iso(d) })
  const [gacha, setGacha] = useState(() => iso(new Date()))
  const [h, setH] = useState(null)
  const [xato, setXato] = useState('')
  const [filtr, setFiltr] = useState({ kategoriya: '', sotuvchi: '', filial: '' })
  const [fil, setFil] = useState([])
  const [kats, setKats] = useState([])
  const [xodimlar, setXodimlar] = useState([])
  const [batafsil, setBatafsil] = useState(false)
  const [oldingi, setOldingi] = useState(null)  // oldingi teng davr (ko'rsatkichlardagi taqqoslash uchun)
  useEffect(() => {
    kategoriyalar().then((k) => setKats(k.filter((x) => x.turi === 'libos'))).catch(() => {})
    xodimlarBoshqaruv().then(setXodimlar).catch(() => {})
    filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {})
  }, [])

  useEffect(() => {
    // «Oylik foyda» o'z bo'limida; bu yerdagi tanlovda faqat jadvalli hisobotlar
    hisobotlarRoyxati().then((r) => setRoyxat(r.filter((x) => x.kalit !== 'pnl'))).catch((e) => setXato(xatoMatni(e)))
  }, [])
  // FT-18.2: qatorni bosganda uni tashkil qilgan zakazlar
  const [taf, setTaf] = useState(null)
  const och = (i) => {
    if (taf?.i === i) return setTaf(null)
    // tafsilot ochilgan qator bilan bir xil filtrda (aks holda jami qatordagidan katta chiqardi)
    hisobotTafsilot(kalit, h.kalitlar[i], dan, gacha, { sotuvchi: filtr.sotuvchi || undefined, filial: filtr.filial || undefined }).then((r) => setTaf({ i, nom: h.qatorlar[i][0], ...r })).catch((e) => setXato(xatoMatni(e)))
  }
  useEffect(() => {
    let bekor = false
    hisobot(kalit, dan, gacha, { kategoriya: filtr.kategoriya || undefined, sotuvchi: filtr.sotuvchi || undefined, filial: filtr.filial || undefined })
      .then((d) => { if (!bekor) { setH(d); setTaf(null); setXato('') } })
      .catch((e) => { if (!bekor) { setH(null); setXato(xatoMatni(e)) } })
    return () => { bekor = true }
  }, [kalit, dan, gacha, filtr])
  // Oldingi teng davr: [dan − N, dan − 1] (N — tanlangan kunlar soni). Davrsiz hisobotda taqqoslash yo'q.
  const kunlar = Math.round((Date.parse(gacha) - Date.parse(dan)) / 864e5) + 1
  const davrsizTur = royxat.find((r) => r.kalit === kalit)?.davrsiz
  // natija qaysi so'rovniki ekani bilan saqlanadi — hisobot turi almashganda eski davr raqamlari boshqa ustunga tushmasin
  const oldingiKalit = `${kalit}|${dan}|${gacha}|${filtr.kategoriya}|${filtr.sotuvchi}|${filtr.filial}`
  useEffect(() => {
    if (davrsizTur) return undefined
    let bekor = false
    hisobot(kalit, kunQosh(dan, -kunlar), kunQosh(dan, -1), { kategoriya: filtr.kategoriya || undefined, sotuvchi: filtr.sotuvchi || undefined, filial: filtr.filial || undefined })
      .then((d) => { if (!bekor) setOldingi({ kalit: oldingiKalit, d }) }).catch(() => {})
    return () => { bekor = true }
  }, [kalit, dan, gacha, filtr, kunlar, davrsizTur, oldingiKalit])
  const oldingiMos = oldingi?.kalit === oldingiKalit ? oldingi.d : null

  const guruhlar = GURUHLAR.map(([nom, kalitlar]) => [nom, kalitlar.map((k) => royxat.find((r) => r.kalit === k)).filter(Boolean)])
  const qolgan = royxat.filter((r) => !GURUHLAR.some(([, k]) => k.includes(r.kalit)))
  if (qolgan.length) guruhlar[guruhlar.length - 1][1].push(...qolgan)
  const davrsiz = h?.davrsiz ?? royxat.find((r) => r.kalit === kalit)?.davrsiz
  // Ko'rsatiladigan ustunlar: asosiylari (Batafsil yopiq bo'lsa) yoki hammasi — asl tartibda indekslar
  const asosiy = ASOSIY_USTUNLAR[kalit]
  const ustunlar = h ? (asosiy && !batafsil
    ? asosiy.map((nom) => h.ustunlar.findIndex((u) => u.nom === nom)).filter((i) => i >= 0)
    : h.ustunlar.map((_, i) => i)) : []
  const zakazUstuni = h?.zakazlar ? h.ustunlar.findIndex((u) => u.nom === 'Zakaz') : -1
  const uzunIzoh = (h?.izoh || '').length > 140

  return (
    <section className="blok jadval-panel hisobot-sahifa">
      {/* Sarlavhaning o'zi — hisobot tanlovi; ostida bitta ixcham filtr qatori: davr, sanalar, kerak bo'lsa kategoriya/sotuvchi/filial */}
      <div className="hisobot-bosh">
        <div className="r2-hisobot-tanlov">
          <label className="hisobot-turi">
            <select value={kalit} aria-label="Hisobot turi" onChange={(e) => { setKalit(e.target.value); setBatafsil(false) }}>
              {guruhlar.filter(([, r]) => r.length).map(([nom, r]) => (
                <optgroup key={nom} label={nom}>
                  {r.map((x) => <option key={x.kalit} value={x.kalit}>{x.sarlavha}</option>)}
                </optgroup>
              ))}
            </select>
            <NavIkona nom="ong" className="tugma-ikon" />
          </label>
          {uzunIzoh && <Info nom={h.sarlavha}>{h.izoh}</Info>}
        </div>
        {h?.izoh && !uzunIzoh && <p className="malumot">{h.izoh}</p>}
      </div>
      <div className="jadval-asboblar hisobot-filtr">
        {davrsiz ? <span className="malumot r2-davrsiz">Hozirgi holat — davrga bog'liq emas</span> : (
          <>
            <div className="tezkor-tablar" role="group" aria-label="Davr">
              {DAVRLAR.map(([nom, fn], i) => {
                const [a, b] = fn(bugun)
                // Faqat birinchi mos davr belgilanadi (chorak boshida «Shu oy» va «Shu chorak» bir xil oraliq);
                // qo'lda kiritilgan oraliqda hech biri tanlanmaydi
                const faol = i === DAVRLAR.findIndex(([, f]) => f(bugun).map(iso).join() === `${dan},${gacha}`)
                return <button key={nom} type="button" className={faol ? 'faol' : ''} aria-pressed={faol}
                  onClick={() => { setDan(iso(a)); setGacha(iso(b)) }}>{nom}</button>
              })}
            </div>
            <div className="davr-sanalar" role="group" aria-label="Sanalar">
              <input type="date" aria-label="Boshlanish sanasi" value={dan} max={gacha} onChange={(e) => e.target.value && setDan(e.target.value)} />
              <span aria-hidden="true">–</span>
              <input type="date" aria-label="Tugash sanasi" value={gacha} min={dan} onChange={(e) => e.target.value && setGacha(e.target.value)} />
            </div>
          </>
        )}
        {h?.filtrlar?.includes('kategoriya') && (
          <select className="kichik-tanlov" value={filtr.kategoriya} aria-label="Kategoriya" onChange={(e) => setFiltr({ ...filtr, kategoriya: e.target.value })}>
            <option value="">Barcha kategoriyalar</option>
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        )}
        {h?.filtrlar?.includes('sotuvchi') && (
          <select className="kichik-tanlov" value={filtr.sotuvchi} aria-label="Sotuvchi" onChange={(e) => setFiltr({ ...filtr, sotuvchi: e.target.value })}>
            <option value="">Barcha sotuvchilar</option>
            {xodimlar.map((x) => <option key={x.id} value={x.id}>{x.ism}</option>)}
          </select>
        )}
        {fil.length > 0 && h?.filtrlar?.includes('filial') && (
          <select className="kichik-tanlov" value={filtr.filial} aria-label="Filial" onChange={(e) => setFiltr({ ...filtr, filial: e.target.value })}>
            <option value="">Barcha filiallar</option>
            {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
          </select>
        )}
        {asosiy && h?.qatorlar.length > 0 && (
          <button type="button" className="ikkinchi kichik" aria-pressed={batafsil} onClick={() => setBatafsil(!batafsil)}>
            {batafsil ? 'Qisqa' : 'Batafsil'}
          </button>
        )}
      </div>
      {xato && <p className="xato jadval-bosh">{xato}</p>}
      {h && (
        <div className="hisobot-ich" role="region" aria-label={h.sarlavha}>
          {h.qatorlar.length > 0 && <HisobotKorsatkichlari h={h} oldingi={davrsiz ? null : oldingiMos} kunlar={kunlar} />}
          {h.qatorlar.length === 0 ? <p className="malumot">{davrsiz ? "Hozircha yozuv yo'q." : "Bu davrda ma'lumot yo'q."}</p> : (
            <div className="hisobot-ora">
              <table className="hisobot">
                <thead>
                  <tr>{ustunlar.map((j) => <th key={h.ustunlar[j].nom} className={h.ustunlar[j].tur === 'matn' ? '' : 'ong'}>{h.ustunlar[j].nom}</th>)}</tr>
                </thead>
                <tbody>
                  {h.qatorlar.map((q, i) => (
                    <tr key={i} className={h.kalitlar ? `bosiladi ${taf?.i === i ? 'ochiq' : ''}` : undefined}
                      onClick={h.kalitlar ? () => och(i) : undefined}>
                      {ustunlar.map((j) => {
                        const v = q[j]
                        const tur = h.ustunlar[j].tur
                        return (
                          <td key={j} className={`${tur === 'matn' ? '' : 'ong'} ${typeof v === 'number' && v < 0 ? 'qizil' : ''}`}>
                            {j === 0 && h.kalitlar
                              ? <button type="button" className="havola" aria-expanded={taf?.i === i}>{korsat(v, tur)}</button>
                              : j === zakazUstuni && h.zakazlar[i] && onZakaz
                                ? <button type="button" className="havola" onClick={(e) => { e.stopPropagation(); onZakaz(h.zakazlar[i]) }}>{korsat(v, tur)}</button>
                                : korsat(v, tur)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
                {h.jami && (
                  <tfoot>
                    <tr>{ustunlar.map((j) => {
                      const v = h.jami[j]
                      return <td key={j} className={h.ustunlar[j].tur === 'matn' ? '' : 'ong'}>{v === null || v === '' ? '' : korsat(v, h.ustunlar[j].tur)}</td>
                    })}</tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
          {h.qoshimcha && <Qoshimcha q={h.qoshimcha} />}
          {h.kalitlar && h.qatorlar.length > 0 && !taf && <p className="malumot">Qatorni bosing — shu davrda to'liq to'langan zakazlari ochiladi.</p>}
          {taf && <Tafsilot taf={taf} kalit={kalit} onZakaz={onZakaz} />}
          {TUSHUM_EMAS.has(kalit) && h.qatorlar.length > 0 && <TushumEslatma onBolim={onBolim} />}
        </div>
      )}
    </section>
  )
}

// Hisobot ostidagi ikkinchi kichik jadval (masalan, Zaloglar — davrda olinganlar turi bo'yicha)
function Qoshimcha({ q }) {
  return (
    <div className="r2h-qoshimcha">
      <h4>{q.sarlavha}</h4>
      <div className="hisobot-ora">
        <table className="hisobot">
          <thead><tr>{q.ustunlar.map((u) => <th key={u.nom} className={u.tur === 'matn' ? '' : 'ong'}>{u.nom}</th>)}</tr></thead>
          <tbody>
            {q.qatorlar.map((r, i) => (
              <tr key={i}>{r.map((v, j) => <td key={j} className={q.ustunlar[j].tur === 'matn' ? '' : 'ong'}>{korsat(v, q.ustunlar[j].tur)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Qator tafsiloti — ustunli kichik jadval; «#44» zakaz kartasini ochadi (B-19)
function Tafsilot({ taf, kalit, onZakaz }) {
  return (
    <div className="tafsilot">
      <b>{taf.nom} — {taf.qatorlar.length} ta zakaz</b>
      {taf.qatorlar.length === 0 ? <p className="malumot">Bu davrda to'liq to'langan zakaz yo'q.</p> : (
        <div className="hisobot-ora">
          <table className="hisobot r2-tafsilot">
            <thead>
              <tr><th>Sana</th><th>Zakaz</th><th>Mijoz</th><th>Libos</th>{kalit !== 'sotuvchi' && <th>Sotuvchi</th>}<th className="ong">Summa</th></tr>
            </thead>
            <tbody>
              {taf.qatorlar.map((q, i) => (
                <tr key={`${q.zakaz_id}-${i}`} className={q.storno ? 'r2-storno' : undefined}>
                  <td>{sanaMatni(q.sana)}{q.storno && <small className="r2-belgi">Bekor qilindi</small>}{q.farq && <small className="r2-belgi">Narx oshdi (yopilgan oy ustidan)</small>}</td>
                  <td>{onZakaz ? <button type="button" className="havola" onClick={() => onZakaz(q.zakaz_id)}>#{q.raqam}</button> : `#${q.raqam}`}</td>
                  <td>{q.mijoz}</td>
                  <td>{q.liboslar.join(', ')}</td>
                  {kalit !== 'sotuvchi' && <td>{q.sotuvchi || '—'}</td>}
                  <td className={`ong ${q.jami < 0 ? 'qizil' : ''}`}>{som(q.jami)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr><td>Zakazlar jami</td><td /><td /><td />{kalit !== 'sotuvchi' && <td />}<td className="ong">{som(taf.jami)}</td></tr>
            </tfoot>
          </table>
        </div>
      )}
      {['libos', 'kategoriya'].includes(kalit) && (
        <p className="malumot">Zakaz summasi chegirma va ustama bilan; jadvaldagi «Ijara narxi bo'yicha» undan farq qilishi mumkin.</p>
      )}
    </div>
  )
}

// Oylik foyda (foyda va zarar) — oy tanlash, filial bo'yicha, oyni yopish/ochish (6.2, FT-18.2) va 12 oylik grafik.
function PnlBolim({ grafikka, onBolim }) {
  const [hisobot, setHisobot] = useState(null)
  const [oy, setOy] = useState(() => OyTanlash.joriy())
  const [fil, setFil] = useState([])
  const [pnlFilial, setPnlFilial] = useState('')
  const [oylik, setOylik] = useState(null)
  const [xato, setXato] = useState('')
  const grafikRef = useRef(null)
  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  useEffect(() => { pnl(oy, pnlFilial).then(setHisobot).catch((e) => setXato(xatoMatni(e))) }, [oy, pnlFilial])
  useEffect(() => { oylikQator(pnlFilial).then(setOylik).catch(() => {}) }, [pnlFilial])
  // Eski «Grafik» bo'limi chaqirilsa — shu sahifa, grafikka surilgan holda
  useEffect(() => { if (grafikka && oylik) grafikRef.current?.scrollIntoView({ block: 'start' }) }, [grafikka, oylik])
  const [oyniYopSurov, setOyniYopSurov] = useState(false)
  const amal = (fn) => async () => {
    setXato('')
    try { await fn(); setHisobot(await pnl(oy, pnlFilial)) } catch (e) { setXato(xatoMatni(e)) }
  }
  const filialNomi = pnlFilial ? fil.find((f) => String(f.id) === String(pnlFilial))?.nomi || 'filial' : ''
  return (
    <div className="stack hisobot-sahifa">
      {xato && <p className="xato">{xato}</p>}
      <section className="blok stack">
        <div className="r2-pnl-bosh">
          <h3>Oylik foyda</h3>
          <OyTanlash value={oy} onChange={setOy} />
          {fil.length > 0 && (
            <select value={pnlFilial} aria-label="Filial" className="kichik-tanlov" onChange={(e) => setPnlFilial(e.target.value)}>
              <option value="">Butun salon</option>
              {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
            </select>
          )}
        </div>
        {pnlFilial && <p className="malumot">Filial natijasi: filialga biriktirilmagan (umumiy) xarajatlar, liboslar va zakazlar bu ko'rinishga kirmaydi.</p>}
        {hisobot && <Pnl r={hisobot} filial={pnlFilial} onBolim={onBolim} />}
        {hisobot && (hisobot.yopilgan ? (
          <div className="stack">
            <p className="malumot">Bu oy yopilgan: ma'lumotlarini faqat rahbar o'zgartira oladi.</p>
            <button className="ikkinchi" onClick={amal(() => oyniOch(oy))}>Oyni qayta ochish</button>
          </div>
        ) : (
          <>
            <button className="ikkinchi" onClick={() => setOyniYopSurov(true)}>Oyni yopish</button>
            {oyniYopSurov && (
              <Tasdiq sarlavha={`${OyTanlash.nomi(oy)} yopilsinmi?`} tugma="Ha, oyni yopish"
                matn="Yopilgan oy ma'lumotlarini faqat rahbar o'zgartira oladi. Keyin «Oyni qayta ochish» orqali ochish mumkin."
                onYop={() => setOyniYopSurov(false)} onTasdiq={() => { setOyniYopSurov(false); amal(() => oyniYop(oy))() }} />
            )}
          </>
        ))}
      </section>
      {oylik && (
        <section className="blok r2-pnl-grafik" ref={grafikRef}>
          <h3>Oxirgi 12 oy{filialNomi ? ` · ${filialNomi}` : ''}</h3>
          <OylikGrafik sarlavha="Foyda" qator={oylik} kalit="sof_foyda" />
          <p className="malumot">Ustun ustiga olib boring yoki bosing — o'sha oy summasi. Aniq raqamlar — yuqorida (oyni tanlang).</p>
        </section>
      )}
    </div>
  )
}

// Tushumning taqqoslanayotgan davrga nisbatan o'zgarishi (FT-18.1); asos 0 bo'lsa foiz hisoblanmaydi
const ozgarish = (hozir, oldin) => {
  if (!oldin) return hozir ? 'yangi' : '—'
  const f = Math.round(((hozir - oldin) / oldin) * 100)
  return `${f > 0 ? '+' : ''}${f}%`
}

function Pnl({ r, filial, onBolim }) {
  // Kassa usuli: pul kirgan kun tushum. FT-18.2: hisoblanmaydigan qatorni bosganda uni tashkil qilgan yozuvlar ochiladi
  const qatorlar = [
    { nom: 'Kirgan pul (avans va qoldiq)', v: r.kirim, kalit: 'kirim' },
    { nom: 'Mijozlarga qaytarilgan', izoh: 'bekor qilingan zakazlar', v: -r.qaytarilgan, kalit: 'qaytarilgan' },
    { nom: "Kelmagan o'tkazmalar", izoh: "rahbar «kelmadi» degan kuni", v: -r.kelmadi, kalit: 'kelmadi', yashir: !r.kelmadi },
    { nom: 'Tushum', v: r.tushum, oralik: true },
    { nom: 'Jarimalar', v: r.jarimalar, kalit: 'jarima' },
    { nom: 'Xarajatlar', v: -r.xarajatlar, kalit: 'xarajat' },
    { nom: 'Sotuvchi bonusi', v: -r.sotuvchi_bonusi, kalit: 'bonus', yashir: !r.sotuvchi_bonusi },
    { nom: r.sof_foyda < 0 ? 'Zarar' : 'Foyda', v: r.sof_foyda, yakuniy: true },
  ].filter((q) => !q.yashir).map((q, i) => ({ ...q, raqam: i + 1 }))
  const [taf, setTaf] = useState(null)
  const [tafOy, setTafOy] = useState(`${r.oy}/${filial}`)
  if (tafOy !== `${r.oy}/${filial}`) { setTafOy(`${r.oy}/${filial}`); setTaf(null) } // oy almashsa tafsilot yopiladi
  const och = (kalit) => {
    if (taf?.qator === kalit) return setTaf(null)
    pnlTafsilot(r.oy, kalit, filial).then(setTaf).catch(() => setTaf(null))
  }
  const t = r.taqqos
  const taqqosNomi = (x) => `${OyTanlash.nomi(x.oy)}${x.gacha_kun ? `, 1–${x.gacha_kun}` : ''}`
  const otgan = t?.otgan_oy
  return (
    <>
      {/* Egasining birinchi savoli bir qarashda (maket uslubi): tushum, xarajat, foyda — o'tgan oyning shu kunigacha bilan */}
      <section className="dash-kpi kpi-filtrlar pnl-kpi" aria-label="Oylik foyda ko'rsatkichlari">
        <KpiFiltr nom="Tushum" son={som(r.tushum)} ikon="tushum" rang="tilla"
          izoh={otgan ? `${taqqosNomi(otgan)}: ${som(otgan.tushum)}` : 'pul kirgan kun bo\'yicha'}
          trend={otgan && <Taqqos hozir={r.tushum} oldin={otgan.tushum} nomi={`${taqqosNomi(otgan)} bilan`} />} />
        <KpiFiltr nom="Xarajatlar" son={som(r.xarajatlar)} ikon="hamyon" rang="pushti"
          izoh={r.sotuvchi_bonusi ? `+ bonus ${som(r.sotuvchi_bonusi)}` : 'tasdiqlanganlari'} />
        <KpiFiltr nom={r.sof_foyda < 0 ? 'Zarar' : 'Foyda'} son={som(r.sof_foyda)} ikon="kassa" rang="yashil" xavf={r.sof_foyda < 0}
          izoh={otgan ? `${taqqosNomi(otgan)}: ${som(otgan.sof_foyda)}` : 'tushum − xarajat'}
          trend={otgan && <Taqqos hozir={r.sof_foyda} oldin={otgan.sof_foyda} nomi={`${taqqosNomi(otgan)} bilan`} />} />
        <KpiFiltr nom="Foyda ulushi" son={r.rentabellik === null ? '—' : `${r.rentabellik}%`} ikon="foiz" rang="kok"
          izoh="har 100 so'm tushumdan" />
      </section>
      {r.tannarxsiz_liboslar > 0 && (
        <p className="ogohlantirish r2-ogoh">
          <span>{r.tannarxsiz_liboslar} ta libosning tannarxi kiritilmagan, foyda haqiqatdagidan yuqori ko'rinishi mumkin.</span>
          {onBolim && <button type="button" className="havola" onClick={() => onBolim('katalog:liboslar')}>Ko'rsatish</button>}
        </p>
      )}
      {r.tasdiqlanmagan_xarajatlar > 0 && (
        <p className="ogohlantirish r2-ogoh">
          <span>{r.tasdiqlanmagan_xarajatlar} ta xarajat hali tasdiqlanmagan va hisobga kirmagan.</span>
          {onBolim && <button type="button" className="havola" onClick={() => onBolim('hisobotlar:xarajat')}>Ko'rsatish</button>}
        </p>
      )}
      <table className="jadval pnl"><tbody>
        {qatorlar.map((q) => (
          <tr key={q.raqam} className={q.yakuniy ? 'pnl-yakuniy' : q.oralik ? 'pnl-oralik' : ''}>
            <td>
              <span className="pnl-raqam">{q.raqam}</span>
              {q.oralik || q.yakuniy ? <b>{q.nom}</b> : q.kalit
                ? <button type="button" className="pnl-havola" aria-expanded={taf?.qator === q.kalit} onClick={() => och(q.kalit)}>{q.nom}</button> : q.nom}
              {q.izoh && <span className="pnl-izoh">{q.izoh}</span>}
            </td>
            <td className={q.yakuniy && q.v < 0 ? 'qizil' : undefined}>{q.oralik || q.yakuniy ? <b>{som(q.v)}</b> : som(q.v)}</td>
          </tr>
        ))}
      </tbody></table>
      {taf && (
        <div className="tafsilot">
          <b>{taf.sarlavha} — {taf.qatorlar.length} ta yozuv</b>
          {taf.qatorlar.length === 0 ? <p className="malumot">Bu oyda yozuv yo'q.</p> : (
            <table className="jadval"><tbody>
              {taf.qatorlar.map((q, i) => (
                <tr key={i} className="kichik-qator"><td>{q.sana ? `${sanaMatni(q.sana)} · ` : ''}{q.matn}</td><td>{som(q.summa)}</td></tr>
              ))}
              <tr><td><b>Jami</b></td><td><b>{som(taf.jami)}</b></td></tr>
            </tbody></table>
          )}
        </div>
      )}
      <p className="malumot">Hisob pul kirgan kun bo'yicha: avans olingan kuni, qoldiq to'langan kuni tushumga kiradi. Zalog kirmaydi.</p>
      {r.kelgusi_avanslar > 0 && (
        <p className="malumot">
          Libosi hali berilmagan zakazlardan olingan pul: <b>{som(r.kelgusi_avanslar)}</b> (bugungi holat) — tushumga kirgan,
          lekin zakaz bekor bo'lsa qoidaga ko'ra qaytarilishi mumkin.
        </p>
      )}
      {r.rentabellik !== null && (
        <p className="malumot">
          Foyda ulushi: tushumning {r.rentabellik}%
          <Info nom="Foyda ulushi">Har 100 so'm tushumdan qancha foyda qolgani. Liboslarga sarflangan pul bu yerda ayirilmaydi —
            u keyingi oylarda o'zini qoplaydi; qanchasi qoplangani «Libos samaradorligi» hisobotida.</Info>
        </p>
      )}
      {r.libos_xaridi > 0 && (
        <p>
          Shu oy libos va aksessuarlar uchun to'landi: {som(r.libos_xaridi)}{r.libos_xaridi_soni > 0 ? ` (${r.libos_xaridi_soni} ta yangi libos)` : ''}. Qo'lingizda qolgan pul:{' '}
          <b className={r.sof_foyda - r.libos_xaridi < 0 ? 'qizil' : ''}>{som(r.sof_foyda - r.libos_xaridi)}</b>
          <span className="malumot"> — foyda minus xarid. Libos va aksessuar foydadan ayirilmaydi: keyingi oylarda o'zini qoplaydi.</span>
        </p>
      )}
      {r.yetkazib_qarz > 0 && (
        <p className="malumot">Yetkazib beruvchilarga qarz (bugungi holat): <b className="qizil">{som(r.yetkazib_qarz)}</b> — Liboslar → «Yetkazib beruvchilar».</p>
      )}
      {r.investitsiya > 0 && (
        <p className="malumot">
          Liboslarga sarflangan pul: {som(r.investitsiya)} · shundan qoplangan {som(r.investitsiya_qoplagan)} (<b>{r.qoplash_foiz}%</b>)
        </p>
      )}
      {t && (
        <div className="stack r2-taqqos">
          <table className="jadval"><tbody>
            {[['otgan_oy', "O'tgan oy"], ['otgan_yil', "O'tgan yil"]].map(([k, nom]) => (
              <tr key={k} className="kichik-qator">
                <td>{nom} ({taqqosNomi(t[k])}): tushum {som(t[k].tushum)}, foyda {som(t[k].sof_foyda)}</td>
                <td>{ozgarish(r.tushum, t[k].tushum)}</td>
              </tr>
            ))}
          </tbody></table>
          {t.qisman && <p className="malumot">Oy hali tugamagan — tushum o'tgan oylarning shu kungacha bo'lgan qismi bilan solishtirildi.</p>}
        </div>
      )}
    </>
  )
}

const USUL = { karta: 'Terminal', otkazma: "O'tkazma", click: 'Click', payme: 'Payme' }

// FT-12.12: rahbar oyiga bir marta bank ko'chirmasidagi summani kiritadi; tizim farqni ko'rsatadi, komissiya xarajatga yoziladi.
function Bank({ onZakaz }) {
  const [oy, setOy] = useState(() => OyTanlash.joriy())
  const [d, setD] = useState(null)
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  useEffect(() => {
    let bekor = false
    bankHolati(oy).then((r) => { if (!bekor) { setD(r); setF({}) } }).catch((e) => { if (!bekor) setXabar({ turi: 'xato', matn: xatoMatni(e) }) })
    return () => { bekor = true }
  }, [oy])

  const saqla = async (usul) => {
    setXabar({ turi: '', matn: '' })
    const u = d.usullar.find((x) => x.usul === usul)
    try {
      setD(await bankKirit({
        oy, usul,
        kochirma_summa: Number(f[`${usul}_k`] ?? u.kochirma ?? 0),
        komissiya: Number(f[`${usul}_m`] ?? u.komissiya ?? 0),
      }))
      setF({})
      setXabar({ turi: 'ok', matn: `${USUL[usul]}: saqlandi.` })
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }

  return (
    <section className="blok stack">
      <div className="r2-pnl-bosh">
        <h3>Bank ko'chirmasi bilan solishtirish</h3>
        <OyTanlash value={oy} onChange={setOy} />
      </div>
      {/* Nima uchun kerak — egasi tushunishi uchun oddiy tilda */}
      <div className="bank-izoh">
        <p><b>Nima uchun:</b> karta, Click va Payme orqali to'langan pul kassaga emas, bank hisobingizga tushadi.
          Sotuvchi «karta bilan to'ladi» deb yozgan pul haqiqatan kelganini faqat bank ko'chirmasi ko'rsatadi.</p>
        <p><b>Qanday:</b> oyni tanlang, bank ilovasidan shu oy uchun har bir usul bo'yicha kelgan summani va bank olgan
          komissiyani yozib, «Saqlash»ni bosing. Tizim sotuvchilar yozgan to'lovlar bilan solishtiradi.</p>
        <p><b>Farq chiqsa:</b> to'lov noto'g'ri usulda yozilgan (masalan, naqd o'rniga karta) yoki pul kelmagan —
          shu oyning to'lovlarini tekshiring. Komissiya avtomatik «Bank komissiyasi» xarajati bo'lib yoziladi.</p>
      </div>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role="status">{xabar.matn}</p>}
      {d && d.usullar.map((u) => (
        <div key={u.usul} className="tasdiq">
          <span>
            <b>{USUL[u.usul]}</b> · tizimda: {som(u.tizimda)}
            {u.farq !== null && (u.farq === 0
              ? <> · <b className="yashil">mos keldi ✓</b></>
              : <> · <b className="qizil">{u.farq < 0 ? `bankka ${som(-u.farq)} kam tushgan` : `bankka ${som(u.farq)} ortiq tushgan`}</b></>)}
          </span>
          <div className="r2-bank-qator">
            <label>Ko'chirmadagi summa
              <SummaInput value={f[`${u.usul}_k`] ?? u.kochirma ?? ''} onChange={(e) => setF({ ...f, [`${u.usul}_k`]: e.target.value })} />
            </label>
            <label>Bank komissiyasi
              <SummaInput value={f[`${u.usul}_m`] ?? u.komissiya ?? ''} onChange={(e) => setF({ ...f, [`${u.usul}_m`]: e.target.value })} />
            </label>
            <button className="ikkinchi kichik" onClick={() => saqla(u.usul)}>Saqlash</button>
          </div>
          <TolovTarixi tolovlar={u.tolovlar || []} onZakaz={onZakaz} />
        </div>
      ))}
      <p className="malumot">Hisob: ko'chirmadagi summa − (tizimda yozilgan to'lovlar − komissiya).</p>
    </section>
  )
}

// Shu usulda yozilgan to'lovlar: kim, qachon, qaysi zakazga — farq chiqsa qaysi to'lov shubhali ekanini topish uchun
const vaqtMatni = (v) => { const t = new Date(v); return `${sanaMatni(iso(t))} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}` }
function TolovTarixi({ tolovlar, onZakaz }) {
  if (tolovlar.length === 0) return <p className="malumot">Bu oyda shu usulda to'lov yozilmagan.</p>
  const xodimlar = {}
  for (const t of tolovlar) if (t.tasdiq !== 'kelmadi') xodimlar[t.xodim] = (xodimlar[t.xodim] || 0) + t.summa
  return (
    <details className="bank-tarix">
      <summary>To'lovlar tarixi ({tolovlar.length}) — kim, qachon, qaysi zakazga</summary>
      <p className="malumot">{Object.entries(xodimlar).map(([ism, s]) => `${ism}: ${som(s)}`).join(' · ')}</p>
      <div className="hisobot-ora">
        <table className="hisobot">
          <thead><tr><th>Vaqt</th><th>Kim yozgan</th><th>Zakaz</th><th>Turi</th><th className="ong">Summa</th></tr></thead>
          <tbody>
            {tolovlar.map((t) => (
              <tr key={t.id} className={t.tasdiq === 'kelmadi' ? 'bank-kelmadi' : ''}>
                <td>{vaqtMatni(t.vaqt)}</td>
                <td>{t.xodim}</td>
                <td>{t.zakaz_id
                  ? <button type="button" className="havola" onClick={() => onZakaz?.(t.zakaz_id)}>#{t.zakaz_raqami} {t.mijoz}</button>
                  : (t.izoh || '—')}</td>
                <td>{t.tur}{t.tasdiq === 'kelmadi' ? ' · rahbar: kelmadi' : t.tasdiq === 'kutilmoqda' ? ' · tasdiq kutilmoqda' : ''}</td>
                <td className="ong">{som(t.summa)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

// FT-15.1: oy oxirida har bir sotuvchi uchun tayyor bonus summasi (funksiya sozlamalarda yoqiladi).
function Bonus({ onBolim }) {
  const [oy, setOy] = useState(() => OyTanlash.joriy())
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  const [ochiq, setOchiq] = useState(null)  // zakazlari ko'rsatilayotgan sotuvchi

  useEffect(() => {
    let bekor = false
    bonusHisobot(oy).then((r) => { if (!bekor) { setD(r); setXato('') } }).catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    return () => { bekor = true }
  }, [oy])

  // O'chiq bo'lsa — bo'sh holat paneli: nima ekani va qayerda yoqiladi (B-22)
  if (d && !d.yoqilgan) {
    return (
      <section className="blok stack r2-bosh-holat">
        <h3>Sotuvchi bonusi o'chirilgan</h3>
        <p className="malumot">Yoqilsa, har oy har bir sotuvchi uchun tayyor bonus summasi shu yerda chiqadi: to'ydan keyin
          libos qaytarib olingan zakazlardan siz belgilagan foiz. Bonus foydadan avtomatik ayiriladi.</p>
        {onBolim
          ? <button type="button" className="ikkinchi" onClick={() => onBolim('sozlamalar:bonus')}>Sozlamada yoqish</button>
          : <p className="malumot">Yoqish: Sozlama → «Sotuvchi bonusi».</p>}
      </section>
    )
  }
  return (
    <section className="blok stack">
      <div className="r2-pnl-bosh">
        <h3>Sotuvchi bonusi</h3>
        <OyTanlash value={oy} onChange={setOy} />
      </div>
      {xato && <p className="xato">{xato}</p>}
      {d && (
        <div className="hisobot-ora">
          <table className="hisobot">
            <thead><tr><th>Sotuvchi</th><th className="ong">Zakazlar</th><th className="ong">Zakazlar summasi</th><th className="ong">Bonus ({Number(d.foiz)}%)</th></tr></thead>
            <tbody>
              {d.sotuvchilar.map((q) => (
                <Fragment key={q.id}>
                  <tr>
                    <td>{q.zakazlar > 0
                      ? <button className="havola-tugma" aria-expanded={ochiq === q.id} onClick={() => setOchiq(ochiq === q.id ? null : q.id)}>{q.ism}</button>
                      : q.ism}</td>
                    <td className="ong">{q.zakazlar}</td><td className="ong">{som(q.tushum)}</td><td className="ong">{som(q.bonus)}</td>
                  </tr>
                  {ochiq === q.id && q.zakaz_royxati.map((z) => (
                    <tr key={z.zakaz_id} className="kichik-qator">
                      <td>#{z.raqam} · {z.mijoz} · qaytarildi {sanaMatni(z.qaytarilgan)}</td><td />
                      <td className="ong">{som(z.summa)}</td><td className="ong">{som(z.bonus)}</td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
            <tfoot><tr><td>Jami</td><td /><td /><td className="ong">{som(d.jami)}</td></tr></tfoot>
          </table>
        </div>
      )}
      <p className="malumot">Bonus xizmat to'liq ko'rsatilgan zakazlardan: to'ydan keyin libos shu oyda qaytarib olingan. Qaytarilgan zakaz bekor qilinmaydi,
        shuning uchun bonus keyin kamaymaydi. Sotuvchi ismini bosing — har bir zakaz va undan chiqqan bonus ko'rinadi.
        Bonus foydadan avtomatik ayiriladi.</p>
    </section>
  )
}
