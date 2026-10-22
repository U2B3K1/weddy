import { useEffect, useState } from 'react'
import Xarajatlar from '../components/Xarajatlar'
import OylikGrafik from '../components/OylikGrafik'
import Tasdiq from '../components/Tasdiq'
import {
  bankHolati, bankKirit, bonusHisobot, dashbord, filiallar, hisobot, hisobotTafsilot, hisobotlarRoyxati, kategoriyalar,
  oylikQator, oyniOch, oyniYop, pnl, pnlTafsilot, som, xatoMatni, xodimlarBoshqaruv,
} from '../api'

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const korsat = (v, tur) => {
  if (v === null || v === undefined || v === '') return '—'
  if (tur === 'pul') return som(v)
  if (tur === 'foiz') return `${v}%`
  return String(v)
}

// FT-18.1: tayyor davrlar — oy, chorak, yil (ixtiyoriy oraliq pastdagi sana maydonlarida)
const DAVRLAR = [
  ['Shu oy', (d) => [new Date(d.getFullYear(), d.getMonth(), 1), d]],
  ["O'tgan oy", (d) => [new Date(d.getFullYear(), d.getMonth() - 1, 1), new Date(d.getFullYear(), d.getMonth(), 0)]],
  ['Shu chorak', (d) => [new Date(d.getFullYear(), Math.floor(d.getMonth() / 3) * 3, 1), d]],
  ['Shu yil', (d) => [new Date(d.getFullYear(), 0, 1), d]],
]

// 6.6: hisobotlar faqat rahbarga va faqat sahifada ko'rsatiladi — fayl sifatida yuklab olinmaydi (FT-18.3, FT-20.2).
// Bo'limlar chap paneldagi tugmalar bilan almashtiriladi (kassa uslubi): hisobot, foyda/zarar, bildirishnoma, grafik.
export default function Hisobotlar({ bolim, onBolim }) {
  if (bolim === 'pnl') return <PnlBolim />
  if (bolim === 'bildirishnoma') return <BildirishnomaBolim onBolim={onBolim} />
  if (bolim === 'grafik') return <GrafikBolim />
  return <HisobotBolim />
}

// Asosiy davr bo'yicha hisobot — turli jadvallar, tafsilot, xarajatlar, bonus va bank solishtirish.
function HisobotBolim() {
  const [royxat, setRoyxat] = useState([])
  const [kalit, setKalit] = useState('libos')
  const [dan, setDan] = useState(() => { const d = new Date(); d.setDate(1); return iso(d) })
  const [gacha, setGacha] = useState(() => iso(new Date()))
  const [h, setH] = useState(null)
  const [xato, setXato] = useState('')
  const [filtr, setFiltr] = useState({ kategoriya: '', sotuvchi: '', filial: '' })
  const [fil, setFil] = useState([])
  const [kats, setKats] = useState([])
  const [xodimlar, setXodimlar] = useState([])
  useEffect(() => {
    kategoriyalar().then((k) => setKats(k.filter((x) => x.turi === 'libos'))).catch(() => {})
    xodimlarBoshqaruv().then(setXodimlar).catch(() => {})
    filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {})
  }, [])

  useEffect(() => {
    hisobotlarRoyxati().then((r) => setRoyxat(r)).catch((e) => setXato(xatoMatni(e)))
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

  return (
    <div className="stack hisobot-sahifa">
      <BugunXulosa />
      <select value={kalit} onChange={(e) => setKalit(e.target.value)}>
        {royxat.map((r) => <option key={r.kalit} value={r.kalit}>{r.sarlavha}</option>)}
      </select>
      <div className="qator davr-tugmalar">
        {DAVRLAR.map(([nom, fn]) => (
          <button key={nom} type="button" className="ikkinchi kichik" onClick={() => { const [a, b] = fn(new Date()); setDan(iso(a)); setGacha(iso(b)) }}>{nom}</button>
        ))}
      </div>
      <div className="qator">
        <input type="date" value={dan} max={gacha} onChange={(e) => e.target.value && setDan(e.target.value)} />
        <span>—</span>
        <input type="date" value={gacha} min={dan} onChange={(e) => e.target.value && setGacha(e.target.value)} />
      </div>
      {h?.filtrlar?.includes('kategoriya') && (
        <select value={filtr.kategoriya} onChange={(e) => setFiltr({ ...filtr, kategoriya: e.target.value })}>
          <option value="">Barcha kategoriyalar</option>
          {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
        </select>
      )}
      {h?.filtrlar?.includes('sotuvchi') && (
        <select value={filtr.sotuvchi} onChange={(e) => setFiltr({ ...filtr, sotuvchi: e.target.value })}>
          <option value="">Barcha sotuvchilar</option>
          {xodimlar.map((x) => <option key={x.id} value={x.id}>{x.ism}</option>)}
        </select>
      )}
      {fil.length > 0 && h?.filtrlar?.includes('filial') && (
        <select value={filtr.filial} aria-label="Filial" onChange={(e) => setFiltr({ ...filtr, filial: e.target.value })}>
          <option value="">Barcha filiallar</option>
          {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
        </select>
      )}
      {xato && <p className="xato">{xato}</p>}
      {h && (
        <section className="blok">
          <h3>{h.sarlavha}</h3>
          {h.izoh && <p className="malumot">{h.izoh}</p>}
          {h.qatorlar.length === 0 ? <p className="malumot">Bu davrda ma'lumot yo'q.</p> : (
            <div className="hisobot-ora">
              <table className="hisobot">
                <thead>
                  <tr>{h.ustunlar.map((u) => <th key={u.nom} className={u.tur === 'matn' ? '' : 'ong'}>{u.nom}</th>)}</tr>
                </thead>
                <tbody>
                  {h.qatorlar.map((q, i) => (
                    <tr key={i}>
                      {q.map((v, j) => (
                        <td key={j} className={`${h.ustunlar[j].tur === 'matn' ? '' : 'ong'} ${typeof v === 'number' && v < 0 ? 'qizil' : ''}`}>
                          {j === 0 && h.kalitlar
                            ? <button type="button" className="havola" aria-expanded={taf?.i === i} onClick={() => och(i)}>{korsat(v, h.ustunlar[j].tur)}</button>
                            : korsat(v, h.ustunlar[j].tur)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                {h.jami && (
                  <tfoot>
                    <tr>{h.jami.map((v, j) => (
                      <td key={j} className={h.ustunlar[j].tur === 'matn' ? '' : 'ong'}>{v === null || v === '' ? '' : korsat(v, h.ustunlar[j].tur)}</td>
                    ))}</tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
          {h.kalitlar && h.qatorlar.length > 0 && !taf && <p className="malumot">Qator nomini bosing — shu davrda to'liq to'langan zakazlari ochiladi.</p>}
          {taf && (
            <div className="tafsilot">
              <b>{taf.nom} — {taf.qatorlar.length} ta zakaz</b>
              {taf.qatorlar.length === 0 ? <p className="malumot">Bu davrda to'liq to'langan zakaz yo'q.</p> : (
                <table className="jadval"><tbody>
                  {taf.qatorlar.map((q) => (
                    <tr key={q.zakaz_id} className="kichik-qator">
                      <td>{q.sana} · #{q.raqam} · {q.mijoz} · {q.liboslar.join(', ')}{q.sotuvchi ? ` · ${q.sotuvchi}` : ''}</td>
                      <td>{som(q.jami)}</td>
                    </tr>
                  ))}
                  <tr><td><b>Zakazlar jami</b></td><td><b>{som(taf.jami)}</b></td></tr>
                </tbody></table>
              )}
              <p className="malumot">Zakaz jami chegirma va ustama bilan; jadvaldagi tushum libos ijara narxi bo'yicha bo'lsa, farq qilishi mumkin.</p>
            </div>
          )}
        </section>
      )}
      <Xarajatlar />
      <Bonus />
      <Bank />
    </div>
  )
}

// Bugungi tezkor xulosa (Tushum, Smena, Olib/qaytar) — dashborddagi bilan bir xil (FT-1.2).
function BugunXulosa() {
  const [d, setD] = useState(null)
  useEffect(() => {
    let faol = true
    const yukla = async () => {
      try { const r = await dashbord('oy', ''); if (faol) setD(r.bugun) } catch { /* jimgina */ }
    }
    yukla()
    const t = setInterval(yukla, 60000)
    return () => { faol = false; clearInterval(t) }
  }, [])
  if (!d) return null
  return (
    <section className="blok bugun-xulosa">
      <h3>Bugun</h3>
      <div className="qator-btn"><span>Tushum</span><b>{som(d.tushum_jami)}</b></div>
      <div className="qator-btn"><span>Smena</span><b>{d.smena_ochiq ? 'ochiq' : 'yopiq'}</b></div>
      <div className="qator-btn"><span>Olib / qaytar</span><b>{d.olib_ketiladi} / {d.qaytariladi}</b></div>
    </section>
  )
}

// Foyda va zarar (P&L) — oy tanlash, filial bo'yicha, oyni yopish/ochish (6.2, FT-18.2).
function PnlBolim() {
  const [hisobot, setHisobot] = useState(null)
  const [oy, setOy] = useState(() => new Date().toISOString().slice(0, 7))
  const [fil, setFil] = useState([])
  const [pnlFilial, setPnlFilial] = useState('')
  const [xato, setXato] = useState('')
  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  useEffect(() => { pnl(oy, pnlFilial).then(setHisobot).catch((e) => setXato(xatoMatni(e))) }, [oy, pnlFilial])
  const [oyniYopSurov, setOyniYopSurov] = useState(false)
  const amal = (fn) => async () => {
    setXato('')
    try { await fn(); setHisobot(await pnl(oy, pnlFilial)) } catch (e) { setXato(xatoMatni(e)) }
  }
  return (
    <div className="stack hisobot-sahifa">
      {xato && <p className="xato">{xato}</p>}
      <section className="blok">
        <h3>Foyda va zarar (P&amp;L)</h3>
        <input type="month" value={oy} onChange={(e) => e.target.value && setOy(e.target.value)} />
        {fil.length > 0 && (
          <select value={pnlFilial} aria-label="Filial" onChange={(e) => setPnlFilial(e.target.value)}>
            <option value="">Butun salon</option>
            {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
          </select>
        )}
        {pnlFilial && <p className="malumot">Filial natijasi: filialga biriktirilmagan (umumiy) xarajatlar, liboslar va zakazlar bu ko'rinishga kirmaydi.</p>}
        {hisobot && <Pnl r={hisobot} filial={pnlFilial} />}
        {hisobot && (hisobot.yopilgan ? (
          <div className="stack">
            <p className="malumot">Bu oy yopilgan: ma'lumotlarini faqat rahbar o'zgartira oladi.</p>
            <button className="ikkinchi" onClick={amal(() => oyniOch(oy))}>Oyni qayta ochish</button>
          </div>
        ) : (
          <>
            <button className="ikkinchi" onClick={() => setOyniYopSurov(true)}>Oyni yopish</button>
            {oyniYopSurov && (
              <Tasdiq sarlavha={`${oy} oyini yopasizmi?`} tugma="Ha, oyni yopish"
                matn="Yopilgan oy ma'lumotlarini faqat rahbar o'zgartira oladi. Keyin «Oyni qayta ochish» orqali ochish mumkin."
                onYop={() => setOyniYopSurov(false)} onTasdiq={() => { setOyniYopSurov(false); amal(() => oyniYop(oy))() }} />
            )}
          </>
        ))}
      </section>
    </div>
  )
}

// Bildirishnomalar — dashbord ogohlantirishlari, bosilganda tegishli bo'limga olib boradi (FT-19.3).
function BildirishnomaBolim({ onBolim }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  useEffect(() => {
    let faol = true
    const yukla = async () => {
      try { const r = await dashbord('oy', ''); if (faol) setD(r) } catch (e) { if (faol) setXato(xatoMatni(e)) }
    }
    yukla()
    const t = setInterval(yukla, 60000)
    return () => { faol = false; clearInterval(t) }
  }, [])
  if (!d) return <p className="malumot">{xato || 'Yuklanmoqda…'}</p>
  const { bugun, ogohlantirishlar: og } = d
  const ogList = [
    og.kassa_farqi !== 0 && [`Kassa farqi (${og.kassa_farqi_sana}): ${som(og.kassa_farqi)}`, 'kassa'],
    og.tannarxsiz_liboslar > 0 && [`${og.tannarxsiz_liboslar} ta libosning tannarxi kiritilmagan`, 'katalog'],
    og.qarzdorlar > 0 && [`${og.qarzdorlar} ta qarzdor`, 'zakazlar'],
    og.saqlanayotgan_zaloglar > 0 && [`${og.saqlanayotgan_zaloglar} ta hujjat/tillo zalog saqlanmoqda`, 'zakazlar'],
    bugun.kechikkan > 0 && [`${bugun.kechikkan} ta kechikkan qaytarish`, 'bosh'],
    og.tugayotgan_promokodlar > 0 && [`${og.tugayotgan_promokodlar} ta promokod muddati 7 kun ichida tugaydi`, 'mijozlar'],
  ].filter(Boolean)
  return (
    <div className="stack hisobot-sahifa">
      <section className="blok ogohlantirish">
        <h3>Bildirishnomalar</h3>
        {ogList.length === 0 ? <p className="malumot">Hozircha bildirishnoma yo'q.</p> : ogList.map(([t, bolim]) => (
          <button key={t} type="button" className="havola qator-matn" onClick={() => onBolim?.(bolim)}>{t}</button>
        ))}
      </section>
    </div>
  )
}

// Oxirgi 12 oy grafigi — tushum va sof foyda, filial bo'yicha.
function GrafikBolim() {
  const [oylik, setOylik] = useState(null)
  const [fil, setFil] = useState([])
  const [pnlFilial, setPnlFilial] = useState('')
  useEffect(() => { filiallar(true).then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  useEffect(() => { oylikQator(pnlFilial).then(setOylik).catch(() => {}) }, [pnlFilial])
  return (
    <div className="stack hisobot-sahifa">
      {fil.length > 0 && (
        <select value={pnlFilial} aria-label="Filial" onChange={(e) => setPnlFilial(e.target.value)}>
          <option value="">Butun salon</option>
          {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
        </select>
      )}
      {oylik && (
        <section className="blok">
          <h3>Oxirgi 12 oy{pnlFilial ? ` · ${fil.find((f) => String(f.id) === String(pnlFilial))?.nomi || 'filial'}` : ''}</h3>
          <OylikGrafik sarlavha="Tushum" qator={oylik} kalit="tushum" />
          <OylikGrafik sarlavha="Sof foyda" qator={oylik} kalit="sof_foyda" />
          <p className="malumot">Aniq raqamlar — «Foyda va zarar» bo'limida (oy tanlang).</p>
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

function Pnl({ r, filial }) {
  // FT-18.2: hisoblanmaydigan qatorni bosganda uni tashkil qilgan zakaz va xarajatlar ochiladi
  const qatorlar = [
    [r.storno ? `1. Tushum (bekor qilinganlar storno: −${som(r.storno)})` : '1. Tushum', r.tushum, false, 'tushum'], ["2. To'g'ridan-to'g'ri xarajat", -r.togridan_togri_xarajat, false, 'togridan'],
    ['3. Yalpi foyda', r.yalpi_foyda, true],
    ['4. Operatsion xarajatlar', -r.operatsion_xarajat, false, 'operatsion'], ['5. Operatsion foyda', r.operatsion_foyda, true],
    ['6. Boshqa daromad', r.boshqa_daromad, false, 'boshqa'], [`7. Soliq (${r.soliq_foizi}%)`, -r.soliq],
    ['8. Sof foyda (zarar)', r.sof_foyda, true],
  ]
  const [taf, setTaf] = useState(null)
  const [tafOy, setTafOy] = useState(`${r.oy}/${filial}`)
  if (tafOy !== `${r.oy}/${filial}`) { setTafOy(`${r.oy}/${filial}`); setTaf(null) } // oy almashsa tafsilot yopiladi
  const och = (kalit) => {
    if (taf?.qator === kalit) return setTaf(null)
    pnlTafsilot(r.oy, kalit, filial).then(setTaf).catch(() => setTaf(null))
  }
  return (
    <>
      {r.tannarxsiz_liboslar > 0 && (
        <p className="ogohlantirish">
          {r.tannarxsiz_liboslar} ta libosning tannarxi kiritilmagan, foyda haqiqatdagidan yuqori ko'rinishi mumkin.
        </p>
      )}
      {r.tasdiqlanmagan_xarajatlar > 0 && (
        <p className="ogohlantirish">{r.tasdiqlanmagan_xarajatlar} ta xarajat hali tasdiqlanmagan va hisobga kirmagan.</p>
      )}
      <table className="jadval"><tbody>
        {qatorlar.map(([n, v, qalin, kalit]) => (
          <tr key={n}>
            <td>{qalin ? <b>{n}</b> : kalit
              ? <button type="button" className="havola" aria-expanded={taf?.qator === kalit} onClick={() => och(kalit)}>{n}</button> : n}</td>
            <td>{qalin ? <b>{som(v)}</b> : som(v)}</td>
          </tr>
        ))}
      </tbody></table>
      {taf && (
        <div className="tafsilot">
          <b>{taf.sarlavha} — {taf.qatorlar.length} ta yozuv</b>
          {taf.qatorlar.length === 0 ? <p className="malumot">Bu oyda yozuv yo'q.</p> : (
            <table className="jadval"><tbody>
              {taf.qatorlar.map((q, i) => (
                <tr key={i} className="kichik-qator"><td>{q.sana ? `${q.sana} · ` : ''}{q.matn}</td><td>{som(q.summa)}</td></tr>
              ))}
              <tr><td><b>Jami</b></td><td><b>{som(taf.jami)}</b></td></tr>
            </tbody></table>
          )}
        </div>
      )}
      {r.sotuvchi_bonusi > 0 && <p className="malumot">Operatsion xarajat ichida sotuvchi bonusi: {som(r.sotuvchi_bonusi)}</p>}
      {r.rentabellik !== null && <p className="malumot">Rentabellik: {r.rentabellik}%</p>}
      {r.taqqos && (
        <table className="jadval"><tbody>
          {[['otgan_oy', "O'tgan oy"], ['otgan_yil', "O'tgan yil, shu oy"]].map(([k, nom]) => (
            <tr key={k} className="kichik-qator">
              <td>{nom} ({r.taqqos[k].oy}): tushum {som(r.taqqos[k].tushum)}, sof foyda {som(r.taqqos[k].sof_foyda)}</td>
              <td>{ozgarish(r.tushum, r.taqqos[k].tushum)}</td>
            </tr>
          ))}
        </tbody></table>
      )}
    </>
  )
}

const USUL = { karta: 'Karta', click: 'Click', payme: 'Payme' }

// FT-12.12: rahbar oyiga bir marta bank ko'chirmasidagi summani kiritadi; tizim farqni ko'rsatadi, komissiya xarajatga yoziladi.
function Bank() {
  const [oy, setOy] = useState(() => iso(new Date()).slice(0, 7))
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
    <details className="blok amal">
      <summary>Bank ko'chirmasi bilan solishtirish</summary>
      <div className="stack">
        <input type="month" value={oy} onChange={(e) => e.target.value && setOy(e.target.value)} />
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        {d && d.usullar.map((u) => (
          <div key={u.usul} className="tasdiq">
            <span>
              <b>{USUL[u.usul]}</b> · tizimda: {som(u.tizimda)}
              {u.farq !== null && <> · farq: <b className={u.farq === 0 ? '' : 'qizil'}>{som(u.farq)}</b></>}
            </span>
            <div className="qator">
              <input type="number" min="0" placeholder="Ko'chirmadagi summa" value={f[`${u.usul}_k`] ?? u.kochirma ?? ''}
                onChange={(e) => setF({ ...f, [`${u.usul}_k`]: e.target.value })} />
              <input type="number" min="0" placeholder="Komissiya" value={f[`${u.usul}_m`] ?? u.komissiya ?? ''}
                onChange={(e) => setF({ ...f, [`${u.usul}_m`]: e.target.value })} />
              <button className="ikkinchi kichik" onClick={() => saqla(u.usul)}>Saqlash</button>
            </div>
          </div>
        ))}
        <p className="malumot">Farq = ko'chirmadagi summa − (tizimdagi tushum − komissiya). Komissiya «Bank komissiyasi» xarajati bo'lib yoziladi.</p>
      </div>
    </details>
  )
}

// FT-15.1: oy oxirida har bir sotuvchi uchun tayyor bonus summasi (funksiya sozlamalarda yoqiladi).
function Bonus() {
  const [oy, setOy] = useState(() => iso(new Date()).slice(0, 7))
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')

  useEffect(() => {
    let bekor = false
    bonusHisobot(oy).then((r) => { if (!bekor) { setD(r); setXato('') } }).catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    return () => { bekor = true }
  }, [oy])

  if (d && !d.yoqilgan) return null
  return (
    <details className="blok amal">
      <summary>Sotuvchi bonusi</summary>
      <div className="stack">
        <input type="month" value={oy} onChange={(e) => e.target.value && setOy(e.target.value)} />
        {xato && <p className="xato">{xato}</p>}
        {d && (
          <div className="hisobot-ora">
            <table className="hisobot">
              <thead><tr><th>Sotuvchi</th><th className="ong">Zakazlar</th><th className="ong">Tushum</th><th className="ong">Bonus ({Number(d.foiz)}%)</th></tr></thead>
              <tbody>
                {d.sotuvchilar.map((q) => (
                  <tr key={q.id}><td>{q.ism}</td><td className="ong">{q.zakazlar}</td><td className="ong">{som(q.tushum)}</td><td className="ong">{som(q.bonus)}</td></tr>
                ))}
              </tbody>
              <tfoot><tr><td>Jami</td><td /><td /><td className="ong">{som(d.jami)}</td></tr></tfoot>
            </table>
          </div>
        )}
        <p className="malumot">Tushum — shu oyda to'liq to'langan zakazlar. Bonus foyda va zarar hisobotida avtomatik hisobga olinadi.</p>
      </div>
    </details>
  )
}
