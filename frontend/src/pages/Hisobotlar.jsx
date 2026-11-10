import { Fragment, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
import Xarajatlar from '../components/Xarajatlar'
import { BoshAmal } from '../components/BoshJoy'
import { OYLAR } from '../components/kalendar/sana'
import OyTanlash from '../components/OyTanlash'
import Tasdiq from '../components/Tasdiq'
import {
  bankHolati, bankKirit, bonusHisobot, filiallar, hisobot, hisobotTafsilot, hisobotlarRoyxati, kategoriyalar,
  oylikQator, oyniOch, oyniYop, pnl, pnlTafsilot, som, xatoMatni, xodimlarBoshqaruv,
  sanaMatni, guruhla,
} from '../api'
import SummaInput from '../components/SummaInput'
import KpiFiltr from '../components/KpiFiltr'
import { Belgi } from '../components/ZakazQatorlari'

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

// Ko'rsatkich kartasida katta summa qisqa: «62,3 mln» (to'liq summa — jadval jami qatorida)
const kpiQiymat = (v, tur) => (tur === 'pul' && typeof v === 'number' && Math.abs(v) >= 1e7
  ? `${(v / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} mln` : korsat(v, tur))
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
          <KpiFiltr key={u.nom} nom={u.nom} son={kpiQiymat(h.jami[u.j], u.tur)} ikon={u.tur === 'pul' ? 'kassa' : 'son'} rang={KPI_RANG[i]}
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
// Kanvas «Nima bo'yicha»: eng ko'p ochiladigan uch hisobot tugmada (qolganlari — yonidagi ro'yxatda)
const TEZKOR = [['libos', 'Liboslar'], ['nazorat', 'Xodimlar'], ['pul-oqimi', 'Pul oqimi']]
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
  if (bolim === 'pnl' || bolim === 'grafik') return <PnlBolim grafikka={bolim === 'grafik'} />
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
  const [kalit, setKalit] = useState('libos')  // kanvas: standart — «Qaysi libos o'zini oqladi»
  const [dan, setDan] = useState(() => { const d = new Date(); d.setDate(1); return iso(d) })
  const [gacha, setGacha] = useState(() => iso(new Date()))
  const [h, setH] = useState(null)
  const [xato, setXato] = useState('')
  const [filtr, setFiltr] = useState({ kategoriya: '', sotuvchi: '', filial: '' })
  const [fil, setFil] = useState([])
  const [kats, setKats] = useState([])
  const [xodimlar, setXodimlar] = useState([])
  const [batafsil, setBatafsil] = useState(false)
  const [oraliq, setOraliq] = useState(false)  // davr tanlovida «Boshqa oraliq» — sana maydonlari ko'rinadi
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
      .then((d) => { if (!bekor) { setH({ ...d, kalit }); setTaf(null); setXato('') } })
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

  const tanla = (k) => { setKalit(k); setBatafsil(false) }
  const davrIndeks = DAVRLAR.findIndex(([, f]) => f(bugun).map(iso).join() === `${dan},${gacha}`)
  const qolda = oraliq || davrIndeks < 0
  const libosKorinish = h?.kalit === 'libos' && h.kalitlar && h.qatorlar.length > 0

  // Jadval ostidagi umumiy qism: qatorni bosish izohi, tafsilot, tushum eslatmasi
  const pastki = h && (
    <>
      {h.qoshimcha && <Qoshimcha q={h.qoshimcha} />}
      {h.kalitlar && h.qatorlar.length > 0 && !taf && <p className="malumot">Qatorni bosing — shu davrda to'liq to'langan zakazlari ochiladi.</p>}
      {taf && <Tafsilot taf={taf} kalit={kalit} onZakaz={onZakaz} />}
      {TUSHUM_EMAS.has(kalit) && h.qatorlar.length > 0 && <TushumEslatma onBolim={onBolim} />}
    </>
  )

  return (
    <div className="stack hisobot-sahifa hisobot-umumiy">
      {/* kanvas (HisobotBolimShisha): «Nima bo'yicha» — asosiy hisobotlar tugmada, qolganlari ro'yxatda; o'ngda davr */}
      <div className="hisobot-asbob">
        <span className="malumot">Nima bo'yicha:</span>
        <div className="hisobot-chiplar" role="group" aria-label="Asosiy hisobotlar">
          {TEZKOR.filter(([k]) => royxat.some((x) => x.kalit === k)).map(([k, nom]) => (
            <button key={k} type="button" className={kalit === k ? 'faol' : ''} aria-pressed={kalit === k} onClick={() => tanla(k)}>{nom}</button>
          ))}
        </div>
        <label className="hisobot-boshqa">
          <select value={kalit} aria-label="Hisobot turi" onChange={(e) => tanla(e.target.value)}>
            {guruhlar.filter(([, r]) => r.length).map(([nom, r]) => (
              <optgroup key={nom} label={nom}>
                {r.map((x) => <option key={x.kalit} value={x.kalit}>{x.sarlavha}</option>)}
              </optgroup>
            ))}
          </select>
        </label>
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
        <div className="hisobot-davr">
          {davrsiz ? <span className="malumot r2-davrsiz">Hozirgi holat — davrga bog'liq emas</span> : (
            <>
              <select className="kichik-tanlov" aria-label="Davr" value={qolda ? 'oraliq' : String(davrIndeks)}
                onChange={(e) => {
                  if (e.target.value === 'oraliq') return setOraliq(true)
                  const [a, b] = DAVRLAR[Number(e.target.value)][1](bugun)
                  setOraliq(false); setDan(iso(a)); setGacha(iso(b))
                }}>
                {DAVRLAR.map(([nom], i) => <option key={nom} value={i}>{nom}</option>)}
                <option value="oraliq">Boshqa oraliq…</option>
              </select>
              {qolda && (
                <div className="davr-sanalar" role="group" aria-label="Sanalar">
                  <input type="date" aria-label="Boshlanish sanasi" value={dan} max={gacha} onChange={(e) => e.target.value && setDan(e.target.value)} />
                  <span aria-hidden="true">–</span>
                  <input type="date" aria-label="Tugash sanasi" value={gacha} min={dan} onChange={(e) => e.target.value && setGacha(e.target.value)} />
                </div>
              )}
            </>
          )}
        </div>
      </div>
      {xato && <p className="xato">{xato}</p>}
      {h && (
        <div className="hisobot-ich" role="region" aria-label={h.sarlavha}>
          {libosKorinish ? (
            <LibosQoplash h={h} oldingi={davrsiz ? null : oldingiMos} kunlar={kunlar} taf={taf} och={och}>{pastki}</LibosQoplash>
          ) : (
            <>
              {h.qatorlar.length > 0 && <HisobotKorsatkichlari h={h} oldingi={davrsiz ? null : oldingiMos} kunlar={kunlar} />}
              <section className="blok jadval-panel hisobot-panel">
                <div className="hisobot-panel-bosh">
                  <h3>{h.sarlavha}</h3>
                  {uzunIzoh && <Info nom={h.sarlavha}>{h.izoh}</Info>}
                  {asosiy && h.qatorlar.length > 0 && (
                    <button type="button" className="ikkinchi kichik" aria-pressed={batafsil} onClick={() => setBatafsil(!batafsil)}>
                      {batafsil ? 'Qisqa' : 'Batafsil'}
                    </button>
                  )}
                </div>
                {h.izoh && !uzunIzoh && <p className="malumot hisobot-izoh">{h.izoh}</p>}
                {h.qatorlar.length === 0 ? <p className="malumot">{davrsiz ? "Hozircha yozuv yo'q." : "Bu davrda ma'lumot yo'q."}</p> : (
                  <Tasma className="hisobot-ora" pastki={110}>
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
                  </Tasma>
                )}
                {pastki}
              </section>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// Kanvas «Qaysi libos o'zini oqladi»: qoplash bo'yicha saralangan, qatorda rasm, nom, artikul · kategoriya.
// Backend ustunlari: 0 Libos, 1 Kategoriya, 2 Berilgan, 3 Ijara narxi, 4 Tannarx, 5 Qoplash, 6 Oxirgi, 7 Bo'sh kun.
const raqam = (n) => (n || 0).toLocaleString('ru-RU')
const qisqaPul = (n) => (Math.abs(n) >= 1e7 ? `${(n / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} mln` : raqam(n))
function LibosQoplash({ h, oldingi, kunlar, taf, och, children }) {
  const j = h.jami || []
  const old = oldingi?.jami
  const tartib = h.qatorlar.map((_, i) => i).sort((a, b) => (h.qatorlar[b][5] ?? -1) - (h.qatorlar[a][5] ?? -1))
  const oqlagan = h.qatorlar.filter((q) => q[5] >= 100).length
  const tannarxli = h.qatorlar.filter((q) => q[4]).length
  const nomi = `Oldingi ${kunlar} kunga nisbatan`
  return (
    <>
      <section className="dash-kpi kpi-filtrlar hisobot-kpi" aria-label="Hisobot ko'rsatkichlari">
        <KpiFiltr nom="Ijaralar" son={raqam(j[2])} ikon="libos" rang="tilla" izoh={`${h.qatorlar.length} ta libos`}
          trend={<Taqqos hozir={j[2]} oldin={old?.[2]} nomi={nomi} />} />
        <KpiFiltr nom="Ijara tushumi" son={qisqaPul(j[3] || 0)} ikon="tushum" rang="yashil" izoh="shu liboslardan"
          trend={<Taqqos hozir={j[3]} oldin={old?.[3]} nomi={nomi} />} />
        <KpiFiltr nom="Tannarx" son={j[4] ? qisqaPul(j[4]) : '—'} ikon="hamyon" rang="kok"
          izoh={tannarxli < h.qatorlar.length ? `${tannarxli} ta libosda kiritilgan` : 'sotib olingan narx'} />
        <KpiFiltr nom="O'rtacha qoplash" son={j[5] == null ? '—' : `${Math.round(j[5])}%`} ikon="foiz" rang="pushti"
          izoh={`${oqlagan} tasi o'zini oqladi`} />
      </section>
      <section className="blok jadval-panel hisobot-panel">
        <div className="hisobot-panel-bosh"><h3>{h.sarlavha}</h3><span className="malumot">qoplash bo'yicha saralangan</span></div>
        <Tasma className="hisobot-ora" pastki={110}>
          <table className="hisobot libos-qoplash">
            <thead>
              <tr><th>Libos</th><th className="ong">Ijaralar</th><th className="ong">Tushum</th><th className="ong">Tannarx</th><th>Qoplash</th></tr>
            </thead>
            <tbody>
              {tartib.map((i) => {
                const q = h.qatorlar[i]
                const [sku, ...nom] = String(q[0]).split(' ')
                return (
                  <tr key={h.kalitlar[i]} className={`bosiladi ${taf?.i === i ? 'ochiq' : ''}`} onClick={() => och(i)}>
                    <td>
                      <span className="mk-libos">
                        <span className="mk-rasm" aria-hidden="true">{h.rasmlar?.[i] ? <img src={h.rasmlar[i]} alt="" loading="lazy" /> : <NavIkona nom="katalog" />}</span>
                        <span className="zakaz-nom">
                          <button type="button" className="havola" aria-expanded={taf?.i === i}>{nom.join(' ') || sku}</button>
                          <small>{sku} · {q[1]}</small>
                        </span>
                      </span>
                    </td>
                    <td className="ong">{q[2]}</td>
                    <td className="ong">{raqam(q[3])}</td>
                    <td className="ong lq-tannarx">{q[4] ? raqam(q[4]) : '—'}</td>
                    <td><Qoplash f={q[5]} /></td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr><td>Jami</td><td className="ong">{raqam(j[2])}</td><td className="ong">{raqam(j[3])}</td>
                <td className="ong">{j[4] ? raqam(j[4]) : '—'}</td>
                <td><span className="qoplash"><span aria-hidden="true" /><b>{j[5] == null ? '—' : `${Math.round(j[5])}%`}</b></span></td></tr>
            </tfoot>
          </table>
        </Tasma>
        <p className="izoh-q">
          <NavIkona nom="yordam" className="tugma-ikon" />
          <span>Qoplash = libosdan butun vaqtda tushgan ijara ÷ uning sotib olingan narxi. Chiziqdagi oq belgi — 100%: undan o'tsa,
            libos o'z narxini qaytargan, qolgani foyda. Ijaralar va tushum — tanlangan davr, to'liq to'langan zakazlar bo'yicha.</span>
        </p>
        {children}
      </section>
    </>
  )
}

// Qoplash chizig'i: shkala 300% gacha, oq belgi — 100% (kanvasdagidek); 100% dan yuqori — yashil, past — qizil
function Qoplash({ f }) {
  if (f == null) return <span className="malumot">tannarx yo'q</span>
  const yaxshi = f >= 100
  return (
    <span className="qoplash">
      <span className={`qoplash-chiziq ${yaxshi ? 'yashil' : 'qizil'}`} aria-hidden="true"><i style={{ width: `${Math.min(100, f / 3)}%` }} /></span>
      <b className={yaxshi ? 'qoplash-yashil' : 'qoplash-qizil'}>{Math.round(f)}%</b>
    </span>
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

// Oylik foyda (kanvas FoydaShisha) — oy tugmalari, 3 ko'rsatkich, «Qayerdan keldi, qayerga ketdi», foyda sharsharasi,
// oxirgi 6 oy grafigi va oylar jadvali. Filial bo'yicha, oyni yopish/ochish (6.2), qator tafsiloti (FT-18.2) saqlanadi.
const oySiljit = (oy, n) => { const [y, m] = oy.split('-').map(Number); const d = new Date(y, m - 1 + n, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }
// «Noyabr, 1–9» (joriy oy), «Oktabr» (shu yil), «Dekabr 2025» (boshqa yil)
const oyYorliq = (oy, joriy) => {
  const [y, m] = oy.split('-').map(Number)
  if (oy === joriy) return `${OYLAR[m - 1]}, 1–${new Date().getDate()}`
  return y === Number(joriy.slice(0, 4)) ? OYLAR[m - 1] : `${OYLAR[m - 1]} ${y}`
}
const mlnQ = (n) => (n === 0 ? '0' : `${(Math.round((n / 1e6) * 10) / 10).toLocaleString('ru-RU')} mln`)
// Ulushlar «eng katta qoldiq» usulida — guruh ichida jami doim 100%
function ulushlar(qiymatlar, jami) {
  if (!jami) return qiymatlar.map(() => 0)
  const x = qiymatlar.map((v) => (v / jami) * 100)
  const b = x.map((v) => Math.floor(v))
  let qol = 100 - b.reduce((a, v) => a + v, 0)
  x.map((v, i) => [v - Math.floor(v), i]).sort((a, c) => c[0] - a[0]).forEach(([, i]) => { if (qol > 0) { b[i] += 1; qol -= 1 } })
  return b
}
// Yaxlit shkala qadami: 1, 2, 2.5, 5 × 10ⁿ (taxminan 4 bo'lak)
const yaxlitQadam = (oraliq) => {
  const xom = oraliq / 4 || 1
  const d = 10 ** Math.floor(Math.log10(xom))
  const n = xom / d
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * d
}

function PnlBolim({ grafikka }) {
  const [joriy] = useState(() => OyTanlash.joriy())
  const [hisobot, setHisobot] = useState(null)
  const [oy, setOy] = useState(joriy)
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
  const tezkor = [0, -1, -2, -3].map((n) => oySiljit(joriy, n))
  return (
    <div className="stack hisobot-sahifa foyda-sahifa">
      {/* kanvas: o'ng tepada — oy holati (yopish / qayta ochish) */}
      {hisobot && (
        <BoshAmal>
          {hisobot.yopilgan
            ? <button type="button" className="bosh-tugma ikkinchi-bosh" onClick={amal(() => oyniOch(oy))}><NavIkona nom="qaytar" className="tugma-ikon" />Oyni qayta ochish</button>
            : <button type="button" className="bosh-tugma ikkinchi-bosh" onClick={() => setOyniYopSurov(true)}><NavIkona nom="qalqon" className="tugma-ikon" />Oyni yopish</button>}
        </BoshAmal>
      )}
      {oyniYopSurov && (
        <Tasdiq sarlavha={`${OyTanlash.nomi(oy)} yopilsinmi?`} tugma="Ha, oyni yopish"
          matn="Yopilgan oy ma'lumotlarini faqat rahbar o'zgartira oladi. Keyin «Oyni qayta ochish» orqali ochish mumkin."
          onYop={() => setOyniYopSurov(false)} onTasdiq={() => { setOyniYopSurov(false); amal(() => oyniYop(oy))() }} />
      )}
      <div className="hisobot-asbob">
        <div className="hisobot-chiplar" role="group" aria-label="Oy">
          {tezkor.map((o) => (
            <button key={o} type="button" className={oy === o ? 'faol' : ''} aria-pressed={oy === o} onClick={() => setOy(o)}>{oyYorliq(o, joriy)}</button>
          ))}
        </div>
        <div className="hisobot-davr">
          <OyTanlash value={oy} onChange={setOy} yorliq="Boshqa oy" />
          {fil.length > 0 && (
            <select value={pnlFilial} aria-label="Filial" className="kichik-tanlov" onChange={(e) => setPnlFilial(e.target.value)}>
              <option value="">Butun salon</option>
              {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
            </select>
          )}
        </div>
      </div>
      {xato && <p className="xato">{xato}</p>}
      {pnlFilial && <p className="malumot">Filial natijasi: filialga biriktirilmagan (umumiy) xarajatlar, liboslar va zakazlar bu ko'rinishga kirmaydi.</p>}
      {hisobot?.yopilgan && <p className="malumot">Bu oy yopilgan: ma'lumotlarini faqat rahbar o'zgartira oladi.</p>}
      {hisobot && <Pnl r={hisobot} oyNom={oyYorliq(oy, joriy)} filial={pnlFilial} />}
      {oylik && <FoydaOylar oylik={oylik} oy={oy} joriy={joriy} onOy={setOy} grafikRef={grafikRef} />}
      {hisobot && <PnlQoshimcha r={hisobot} />}
    </div>
  )
}

function Pnl({ r, oyNom, filial }) {
  // Kassa usuli: pul kirgan kun tushum. Kirdi − chiqdi = sof foyda (jarima kirdi, qaytarilgan/kelmagan/xarajat/bonus chiqdi)
  const kirdi = [
    { nom: 'Avans va qoldiq', v: r.kirim, kalit: 'kirim' },
    { nom: 'Kechikish va boshqa jarimalar', v: r.jarimalar, kalit: 'jarima' },
  ].filter((x) => x.v)
  const moddalar = r.xarajat_moddalari ? r.xarajat_moddalari.map((m) => ({ nom: m.nomi, v: m.summa, kalit: 'xarajat' }))
    : [{ nom: 'Xarajatlar', v: r.xarajatlar, kalit: 'xarajat' }]
  const chiqdi = [
    { nom: 'Mijozlarga qaytarilgan', v: r.qaytarilgan, kalit: 'qaytarilgan' },
    { nom: "Kelmagan o'tkazmalar", v: r.kelmadi, kalit: 'kelmadi' },
    ...moddalar,
    { nom: 'Sotuvchi bonusi', v: r.sotuvchi_bonusi, kalit: 'bonus' },
  ].filter((x) => x.v)
  const K = kirdi.reduce((a, x) => a + x.v, 0)
  const C = chiqdi.reduce((a, x) => a + x.v, 0)
  const F = K - C
  const kirU = ulushlar(kirdi.map((x) => x.v), K)
  const chiU = ulushlar(chiqdi.map((x) => x.v), C)
  const [taf, setTaf] = useState(null)
  const [tafOy, setTafOy] = useState(`${r.oy}/${filial}`)
  if (tafOy !== `${r.oy}/${filial}`) { setTafOy(`${r.oy}/${filial}`); setTaf(null) } // oy almashsa tafsilot yopiladi
  const och = (kalit) => {
    if (taf?.qator === kalit) return setTaf(null)
    pnlTafsilot(r.oy, kalit, filial).then(setTaf).catch(() => setTaf(null))
  }
  const otgan = r.taqqos?.otgan_oy
  const taqqosNomi = (x) => `${OyTanlash.nomi(x.oy)}${x.gacha_kun ? `, 1–${x.gacha_kun}` : ''}`
  const band = (x, i, foiz, chiq) => (
    <div className="fy-band" key={`${x.kalit}-${x.nom}-${i}`}>
      <div className="fy-band-yuqori">
        <button type="button" className="pnl-havola" aria-expanded={taf?.qator === x.kalit} onClick={() => och(x.kalit)}>{x.nom}</button>
        <b>{chiq ? '− ' : ''}{raqam(x.v)}</b>
      </div>
      <div className="fy-band-pastki">
        <span className={`fy-chiziq${chiq ? ' qizil' : ''}`} aria-hidden="true"><i style={{ width: `${foiz}%` }} /></span>
        <em>{foiz}%</em>
      </div>
    </div>
  )
  return (
    <>
      {/* Egasining birinchi savoli bir qarashda: qancha kirdi, qancha chiqdi, nima qoldi — o'tgan oyning shu kunigacha bilan */}
      <section className="dash-kpi kpi-filtrlar pnl-kpi fy-kpi" aria-label="Oylik foyda ko'rsatkichlari">
        <KpiFiltr nom="Kirgan pul" son={som(K)} ikon="hamyon" rang="tilla" izoh="avans, qoldiq va jarimalar" />
        <KpiFiltr nom="Chiqqan pul" son={som(C)} ikon="chiqdi" rang="qizil" izoh={K ? `kirgan pulning ${Math.round((C / K) * 100)}%` : 'xarajat, qaytarilgan va bonus'} />
        <KpiFiltr nom={F < 0 ? 'Zarar' : 'Sof foyda'} son={som(F)} ikon="tushum" rang="yashil" xavf={F < 0}
          izoh={otgan ? `${taqqosNomi(otgan)}: ${som(otgan.sof_foyda)}` : 'kirdi − chiqdi'}
          trend={otgan && <Taqqos hozir={r.sof_foyda} oldin={otgan.sof_foyda} nomi={`${taqqosNomi(otgan)} bilan`} />} />
      </section>
      {/* «tannarxi kiritilmagan» va «tasdiqlanmagan xarajat» ogohlantirishlari — qo'ng'iroqchada (foydalanuvchi so'rovi, 2026-11-10) */}
      <div className="fy-ikki">
        <section className="blok hisobot-panel" aria-label="Qayerdan keldi, qayerga ketdi">
          <div className="hisobot-panel-bosh"><h3>Qayerdan keldi, qayerga ketdi</h3><span className="malumot">{oyNom}</span></div>
          <div className="fy-guruh">
            <p className="fy-guruh-bosh kirdi"><span>Kirdi</span><span>{som(K)}</span></p>
            {kirdi.length ? kirdi.map((x, i) => band(x, i, kirU[i], false)) : <p className="malumot fy-bosh-izoh">Bu oyda pul kirmagan.</p>}
          </div>
          <div className="fy-guruh">
            <p className="fy-guruh-bosh chiqdi"><span>Chiqdi</span><span>− {som(C)}</span></p>
            {chiqdi.length ? chiqdi.map((x, i) => band(x, i, chiU[i], true)) : <p className="malumot fy-bosh-izoh">Bu oyda pul chiqmagan.</p>}
          </div>
          <div className={`fy-natija${F < 0 ? ' zarar' : ''}`}><span>{F < 0 ? 'Zarar' : 'Sof foyda'}</span><b>{som(F)}</b></div>
          <p className="malumot">Zalog hisobga kirmaydi — u mijozning puli, qaytariladi. Foizlar — o'z guruhi ichida. Nomni bosing — yozuvlari ochiladi.</p>
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
        </section>
        <Sharshara K={K} chiqdi={chiqdi} F={F} oyNom={oyNom} jarima={r.jarimalar} />
      </div>
    </>
  )
}

// «Foyda qanday hosil bo'ldi» — sharshara: kirdi → har bir chiqim pastga → sof foyda. Chiqimlar 4 tadan ko'p bo'lsa,
// kichiklari «Boshqa»ga yig'iladi. Zararda sof foyda ustuni noldan pastga (qizil).
function Sharshara({ K, chiqdi, F, oyNom, jarima }) {
  if (!K) {
    return (
      <section className="blok hisobot-panel fy-sharshara" aria-label="Foyda qanday hosil bo'ldi">
        <div className="hisobot-panel-bosh"><h3>Foyda qanday hosil bo'ldi</h3><span className="malumot">{oyNom}</span></div>
        <p className="malumot">Bu oyda pul kirmagan — grafik chizilmaydi.</p>
      </section>
    )
  }
  const tartibli = [...chiqdi].sort((a, b) => b.v - a.v)
  const asosiy = tartibli.length > 4 ? tartibli.slice(0, 3) : tartibli
  const qolgan = tartibli.length > 4 ? tartibli.slice(3).reduce((a, x) => a + x.v, 0) : 0
  const bosqich = qolgan ? [...asosiy.map((x) => [x.nom, x.v]), ['Boshqa', qolgan]] : asosiy.map((x) => [x.nom, x.v])
  const qadam = yaxlitQadam(K - Math.min(0, F))
  const yuqori = Math.ceil(K / qadam) * qadam
  const quyi = F < 0 ? -Math.ceil(-F / qadam) * qadam : 0
  const f = (v) => Math.round(((v - quyi) / (yuqori - quyi)) * 1000) / 10
  const belgilar = []
  for (let v = quyi; v <= yuqori + 1; v += qadam) belgilar.push({ b: f(v), m: mlnQ(v), asos: v === 0 })
  const ulush = ulushlar(bosqich.map(([, v]) => v).concat(Math.max(F, 0)), K)
  let tepa = K
  const ustunlar = [{ nom: 'Kirdi', ulush: '100%', past: f(0), boy: f(K) - f(0), tepa: f(K), m: mlnQ(K), tur: 'kirdi' }]
  bosqich.forEach(([nom, v], k) => {
    const past = tepa - v
    ustunlar.push({ nom, ulush: `${ulush[k]}%`, past: f(past), boy: f(tepa) - f(past), tepa: f(tepa), m: `− ${mlnQ(v)}`, tur: 'chiqdi' })
    tepa = past
  })
  ustunlar.push(F >= 0
    ? { nom: 'Sof foyda', ulush: `${ulush[ulush.length - 1]}%`, past: f(0), boy: f(F) - f(0), tepa: f(F), m: mlnQ(F), tur: 'foyda' }
    : { nom: 'Zarar', ulush: '', past: f(F), boy: f(0) - f(F), tepa: f(0), m: `− ${mlnQ(-F)}`, tur: 'zarar' })
  const eng = tartibli[0]
  return (
    <section className="blok hisobot-panel fy-sharshara" aria-label="Foyda qanday hosil bo'ldi">
      <div className="hisobot-panel-bosh"><h3>Foyda qanday hosil bo'ldi</h3><span className="malumot">{oyNom} · so'm</span></div>
      <figure className="sh-figura" role="img" aria-label={`${oyNom}: kirdi ${mlnQ(K)}, chiqdi ${mlnQ(K - F)}, ${F < 0 ? 'zarar' : 'sof foyda'} ${mlnQ(Math.abs(F))}`}>
        <div className="sh-quti">
          {belgilar.map((b) => <div key={b.b} className={`sh-chiziq${b.asos ? ' asos' : ''}`} style={{ bottom: `${b.b}%` }}><span>{b.m}</span></div>)}
          <div className="sh-ustunlar">
            {ustunlar.map((u, i) => (
              <div key={`${u.nom}-${i}`} className={`sh-ustun ${u.tur}`}>
                <i style={{ bottom: `${u.past}%`, height: `${u.boy}%` }} />
                <span className="sh-yorliq" style={{ bottom: `calc(${u.tepa}% + 6px)` }}>{u.m}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="sh-nomlar" aria-hidden="true">
          {ustunlar.map((u, i) => <span key={`${u.nom}-${i}`}>{u.nom}{u.ulush && <small>{u.ulush}</small>}</span>)}
        </div>
      </figure>
      <div className="fy-xulosa">
        <p><NavIkona nom="foiz" className="tugma-ikon" /><span>Har 100 so'm kirgan puldan <b>{Math.max(0, Math.round((F / K) * 100))} so'm</b> {F < 0 ? 'ham qolmadi — oy zararda.' : "foyda bo'lib qoldi."}</span></p>
        {eng && <p><NavIkona nom="hamyon" className="tugma-ikon" /><span>Eng katta chiqim — <b>{eng.nom.toLowerCase()}</b>: kirgan pulning {Math.round((eng.v / K) * 100)}%.</span></p>}
        {jarima > 0 && <p><NavIkona nom="soat" className="tugma-ikon" /><span>Jarimalar kirgan pulga <b>{som(jarima)}</b> qo'shdi.</span></p>}
      </div>
    </section>
  )
}

// Pastki qator (kanvas): «Oxirgi 6 oy» chiziqli grafigi (to'liq oylar) va «Oylar bo'yicha» jadvali — oyni bosib tanlash
function FoydaOylar({ oylik, oy, joriy, onOy, grafikRef }) {
  const toliq = oylik.filter((o) => o.oy < joriy).slice(-6)
  const jadval = [...oylik].slice(-6).reverse()
  const X0 = 64, X1 = 540, Y0 = 214, Y1 = 20
  const kirdi = (o) => o.kirdi ?? o.tushum
  const maks = Math.max(1, ...toliq.map(kirdi))
  const minF = Math.min(0, ...toliq.map((o) => o.sof_foyda))
  const qadam = yaxlitQadam(maks - minF)
  const yuqori = Math.ceil(maks / qadam) * qadam
  const quyi = minF < 0 ? -Math.ceil(-minF / qadam) * qadam : 0
  const qx = toliq.length > 1 ? (X1 - X0) / (toliq.length - 1) : 0
  const xy = (v, i) => [X0 + i * qx, Y0 - ((v - quyi) / (yuqori - quyi)) * (Y0 - Y1)]
  const chegaraY = (y) => (quyi === 0 ? Math.min(Y0, y) : y)
  const silliq = (pts) => pts.map((p, i) => {
    if (i === 0) return `M${p[0].toFixed(1)},${p[1].toFixed(1)}`
    const p0 = pts[i - 2] || pts[i - 1], p1 = pts[i - 1], p3 = pts[i + 1] || p
    // salbiy qiymat bo'lmasa egri chiziq nol chizig'idan pastga «sakramasin»
    const c1 = [p1[0] + (p[0] - p0[0]) / 6, chegaraY(p1[1] + (p[1] - p0[1]) / 6)]
    const c2 = [p[0] - (p3[0] - p1[0]) / 6, chegaraY(p[1] - (p3[1] - p1[1]) / 6)]
    return `C${[...c1, ...c2, ...p].map((z) => z.toFixed(1)).join(',')}`
  }).join(' ')
  const kp = toliq.map((o, i) => xy(kirdi(o), i))
  const fp = toliq.map((o, i) => xy(o.sof_foyda, i))
  const nolY = xy(0, 0)[1]
  const yop = (d) => `${d} L${X1},${nolY} L${X0},${nolY} Z`
  const tanI = toliq.findIndex((o) => o.oy === oy)
  const panjara = []
  for (let v = quyi; v <= yuqori + 1; v += qadam) panjara.push(v)
  const oyQisqa = (o) => OYLAR[Number(o.slice(5, 7)) - 1]
  return (
    <div className="fy-pastki">
      <section className="blok hisobot-panel" aria-label="Oxirgi 6 oy" ref={grafikRef}>
        <div className="hisobot-panel-bosh">
          <h3>Oxirgi 6 oy</h3>
          <span className="fy-belgilar"><span><i className="kirdi" />Kirdi</span><span><i className="foyda" />Sof foyda</span></span>
        </div>
        <p className="malumot">{tanI >= 0 ? `${OyTanlash.nomi(oy)} ajratilgan — boshqa oyni tepadagi tugmalar yoki jadvaldan tanlang.`
          : 'Joriy oy hali tugamagani uchun grafikda yo\'q — to\'liq oylardan birini tanlang.'}</p>
        {toliq.length < 2 ? <p className="malumot">Grafik uchun kamida ikki to'liq oy kerak.</p> : (
          <figure className="fy-grafik">
            <svg viewBox="0 0 560 250" role="img" aria-label={`${toliq.map((o) => `${oyQisqa(o.oy)}: kirdi ${mlnQ(kirdi(o))}, foyda ${mlnQ(o.sof_foyda)}`).join('; ')}`}>
              <defs>
                <linearGradient id="fy-kirdi-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style={{ stopColor: 'var(--tilla)', stopOpacity: 0.34 }} /><stop offset="1" style={{ stopColor: 'var(--tilla)', stopOpacity: 0 }} /></linearGradient>
                <linearGradient id="fy-foyda-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style={{ stopColor: 'var(--yaxshi)', stopOpacity: 0.28 }} /><stop offset="1" style={{ stopColor: 'var(--yaxshi)', stopOpacity: 0 }} /></linearGradient>
              </defs>
              {panjara.map((v) => {
                const y = xy(v, 0)[1]
                return (
                  <g key={v}>
                    <line x1={X0} y1={y} x2={X1} y2={y} className={v === 0 ? 'fy-nol' : 'fy-panjara'} />
                    <text x={X0 - 10} y={y + 4} textAnchor="end" className="fy-o">{mlnQ(v)}</text>
                  </g>
                )
              })}
              {toliq.map((o, i) => <text key={o.oy} x={X0 + i * qx} y={238} textAnchor="middle" className="fy-o">{oyQisqa(o.oy)}</text>)}
              {tanI >= 0 && <rect x={kp[tanI][0] - 30} y={Y1} width="60" height={Y0 - Y1} rx="10" className="fy-tanlangan" />}
              <path d={yop(silliq(kp))} fill="url(#fy-kirdi-g)" />
              <path d={yop(silliq(fp))} fill="url(#fy-foyda-g)" />
              <path d={silliq(kp)} className="fy-chiziq-kirdi" />
              <path d={silliq(fp)} className="fy-chiziq-foyda" />
              {kp.map(([x, y], i) => <circle key={`k${i}`} cx={x} cy={y} r="3.5" className="fy-nuqta-kirdi" />)}
              {fp.map(([x, y], i) => <circle key={`f${i}`} cx={x} cy={y} r="3.5" className="fy-nuqta-foyda" />)}
            </svg>
            {tanI >= 0 && (
              <div className="fy-izoh-oyna" style={{ left: `${(kp[tanI][0] / 560) * 100}%`, top: `${(kp[tanI][1] / 250) * 100}%` }}>
                <b>{OyTanlash.nomi(oy)}</b>
                <span className="kirdi">Kirdi: {som(kirdi(toliq[tanI]))}</span>
                <span className="foyda">Sof foyda: {som(toliq[tanI].sof_foyda)}</span>
              </div>
            )}
          </figure>
        )}
      </section>
      <section className="blok hisobot-panel" aria-label="Oylar bo'yicha">
        <div className="hisobot-panel-bosh"><h3>Oylar bo'yicha</h3><span className="malumot">oyni bosing</span></div>
        <div className="hisobot-ora">
          <table className="fy-oylar">
            <thead><tr><th>Oy</th><th>Kirdi</th><th>Chiqdi</th><th>Sof foyda</th><th>Ulush</th></tr></thead>
            <tbody>
              {jadval.map((o) => {
                const k = kirdi(o)
                const c = o.chiqdi ?? k - o.sof_foyda
                return (
                  <tr key={o.oy} className={o.oy === oy ? 'tanlandi' : undefined}>
                    <td><button type="button" className="fy-oy-tugma" aria-pressed={o.oy === oy} onClick={() => onOy(o.oy)}>{oyYorliq(o.oy, joriy)}</button></td>
                    <td>{mlnQ(k)}</td>
                    <td className="fy-qizil">{mlnQ(c)}</td>
                    <td className={o.sof_foyda < 0 ? 'fy-qizil' : 'fy-yashil'}>{mlnQ(o.sof_foyda)}</td>
                    <td><span className={`fy-ulush${o.sof_foyda < 0 ? ' zarar' : ''}`}>{k ? `${Math.round((o.sof_foyda / k) * 100)}%` : '—'}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="malumot">Ulush — kirgan pulning qancha qismi foyda bo'lib qoldi.</p>
      </section>
    </div>
  )
}

// Foyda ostidagi qo'shimcha ma'lumotlar: kelgusi avanslar, libos xaridi, qarzlar, investitsiya, o'tgan yil bilan taqqos
function PnlQoshimcha({ r }) {
  const t = r.taqqos
  const taqqosNomi = (x) => `${OyTanlash.nomi(x.oy)}${x.gacha_kun ? `, 1–${x.gacha_kun}` : ''}`
  const qatorlar = [
    r.kelgusi_avanslar > 0 && ['Libosi hali berilmagan zakazlardan olingan pul', som(r.kelgusi_avanslar),
      "bugungi holat: tushumga kirgan, lekin zakaz bekor bo'lsa qoidaga ko'ra qaytarilishi mumkin"],
    r.libos_xaridi > 0 && ['Shu oy libos va aksessuar xaridi', som(r.libos_xaridi),
      r.libos_xaridi_soni > 0 ? `${r.libos_xaridi_soni} ta yangi libos; foydadan ayirilmaydi — keyingi oylarda o'zini qoplaydi` : "foydadan ayirilmaydi — keyingi oylarda o'zini qoplaydi"],
    r.libos_xaridi > 0 && ["Qo'lingizda qolgan pul", som(r.sof_foyda - r.libos_xaridi), 'foyda minus xarid', r.sof_foyda - r.libos_xaridi < 0],
    r.yetkazib_qarz > 0 && ['Yetkazib beruvchilarga qarz', som(r.yetkazib_qarz), 'bugungi holat — Liboslar › «Yetkazib beruvchilar»', true],
    r.investitsiya > 0 && ['Liboslarga sarflangan pul', som(r.investitsiya), `shundan qoplangan ${som(r.investitsiya_qoplagan)} (${r.qoplash_foiz}%)`],
    t?.otgan_yil && ["O'tgan yil", som(t.otgan_yil.sof_foyda), `${taqqosNomi(t.otgan_yil)}: tushum ${som(t.otgan_yil.tushum)} · bu oy ${ozgarish(r.tushum, t.otgan_yil.tushum)}`],
  ].filter(Boolean)
  return (
    <section className="blok hisobot-panel fy-qoshimcha" aria-label="Qo'shimcha">
      <div className="hisobot-panel-bosh"><h3>Bilish foydali</h3><span className="malumot">hisob pul kirgan kun bo'yicha</span></div>
      {qatorlar.map(([nom, v, izoh, qizil]) => (
        <div key={nom} className="fy-q-qator">
          <span><b>{nom}</b>{izoh && <small>{izoh}</small>}</span>
          <b className={qizil ? 'fy-qizil' : undefined}>{v}</b>
        </div>
      ))}
      <p className="malumot">Avans olingan kuni, qoldiq to'langan kuni tushumga kiradi. Zalog kirmaydi.
        {t?.qisman && ' Oy hali tugamagan — taqqoslash o\'tgan oylarning shu kungacha bo\'lgan qismi bilan.'}</p>
    </section>
  )
}

// Tushumning taqqoslanayotgan davrga nisbatan o'zgarishi (FT-18.1); asos 0 bo'lsa foiz hisoblanmaydi
const ozgarish = (hozir, oldin) => {
  if (!oldin) return hozir ? 'yangi' : '—'
  const f = Math.round(((hozir - oldin) / oldin) * 100)
  return `${f > 0 ? '+' : ''}${f}%`
}

const USUL = { karta: 'Terminal', otkazma: "O'tkazma", click: 'Click', payme: 'Payme' }

// FT-12.12: rahbar oyiga bir marta bank ko'chirmasidagi summani kiritadi; tizim farqni ko'rsatadi, komissiya xarajatga yoziladi.
// Kanvas (KassaBankShisha): tepada 5 ko'rsatkich, bitta jadval — usul, tizimda, komissiya, kutilgan sof, bank ko'chirmasi, farq;
// ko'chirma va komissiya qatorning o'zida kiritiladi, farq jonli hisoblanadi, «Solishtirishni saqlash» o'zgarganlarini yozadi.
function Bank({ onZakaz }) {
  const [oy, setOy] = useState(() => OyTanlash.joriy())
  const [d, setD] = useState(null)
  const [f, setF] = useState({})
  const [band, setBand] = useState(false)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  useEffect(() => {
    let bekor = false
    bankHolati(oy).then((r) => { if (!bekor) { setD(r); setF({}) } }).catch((e) => { if (!bekor) setXabar({ turi: 'xato', matn: xatoMatni(e) }) })
    return () => { bekor = true }
  }, [oy])

  const qatorlar = (d?.usullar || []).map((u) => {
    const k = f[`${u.usul}_k`] ?? (u.kochirma ?? '')
    const m = f[`${u.usul}_m`] ?? (u.komissiya ?? '')
    const kom = Number(m) || 0
    const kutilgan = u.tizimda - kom
    return { ...u, k, m, kom, kutilgan, farq: k === '' ? null : Number(k) - kutilgan,
      ozgardi: f[`${u.usul}_k`] !== undefined || f[`${u.usul}_m`] !== undefined }
  })
  const jami = (fn) => qatorlar.reduce((a, q) => a + (fn(q) || 0), 0)
  const kiritilgan = qatorlar.filter((q) => q.k !== '')
  const J = { tizim: jami((q) => q.tizimda), kom: jami((q) => q.kom), kutilgan: jami((q) => q.kutilgan),
    bank: kiritilgan.length ? jami((q) => (q.k === '' ? 0 : Number(q.k))) : null,
    farq: kiritilgan.length ? kiritilgan.reduce((a, q) => a + q.farq, 0) : null }
  const ozgarganlar = qatorlar.filter((q) => q.ozgardi && q.k !== '')
  // ko'rsatkich kartasida katta summa qisqa («22,5 mln»); aniq summa — jadvalning jami qatorida
  const qisqa = (v) => (Math.abs(v) >= 1e7 ? `${(v / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} mln` : guruhla(v))

  const saqla = async () => {
    setXabar({ turi: '', matn: '' }); setBand(true)
    try {
      let natija = d
      for (const q of ozgarganlar) natija = await bankKirit({ oy, usul: q.usul, kochirma_summa: Number(q.k), komissiya: q.kom })
      setD(natija); setF({})
      setXabar({ turi: 'ok', matn: `Saqlandi: ${ozgarganlar.map((q) => USUL[q.usul]).join(', ')}.` })
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) } finally { setBand(false) }
  }
  const farqPill = (v) => (v == null ? <span className="malumot">—</span>
    : <span className={`kassa-pill ${v === 0 ? 'yashil' : 'qizil'}`}>{v === 0 ? '0' : `${v > 0 ? '+' : '−'}${guruhla(Math.abs(v))}`}</span>)

  return (
    <div className="stack hisobot-sahifa bank-sahifa">
      <section className="dash-kpi kpi-filtrlar bank-kpi" aria-label="Bank ko'rsatkichlari">
        <KpiFiltr nom="Tizimdagi tushum" son={qisqa(J.tizim)} ikon="tushum" rang="tilla" izoh="naqdsiz to'lovlar" />
        <KpiFiltr nom="Komissiya" son={qisqa(J.kom)} ikon="foiz" rang="kok" izoh="bank ushlab qolgan" />
        <KpiFiltr nom="Kutilgan sof" son={qisqa(J.kutilgan)} ikon="bajarildi" rang="yashil" izoh="tushum − komissiya" />
        <KpiFiltr nom="Bank ko'chirmasi" son={J.bank == null ? '—' : qisqa(J.bank)} ikon="bank" rang="pushti" izoh={J.bank == null ? 'hali kiritilmagan' : `${kiritilgan.length} usul bo'yicha`} />
        <KpiFiltr nom="Farq" son={J.farq == null ? '—' : `${J.farq > 0 ? '+' : J.farq < 0 ? '−' : ''}${qisqa(Math.abs(J.farq))}`} ikon="diqqat" rang="yashil"
          xavf={J.farq != null && J.farq !== 0} izoh={J.farq == null ? 'ko\'chirma kiritilgach' : J.farq === 0 ? 'mos keldi' : 'tekshiring'} />
      </section>
      <section className="blok kassa-panel" aria-label="To'lov usullari bo'yicha">
        <div className="kassa-panel-bosh"><h3><NavIkona nom="bank" className="tugma-ikon" />To'lov usullari bo'yicha</h3>
          <OyTanlash value={oy} onChange={setOy} /></div>
        {d && qatorlar.length === 0 && <p className="malumot">Bu oyda naqdsiz to'lov yo'q.</p>}
        {qatorlar.length > 0 && (
          <div className="hisobot-ora">
            <table className="kassa-jadval bank-jadval">
              <thead><tr><th>To'lov usuli</th><th className="ong">Tizimda</th><th className="ong">Komissiya</th><th className="ong">Kutilgan sof</th>
                <th className="ong">Bank ko'chirmasi</th><th className="ong">Farq</th></tr></thead>
              <tbody>
                {qatorlar.map((q) => (
                  <tr key={q.usul}>
                    <td><b>{USUL[q.usul]}</b></td>
                    <td className="ong">{guruhla(q.tizimda)}</td>
                    <td className="ong"><SummaInput className="bank-input" aria-label={`${USUL[q.usul]} — bank komissiyasi`} value={q.m}
                      onChange={(e) => setF({ ...f, [`${q.usul}_m`]: e.target.value })} /></td>
                    <td className="ong">{guruhla(q.kutilgan)}</td>
                    <td className="ong"><SummaInput className="bank-input" aria-label={`${USUL[q.usul]} — bank ko'chirmasi`} value={q.k}
                      onChange={(e) => setF({ ...f, [`${q.usul}_k`]: e.target.value })} /></td>
                    <td className="ong">{farqPill(q.farq)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr><td>Jami</td><td className="ong">{guruhla(J.tizim)}</td><td className="ong">{guruhla(J.kom)}</td><td className="ong">{guruhla(J.kutilgan)}</td>
                  <td className="ong">{J.bank == null ? '—' : guruhla(J.bank)}</td><td className="ong">{farqPill(J.farq)}</td></tr>
              </tfoot>
            </table>
          </div>
        )}
        <div className="bank-oxir">
          <p className="izoh-q"><NavIkona nom="yordam" className="tugma-ikon" /><span>Farq = bank ko'chirmasi − (tizimdagi tushum − komissiya). Ko'chirmadagi summani
            yozing — farq o'zi hisoblanadi. Komissiya avtomatik «Bank komissiyasi» xarajati bo'lib yoziladi.</span></p>
          <button type="button" disabled={!ozgarganlar.length || band} onClick={saqla}>Solishtirishni saqlash</button>
        </div>
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role="status">{xabar.matn}</p>}
      </section>
      {/* Nima uchun kerak — egasi tushunishi uchun oddiy tilda; farq chiqsa — har usulning to'lovlar tarixi */}
      <section className="blok kassa-panel" aria-label="To'lovlar tarixi">
        <div className="kassa-panel-bosh"><h3><NavIkona nom="tarix" className="tugma-ikon" />Farq chiqsa — to'lovlar tarixi</h3></div>
        <div className="bank-izoh">
          <p><b>Nima uchun:</b> karta, Click va Payme orqali to'langan pul kassaga emas, bank hisobingizga tushadi.
            Sotuvchi «karta bilan to'ladi» deb yozgan pul haqiqatan kelganini faqat bank ko'chirmasi ko'rsatadi.</p>
          <p><b>Farq chiqsa:</b> to'lov noto'g'ri usulda yozilgan (masalan, naqd o'rniga karta) yoki pul kelmagan — quyidagi tarixdan qidiring.</p>
        </div>
        {qatorlar.map((q) => <TolovTarixi key={q.usul} nom={USUL[q.usul]} tolovlar={q.tolovlar || []} onZakaz={onZakaz} />)}
      </section>
    </div>
  )
}

// Shu usulda yozilgan to'lovlar: kim, qachon, qaysi zakazga — farq chiqsa qaysi to'lov shubhali ekanini topish uchun
const vaqtMatni = (v) => { const t = new Date(v); return `${sanaMatni(iso(t))} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}` }
function TolovTarixi({ nom, tolovlar, onZakaz }) {
  if (tolovlar.length === 0) return <p className="malumot">{nom}: bu oyda to'lov yozilmagan.</p>
  const xodimlar = {}
  for (const t of tolovlar) if (t.tasdiq !== 'kelmadi') xodimlar[t.xodim] = (xodimlar[t.xodim] || 0) + t.summa
  return (
    <details className="bank-tarix">
      <summary>{nom}: to'lovlar tarixi ({tolovlar.length}) — kim, qachon, qaysi zakazga</summary>
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
// Kanvas (HisobotBonusShisha): 4 ko'rsatkich; chapda «Sotuvchilar bo'yicha» (qator ochilsa — zakazlari), o'ngda «Formula» (tanlangan
// sotuvchi: ijara × stavka = bonus) va «Qoidalar».
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
      <section className="blok stack r2-bosh-holat bonus-ochiq-emas">
        <h3 className="sanoq-panel-nom"><NavIkona nom="sovga" className="tugma-ikon" />Sotuvchi bonusi o'chirilgan</h3>
        <p className="malumot">Yoqilsa, har oy har bir sotuvchi uchun tayyor bonus summasi shu yerda chiqadi: to'ydan keyin
          libos qaytarib olingan zakazlardan siz belgilagan foiz. Bonus foydadan avtomatik ayiriladi.</p>
        {onBolim
          ? <button type="button" className="ikkinchi" onClick={() => onBolim('sozlamalar:bonus')}>Sozlamada yoqish</button>
          : <p className="malumot">Yoqish: Sozlama → «Sotuvchi bonusi».</p>}
      </section>
    )
  }
  const sotuvchilar = d ? [...d.sotuvchilar].sort((a, b) => b.bonus - a.bonus) : []
  const zakazlar = sotuvchilar.reduce((s, q) => s + q.zakazlar, 0)
  const ijara = sotuvchilar.reduce((s, q) => s + q.tushum, 0)
  const foiz = d ? Number(d.foiz) : 0
  const formula = sotuvchilar.find((q) => q.id === ochiq) || sotuvchilar.find((q) => q.zakazlar > 0)
  return (
    <div className="stack">
      {d && (
        <section className="dash-kpi libos-kpi" aria-label="Bonus ko'rsatkichlari">
          <KpiFiltr nom="Hisobga kirgan zakazlar" son={zakazlar} ikon="hujjat" rang="kok" izoh="libos shu oyda qaytarilgan" />
          <KpiFiltr nom="Ular bo'yicha ijara" son={guruhla(ijara)} ikon="hamyon" rang="tilla" izoh="zakazlar summasi" />
          <KpiFiltr nom="Bonus stavkasi" son={`${foiz}%`} ikon="foiz" rang="pushti"
            pastki={onBolim ? <button type="button" className="kpi-pastki" onClick={() => onBolim('sozlamalar:bonus')}>Sozlamada</button> : <small>Sozlamada</small>} />
          <KpiFiltr nom="Jami bonus" son={guruhla(d.jami)} ikon="bajarildi" rang="yashil" izoh="foydadan ayiriladi" />
        </section>
      )}
      <div className="xarajat-ikki">
        <section className="blok xarajat-panel" aria-label="Sotuvchilar bo'yicha">
          <div className="sanoq-panel-bosh">
            <h3 className="sanoq-panel-nom"><Belgi nom="mijoz" className="tugma-ikon" />Sotuvchilar bo'yicha</h3>
            <OyTanlash value={oy} onChange={(v) => { setOy(v); setOchiq(null) }} />
          </div>
          {xato && <p className="xato">{xato}</p>}
          {d && (
            <table className="soz-jadval bonus-jadval">
              <thead><tr><th>Sotuvchi</th><th className="ong">Zakazlar</th><th className="ong">Ijara</th><th className="ong">Stavka</th><th className="ong">Bonus</th></tr></thead>
              <tbody>
                {sotuvchilar.map((q) => (
                  <Fragment key={q.id}>
                    <tr className={ochiq === q.id ? 'tanlangan' : ''}>
                      <td>{q.zakazlar > 0
                        ? (
                          <button type="button" className="bonus-ism" aria-expanded={ochiq === q.id} onClick={() => setOchiq(ochiq === q.id ? null : q.id)}>
                            <NavIkona nom="ong" className={`tugma-ikon bonus-chevron${ochiq === q.id ? ' ochiq' : ''}`} />
                            <span className="soz-avatar" aria-hidden="true">{q.ism.split(/\s+/).slice(0, 2).map((s) => s[0]).join('').toUpperCase()}</span>
                            <b>{q.ism}</b>
                          </button>
                        )
                        : <span className="bonus-ism"><span className="bonus-chevron-joy" /><span className="soz-avatar" aria-hidden="true">{q.ism[0]?.toUpperCase()}</span><b>{q.ism}</b></span>}</td>
                      <td className="ong">{q.zakazlar}</td><td className="ong">{guruhla(q.tushum)}</td><td className="ong">{foiz}%</td>
                      <td className="ong"><b className="bonus-summa">{guruhla(q.bonus)}</b></td>
                    </tr>
                    {ochiq === q.id && (
                      <tr className="bonus-ichki"><td colSpan={5}>
                        <table className="soz-jadval">
                          <thead><tr><th>Zakaz</th><th>Mijoz</th><th>Qaytdi</th><th className="ong">Ijara</th><th className="ong">Bonus</th></tr></thead>
                          <tbody>
                            {q.zakaz_royxati.map((z) => (
                              <tr key={z.zakaz_id}>
                                <td><b>#{z.raqam}</b></td><td>{z.mijoz}</td><td className="soz-mute">{sanaMatni(z.qaytarilgan)}</td>
                                <td className="ong">{guruhla(z.summa)}</td><td className="ong"><b className="bonus-summa">{guruhla(z.bonus)}</b></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
              <tfoot><tr><td>Jami</td><td className="ong">{zakazlar}</td><td className="ong">{guruhla(ijara)}</td><td className="ong">{foiz}%</td>
                <td className="ong"><b className="bonus-summa">{guruhla(d.jami)}</b></td></tr></tfoot>
            </table>
          )}
          <p className="aks-t-izoh"><NavIkona nom="yordam" className="tugma-ikon" />Sotuvchi ismini bosing — har bir zakaz va undan chiqqan bonus ko'rinadi.</p>
        </section>
        <div className="sanoq-ustun">
          {formula && (
            <section className="blok xarajat-panel" aria-label="Formula">
              <div className="sanoq-panel-bosh"><h3 className="sanoq-panel-nom"><Belgi nom="son" className="tugma-ikon" />Formula</h3><small>{formula.ism}</small></div>
              <div className="bonus-formula">
                <small>{guruhla(formula.tushum)} × {foiz}% =</small>
                <b>{som(formula.bonus)}</b>
              </div>
              <div className="aks-t-q"><span>Foydadan ayiriladi</span><b>zakaz qaytgan oyda, o'zi</b></div>
              <p className="soz-izoh">Bonusni berganingizda xarajatga qayta yozmang — u allaqachon hisobda.</p>
            </section>
          )}
          <section className="blok xarajat-panel" aria-label="Qoidalar">
            <h3 className="sanoq-panel-nom"><NavIkona nom="hujjat" className="tugma-ikon" />Qoidalar</h3>
            <ul className="bonus-qoidalar">
              <li>Bonus shu oyda <b>libosi qaytarib olingan</b> zakazlardan hisoblanadi.</li>
              <li>Qaytarilgan zakaz bekor qilinmaydi — bonus keyin kamaymaydi.</li>
              <li>Bonus foydadan avtomatik ayiriladi — «Oylik foyda» da alohida qator.</li>
            </ul>
            {onBolim && <button type="button" className="havola" onClick={() => onBolim('sozlamalar:bonus')}>Stavkani o'zgartirish — Sozlama →</button>}
          </section>
        </div>
      </div>
    </div>
  )
}
