import { useEffect, useMemo, useState } from 'react'
import { kalendar, xatoMatni } from '../api'
import NavIkona from '../components/NavIkona'
import KpiFiltr from '../components/KpiFiltr'
import LibosSiluet from '../components/LibosSiluet'
import { HAFTA, OYLAR, bugunIso, isoOch, kunQosh, kunlarSoni, ustun } from '../components/kalendar/sana'

// Tayyor davrlar; «dan» va «gacha» sanalari bilan istalgan davr (3 oygacha — server chegarasi) tanlanadi
const KORINISH = [['kun', 'Kun', 1], ['hafta', 'Hafta', 7], ['oy', 'Oy', 31]]
const ENG_UZUN = 93
// Ustun kengligi davr uzunligiga qarab: bir kun — keng, ikki haftagacha — o'rta, undan uzun — ixcham
const korinishi = (n) => (n === 1 ? 'kun' : n <= 14 ? 'hafta' : 'oy')
const tolaSana = (v) => v >= '2000-01-01' && v <= '2100-12-31'
const oy = (m) => OYLAR[m].toLowerCase()
const hafta = (s) => { const { y, m, d } = isoOch(s); return HAFTA[ustun(y, m, d)] }

// «2 – 8 noyabr», «28 oktabr – 3 noyabr»; boshqa yil bo'lsa yili ham
function davrNomi(dan, gacha) {
  const a = isoOch(dan), b = isoOch(gacha)
  const yil = b.y !== isoOch(bugunIso()).y ? ` ${b.y}` : ''
  if (dan === gacha) return `${a.d} ${oy(a.m)}${yil}`
  return (a.m === b.m ? `${a.d} – ${b.d} ${oy(b.m)}` : `${a.d} ${oy(a.m)} – ${b.d} ${oy(b.m)}`) + yil
}

// Libosning bir kundagi holati: bron kunlari (band — avans olingan, yoki vaqtinchalik) yoki bron ortidagi tozalash kuni
function kunHolati(l, k) {
  for (const b of l.bronlar) {
    if (k >= b.dan && k <= b.gacha) return { turi: b.turi === 'mustahkam' ? 'band' : 'vaqtinchalik', b }
    if (k > b.gacha && k <= b.band_gacha) return { turi: 'bufer', b }
  }
  return null
}

// Libos qatori bo'laklari: bitta bronning ketma-ket kunlari bitta tasma bo'lib birlashadi; bo'sh kun — alohida katak
function bolaklar(l, kunlar) {
  const natija = []
  for (const k of kunlar) {
    const h = kunHolati(l, k)
    const p = l.primerkalar?.find((x) => x.sana === k)  // eski primerka yozuvlari (FT-2.8)
    const kalit = h && !p ? `${h.turi}:${h.b.dan}` : null
    const oxirgi = natija[natija.length - 1]
    if (kalit && oxirgi?.kalit === kalit) { oxirgi.son++; oxirgi.gacha = k } else natija.push({ kalit, h, p, dan: k, gacha: k, son: 1 })
  }
  return natija
}

// QA-12: bo'sh kataklar Tab tartibida libos qatoriga bitta (birinchisi); qolganlariga strelkalar bilan yuriladi —
// ←/→ shu qatorda, ↑/↓ shu kunda boshqa libos qatoriga (129 ta Tab to'xtashi o'rniga)
function katakdanYur(e) {
  const t = e.target
  if (!t.classList?.contains('bosh-katak') || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return
  let keyingi = null
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    const katak = [...t.closest('tr').querySelectorAll('.bosh-katak')]
    keyingi = katak[katak.indexOf(t) + (e.key === 'ArrowRight' ? 1 : -1)]
  } else {
    const qatorlar = [...t.closest('table').querySelectorAll('tbody tr')]
    const qadam = e.key === 'ArrowDown' ? 1 : -1
    for (let i = qatorlar.indexOf(t.closest('tr')) + qadam; i >= 0 && i < qatorlar.length && !keyingi; i += qadam) {
      keyingi = qatorlar[i].querySelector(`.bosh-katak[data-kun="${t.dataset.kun}"]`)
    }
  }
  if (keyingi) { e.preventDefault(); keyingi.focus() }
}

// FT-2.6: bandlik kalendari — kun, hafta, oy; libos qatorlarida bron tasmasi, kun sarlavhasida nechta libos band.
// Kun bosilsa — shu kun varaqasi: kim olib ketadi, kim qaytaradi, nima ijarada, nima tozalashda.
// `onYangi({ dan, gacha, libos_id })` (R2): bo'sh katak bosilsa — shu libos va kunga oldindan to'ldirilgan Yangi zakaz.
export default function Kalendar({ onZakaz, onYangi }) {
  const [uzunlik, setUzunlik] = useState(7)
  const [bosh, setBosh] = useState(bugunIso)
  const korinish = korinishi(uzunlik)
  const [qatorlar, setQatorlar] = useState(null)
  const [xato, setXato] = useState('')
  const [q, setQ] = useState('')
  const [tanlangan, setTanlangan] = useState(null)
  const bugun = bugunIso()
  // Bo'sh katak — o'tmagan kun, bron va primerkasiz bitta kun (shu libos va kunga Yangi zakaz)
  const yangiMumkin = (s) => !s.h && !s.p && s.son === 1 && s.dan >= bugun

  const kunlar = useMemo(() => Array.from({ length: uzunlik }, (_, i) => kunQosh(bosh, i)), [bosh, uzunlik])
  const dan = kunlar[0], gacha = kunlar[kunlar.length - 1]
  // Sana klaviaturadan terilganda yil oraliq qiymatlardan o'tadi (0002, 0020…): maydon matni alohida saqlanadi,
  // kalendar esa faqat to'liq sana kiritilgach siljiydi.
  const [danMatn, setDanMatn] = useState(dan)
  const [gachaMatn, setGachaMatn] = useState(gacha)
  const davr = (s, n) => { setBosh(s); setUzunlik(n); setDanMatn(s); setGachaMatn(kunQosh(s, n - 1)) }
  const siljit = (s) => davr(s, uzunlik)
  const danTer = (v) => { setDanMatn(v); if (tolaSana(v)) { setBosh(v); setGachaMatn(kunQosh(v, uzunlik - 1)) } }
  // «gacha» — davr uzunligini o'zgartiradi (boshidan oldin yoki 3 oydan uzun bo'lsa qabul qilinmaydi)
  const gachaTer = (v) => {
    setGachaMatn(v)
    const n = tolaSana(v) ? kunlarSoni(dan, v) + 1 : 0
    if (n >= 1 && n <= ENG_UZUN) setUzunlik(n)
  }

  useEffect(() => {
    let bekor = false
    const yukla = () => kalendar(dan, gacha)
      .then((d) => { if (!bekor) { setQatorlar(d); setXato('') } })
      .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    yukla()
    const t = setInterval(yukla, 5000) // FT-1.4: bandlik o'zgarishi 5 soniyadan kam vaqtda ko'rinadi
    return () => { bekor = true; clearInterval(t) }
  }, [dan, gacha])

  const hammasi = qatorlar || []
  // Kun sarlavhasidagi son: shu kuni bron qilingan liboslar (tozalash kuni hisobga kirmaydi)
  const bandSoni = useMemo(() => Object.fromEntries(kunlar.map((k) => [k,
    (qatorlar || []).filter((l) => { const h = kunHolati(l, k); return h && h.turi !== 'bufer' }).length])), [kunlar, qatorlar])
  const qidiruv = q.trim().toLowerCase()
  const korinadi = qidiruv
    ? hammasi.filter((l) => `${l.artikul} ${l.nomi}`.toLowerCase().includes(qidiruv))
    : hammasi
  // Kategoriya bo'yicha guruhlar (backend kategoriya tartibida beradi)
  const guruhlar = []
  for (const l of korinadi) {
    if (guruhlar[guruhlar.length - 1]?.nomi !== l.kategoriya) guruhlar.push({ nomi: l.kategoriya, liboslar: [] })
    guruhlar[guruhlar.length - 1].liboslar.push(l)
  }
  // «Kun» ko'rinishida varaq doim ochiq; boshqa davrga o'tilsa tanlangan kun yopiladi
  const varaqKuni = korinish === 'kun' ? dan : kunlar.includes(tanlangan) ? tanlangan : kunlar.includes(bugun) ? bugun : dan
  // Kanvas (BandlikShisha) ko'rsatkichlari: davrdagi band ulushi, bo'sh libos-kunlar, vaqtinchalik bronlar, tozalashdagilar
  const xulosa = useMemo(() => {
    const rows = qatorlar || []
    let band = 0, bufer = 0
    const vaqt = new Set()
    for (const l of rows) for (const k of kunlar) {
      const h = kunHolati(l, k)
      if (!h) continue
      if (h.turi === 'bufer') bufer++
      else { band++; if (h.turi === 'vaqtinchalik') vaqt.add(h.b.zakaz_id ?? `${l.id}-${h.b.dan}`) }
    }
    const jami = rows.length * kunlar.length
    return { foiz: jami ? Math.round((band * 100) / jami) : 0, bosh: jami - band - bufer, vaqt: vaqt.size,
      tozalash: rows.filter((l) => l.holat === 'tozalashda').length, tamir: rows.filter((l) => l.holat === 'tamirda').length }
  }, [qatorlar, kunlar])
  const davrSoz = { kun: 'shu kuni', hafta: 'shu hafta', oy: 'shu oyda' }[korinish] || 'shu davrda'

  return (
    <div className="bandlik-sahifa">
    {qatorlar && (
      <section className="dash-kpi bandlik-kpi" aria-label="Bandlik ko'rsatkichlari">
        <KpiFiltr nom={`Band (${davrSoz})`} son={`${xulosa.foiz}%`} ikon="kun" rang="tilla" izoh={`${hammasi.length} libosdan`} />
        <KpiFiltr nom="Bo'sh libos-kunlar" son={xulosa.bosh} ikon="bajarildi" rang="yashil" izoh={`${davrSoz} berish mumkin`} />
        <KpiFiltr nom="Vaqtinchalik bron" son={xulosa.vaqt} ikon="soat" rang="sariq" izoh="avans hali olinmagan" />
        <KpiFiltr nom="Tozalash va ta'mir" son={xulosa.tozalash + xulosa.tamir} ikon="tamir" rang="kok" izoh={`tozalash ${xulosa.tozalash} · ta'mir ${xulosa.tamir}`} />
      </section>
    )}
    <div className="bandlik-tor">
    <section className="blok jadval-panel kalendar-sahifa">
      <div className="jadval-asboblar">
        <h3 className="panel-nom">Bandlik</h3>
        <div className="tezkor-tablar" role="tablist" aria-label="Ko'rinish">
          {KORINISH.map(([k, nom, n]) => (
            <button key={k} type="button" role="tab" aria-selected={uzunlik === n} className={uzunlik === n ? 'faol' : ''}
              onClick={() => davr(bosh, n)}>{nom}</button>
          ))}
        </div>
        <div className="kalendar-nav">
          <button type="button" className="ikkinchi kichik" aria-label="Oldingi davr" onClick={() => siljit(kunQosh(bosh, -uzunlik))}>‹</button>
          <span className="davr-nomi" aria-live="polite">{davrNomi(dan, gacha)}</span>
          <button type="button" className="ikkinchi kichik" aria-label="Keyingi davr" onClick={() => siljit(kunQosh(bosh, uzunlik))}>›</button>
          {bosh !== bugun && <button type="button" className="ikkinchi kichik" onClick={() => siljit(bugun)}>Bugun</button>}
        </div>
        <div className="davr-sanalar" role="group" aria-label="Davr">
          <input type="date" aria-label="Davr boshi" value={danMatn} min="2000-01-01" max="2100-12-31" onChange={(e) => danTer(e.target.value)} />
          <span aria-hidden="true">–</span>
          <input type="date" aria-label="Davr oxiri" value={gachaMatn} min={dan} max={kunQosh(dan, ENG_UZUN - 1)} onChange={(e) => gachaTer(e.target.value)} />
        </div>
        <label className="qidiruv-maydon">
          <NavIkona nom="qidiruv" className="tugma-ikon" />
          <input type="search" className="jadval-qidiruv" placeholder="Artikul yoki nomi" aria-label="Libos qidirish"
            value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
      </div>
      {/* legenda — kanvasdagidek jadval ustida */}
      <p className="bandlik-izoh">
        <span><i className="izoh-band" /> bron (avans olingan)</span>
        <span><i className="izoh-vaqtinchalik" /> vaqtinchalik bron</span>
        <span><i className="izoh-bufer" /> tozalash kuni</span>
        {hammasi.some((l) => l.primerkalar?.length) && <span><i className="primerka-belgi">P</i> primerka</span>}
      </p>
      {xato && <p className="xato jadval-bosh">{xato}</p>}
      {qatorlar !== null && korinadi.length === 0 ? (
        <p className="malumot jadval-bosh">{qidiruv ? `«${q}» bo'yicha libos topilmadi.` : "Hali libos yo'q."}</p>
      ) : (
        <div className="bandlik-ora">
          <table className={`bandlik bandlik-${korinish}`} style={{ '--kun-son': kunlar.length }} onKeyDown={katakdanYur}>
            <thead>
              <tr>
                <th className="libos-katak">Libos <small>{hammasi.length} ta</small></th>
                {kunlar.map((k, i) => {
                  const { d, m } = isoOch(k)
                  const son = bandSoni[k], ulush = hammasi.length ? son / hammasi.length : 0
                  return (
                    <th key={k} className={`${k === bugun ? 'bugun' : ''} ${k === varaqKuni ? 'tanlangan' : ''} ${d === 1 && i > 0 ? 'oy-boshi' : ''}`}>
                      <button type="button" className="kun-bosh" aria-pressed={k === varaqKuni}
                        aria-label={`${d} ${oy(m)}, ${hafta(k)[1].toLowerCase()}: ${son} libos band`}
                        onClick={() => uzunlik > 1 && setTanlangan(k === tanlangan ? null : k)}>
                        {(i === 0 || d === 1) && korinish === 'oy' && <i>{oy(m).slice(0, 3)}</i>}
                        <small>{hafta(k)[0]}</small>
                        <b>{d}</b>
                        <span className={`kun-band ${ulush >= 0.5 ? 'qizgin' : son ? 'bor' : ''}`}>{son || '·'}</span>
                      </button>
                    </th>
                  )
                })}
              </tr>
            </thead>
            {guruhlar.map((g) => (
              <tbody key={g.nomi}>
                {guruhlar.length > 1 && (
                  <tr className="bandlik-guruh"><th colSpan={kunlar.length + 1}><span>{g.nomi}<span className="tab-son">{g.liboslar.length}</span></span></th></tr>
                )}
                {g.liboslar.map((l) => { const bol = bolaklar(l, kunlar); const birinchi = bol.find(yangiMumkin)?.dan; return (
                  <tr key={l.id} className={l.holat !== 'bosh' ? 'libos-band' : ''}>
                    <th className="libos-katak" scope="row">
                      <span className="libos-katak-ichi">
                        {/* kanvas: libos surati (bo'lmasa — siluet) */}
                        <span className="bandlik-rasm" aria-hidden="true">{l.rasm ? <img src={l.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
                        <span className="libos-katak-matn">
                          <b>{l.nomi}</b>
                          <small>{l.holat !== 'bosh' ? <em>{l.holat === 'tamirda' ? "ta'mirda" : 'tozalashda'}</em> : `${l.artikul}${l.olcham ? ` · ${l.olcham}` : ''}`}</small>
                        </span>
                      </span>
                    </th>
                    {bol.map((s) => (
                      <td key={s.dan} colSpan={s.son}
                        className={`${s.h ? 'bron-katak' : ''} ${s.son === 1 && s.dan === bugun ? 'bugun' : ''} ${s.son === 1 && s.dan === varaqKuni ? 'tanlangan' : ''}`}>
                        {s.h && <Tasma s={s} onZakaz={onZakaz} />}
                        {onYangi && yangiMumkin(s) && (
                          <button type="button" className="bosh-katak" title={`${l.artikul} — ${davrNomi(s.dan, s.dan)}: yangi zakaz`}
                            data-kun={s.dan} tabIndex={s.dan === birinchi ? 0 : -1}
                            aria-label={`${l.artikul} ${l.nomi}, ${davrNomi(s.dan, s.dan)} — yangi zakaz`}
                            onClick={() => onYangi({ dan: s.dan, gacha: s.dan, libos_id: l.id })}><span aria-hidden="true">+</span></button>
                        )}
                        {s.p && (
                          <button type="button" className="primerka-belgi" title={`Primerka ${s.p.vaqt}: #${s.p.zakaz_raqami} ${s.p.mijoz}`}
                            onClick={() => onZakaz(s.p.zakaz_id)}>P</button>
                        )}
                      </td>
                    ))}
                  </tr>
                ) })}
              </tbody>
            ))}
          </table>
        </div>
      )}
    </section>
    {varaqKuni && qatorlar && (
      <aside className="blok dash-karta bandlik-yon" aria-label="Tanlangan kun">
        <KunVaraq kun={varaqKuni} qatorlar={hammasi} onZakaz={onZakaz} bugun={bugun}
          onYop={korinish === 'kun' || !tanlangan ? null : () => setTanlangan(null)} />
      </aside>
    )}
    </div>
    </div>
  )
}

// Bron tasmasi: olib ketishdan qaytarishgacha bitta chiziq; davr chetidan davom etsa — o'sha tomoni to'g'ri kesilgan
function Tasma({ s, onZakaz }) {
  const { turi, b } = s.h
  const chet = `${b.dan < s.dan ? 'chap-ochiq' : ''} ${(turi === 'bufer' ? b.band_gacha : b.gacha) > s.gacha ? 'ong-ochiq' : ''}`
  if (turi === 'bufer') return <span className={`bufer-tasma ${chet}`} title={`Tozalash · #${b.zakaz_raqami ?? ''}`} />
  const nom = b.zakaz_raqami ? `#${b.zakaz_raqami} ${b.mijoz ?? ''}` : 'band'
  const sarlavha = `${nom} · ${davrNomi(b.dan, b.gacha)}${turi === 'vaqtinchalik' ? ' · vaqtinchalik' : ''}`
  if (!b.zakaz_id) return <span className={`bron-tasma k-${turi} ${chet}`} title={sarlavha}>{nom}</span>
  return <button type="button" className={`bron-tasma k-${turi} ${chet}`} title={sarlavha} onClick={() => onZakaz(b.zakaz_id)}>{nom}</button>
}

const BOLIMLAR = [['olib', 'Olib ketadi'], ['qaytar', 'Qaytaradi'], ['ijara', 'Ijarada'], ['tozalash', 'Tozalashda']]

// Kun varaqasi: shu kungi ish zakaz bo'yicha (bitta zakazdagi bir nechta libos — bitta qatorda)
function KunVaraq({ kun, qatorlar, onZakaz, onYop, bugun }) {
  const guruh = Object.fromEntries(BOLIMLAR.map(([k]) => [k, new Map()]))
  let bosh = 0
  for (const l of qatorlar) {
    const h = kunHolati(l, kun)
    if (!h) { if (l.holat === 'bosh') bosh++; continue }
    const bolim = h.turi === 'bufer' ? 'tozalash' : h.b.dan === kun ? 'olib' : h.b.gacha === kun ? 'qaytar' : 'ijara'
    const kalit = h.b.zakaz_id ?? `libos-${l.id}`
    if (!guruh[bolim].has(kalit)) guruh[bolim].set(kalit, { b: h.b, turi: h.turi, liboslar: [] })
    guruh[bolim].get(kalit).liboslar.push(l.artikul)
  }
  const { d, m } = isoOch(kun)
  const bor = BOLIMLAR.filter(([k]) => guruh[k].size)
  return (
    <div className="kun-varaq" role="region" aria-label={`${d} ${oy(m)} kuni`}>
      <div className="kun-varaq-bosh">
        <h4><b>{d}</b> {oy(m)} <em>{hafta(kun)[1].toLowerCase()}{kun === bugun ? ', bugun' : ''}</em></h4>
        <span className="kun-varaq-xulosa">{bosh} libos bo'sh</span>
        {onYop && <button type="button" className="ikkinchi kichik" onClick={onYop}>Yopish</button>}
      </div>
      {/* kanvas: kun bo'yicha to'rt son */}
      <div className="kun-qutilar">
        <div><small>Beriladi</small><b>{guruh.olib.size}</b></div>
        <div><small>Qaytadi</small><b>{guruh.qaytar.size}</b></div>
        <div><small>Tozalashga</small><b>{guruh.tozalash.size}</b></div>
        <div className="yashil"><small>Bo'sh qoladi</small><b>{bosh}</b></div>
      </div>
      {bor.length === 0 ? (
        <p className="malumot">Bu kuni bron yo'q — hamma libos bo'sh.</p>
      ) : (
        <div className="kun-guruhlar">
          {bor.map(([k, nom]) => (
            <section key={k} className={`kun-guruh kun-${k}`}>
              <h5>{nom}<span className="tab-son">{guruh[k].size}</span></h5>
              <ul>
                {[...guruh[k].values()].map(({ b, turi, liboslar }) => {
                  const ichi = <>
                    <span><b>{b.zakaz_raqami ? `#${b.zakaz_raqami}` : 'Bron'}</b> {b.mijoz}</span>
                    <small>{liboslar.join(', ')}{turi === 'vaqtinchalik' ? ' · vaqtinchalik' : ''}</small>
                  </>
                  return (
                    <li key={b.zakaz_id ?? liboslar[0]}>
                      {b.zakaz_id
                        ? <button type="button" className={`kun-zakaz ${turi}`} onClick={() => onZakaz(b.zakaz_id)}>{ichi}</button>
                        : <div className={`kun-zakaz ${turi}`}>{ichi}</div>}
                    </li>
                  )
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
