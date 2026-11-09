import { useCallback, useEffect, useState } from 'react'
import Salonchilar from './Salonchilar'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
import KpiFiltr from '../components/KpiFiltr'
import { BoshAmal } from '../components/BoshJoy'
import { HAFTA, OYLAR, bugunIso, isoOch, kunlarSoni, ustun } from '../components/kalendar/sana'
import { mijozKarta, mijozOzgartir, mijozQoraRoyxat, mijozSonlari, mijozlarSahifa, sanaMatni, som, xatoMatni } from '../api'
import { ZAKAZ_HOLATLARI } from '../nomlar'

const MANBA = { instagram: 'Instagram', telegram: 'Telegram', tavsiya: 'Tavsiya', salonchi: 'Salonchi', boshqa: 'Boshqa' }
const SAHIFA = 50
// filtr: '' (hammasi) | 'qora' (qora ro'yxat) | ko'rsatkich kartasi turi — 'yangi', 'toy', 'qarzdor' (faqat rahbar)
const sorov = (q, filtr, offset) => ({
  ...(q.trim() ? { q: q.trim() } : {}), ...(filtr === 'qora' ? { qora_royxat: 1 } : filtr ? { tur: filtr } : {}), limit: SAHIFA, offset,
})
// Rahbar ko'rsatkich kartalari (maket uslubi): bosilsa ro'yxat shu bo'yicha, yana bosilsa — hammasi
const KORSATKICHLAR = [
  { k: '', nom: 'Jami mijozlar', ikon: 'mijoz', rang: 'tilla', son: (s) => s.jami, izoh: (s) => `${s.qora} tasi qora ro'yxatda` },
  { k: 'yangi', nom: 'Yangi mijozlar', ikon: 'bajarildi', rang: 'yashil', son: (s) => s.yangi, izoh: (s) => `oxirgi ${s.davr} kunda` },
  { k: 'toy', nom: "Yaqin to'ylar", ikon: 'kun', rang: 'kok', son: (s) => s.toy, izoh: (s) => `to'yi ${s.davr} kun ichida` },
  { k: 'qarzdor', nom: 'Qarzdorlar', ikon: 'hamyon', rang: 'pushti', son: (s) => s.qarzdor, xavf: (s) => s.qarzdor > 0,
    izoh: (s) => (s.qarzdor > 0 ? `jami ${som(s.qarz_jami)}` : "qarz yo'q") },
]
// «+998942153650» → «+998 94 215 36 50» (boshqa ko'rinishdagi raqam o'zgarmaydi)
const telefonMatni = (t) => { const m = /^\+998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(t || ''); return m ? `+998 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : (t || '') }
const OLCHAMLAR = [['kokrak', "Ko'krak"], ['bel', 'Bel'], ['son', 'Son'], ['boy', "Bo'y"], ['oyoq_olchami', 'Oyoq kiyim']]
const holatSinfi = (h) => ({ vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopildi: 'qaytarildi', bekor: 'qarz' }[h] || 'bron')
const boshHarf = (m) => (m.fio || '').trim().charAt(0).toUpperCase() || '#'

// Ekran 14: mijozlar. To'liq ro'yxat faqat rahbarga; sotuvchi kamida 4 ta belgi bilan qidiradi (7.4, Ilova B).
// Promokodlar bu yerda emas — Sozlama → Narx va chegirma → Promokodlar (qoidalari bilan bir joyda).
// `onYangiZakaz({ telefon, fio })` (ixtiyoriy, App uzatadi) — mijoz kartasidan oldindan to'ldirilgan Yangi zakaz; berilmasa tugma yo'q
export default function Mijozlar({ rahbar, onZakaz, bolim, onYangiZakaz }) {
  return (
    <div className="stack">
      {bolim === 'mijozlar' && <MijozlarRoyxati rahbar={rahbar} onZakaz={onZakaz} onYangiZakaz={onYangiZakaz} />}
      {bolim === 'salonchilar' && <Salonchilar rahbar={rahbar} />}
    </div>
  )
}

// Ro'yxat — Katalog va Zakazlar jadvallari bilan bir xil panel: tablar, ikonali qidiruv, jadval
function MijozlarRoyxati({ rahbar, onZakaz, onYangiZakaz }) {
  const [q, setQ] = useState('')
  const [filtr, setFiltr] = useState('')  // rahbar: '' | 'qora' | 'yangi' | 'toy' | 'qarzdor'
  const [sonlar, setSonlar] = useState(null)
  const [royxat, setRoyxat] = useState([])
  const [jami, setJami] = useState(0)
  const [tanlangan, setTanlangan] = useState(null)
  const [korilgan, setKorilgan] = useState(null)  // o'ng panel: sichqoncha ostidagi qator (bo'lmasa — birinchisi)
  const [xato, setXato] = useState('')
  const [band, setBand] = useState(false)

  // B-32: sahifalab — oxirgi zakaz bo'yicha 50 tadan; «Yana» qolganini qo'shadi (avval jimgina 200/50 ta bilan kesilardi)
  useEffect(() => {
    if (!rahbar && q.trim().length < 4) return undefined
    let bekor = false
    const t = setTimeout(() => {
      mijozlarSahifa(sorov(q, filtr, 0))
        .then((d) => { if (!bekor) { setRoyxat(d.natija); setJami(d.jami); setXato('') } })
        .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    }, 300)
    return () => { bekor = true; clearTimeout(t) }
  }, [q, filtr, rahbar, tanlangan])
  useEffect(() => {
    if (rahbar && !tanlangan) mijozSonlari().then(setSonlar).catch(() => {})
  }, [rahbar, tanlangan])
  const yana = () => {
    setBand(true)
    mijozlarSahifa(sorov(q, filtr, royxat.length)).then((d) => { setRoyxat([...royxat, ...d.natija]); setJami(d.jami) })
      .catch((e) => setXato(xatoMatni(e))).finally(() => setBand(false))
  }
  const bugun = bugunIso()

  if (tanlangan) return <Karta id={tanlangan} rahbar={rahbar} onOrqaga={() => setTanlangan(null)} onZakaz={onZakaz} onYangiZakaz={onYangiZakaz} />
  const qisqa = !rahbar && q.trim().length < 4
  const korinadigan = qisqa ? [] : royxat
  const korinadiganMijoz = korinadigan.find((m) => m.id === korilgan) || korinadigan[0] || null

  const nomlar = { yangi: 'Yangi mijozlar', toy: "Yaqin to'ylar", qarzdor: 'Qarzdorlar' }
  return (
    <div className="stack mijoz-sahifa">
      {/* kanvas: ro'yxatda bo'lim boshida «+ Yangi zakaz» (mijoz kartasida — o'z tugmasi bor) */}
      {onYangiZakaz && (
        <BoshAmal><button type="button" className="bosh-tugma" onClick={() => onYangiZakaz()}><NavIkona nom="qosh" className="tugma-ikon" />Yangi zakaz</button></BoshAmal>
      )}
      {rahbar && (
        <section className="dash-kpi mijoz-kpi kpi-filtrlar" aria-label="Mijozlar ko'rsatkichlari">
          {KORSATKICHLAR.map((c) => (
            <KpiFiltr key={c.k || 'jami'} nom={c.nom} ikon={c.ikon} rang={c.rang} son={sonlar ? c.son(sonlar) : null}
              izoh={sonlar ? c.izoh(sonlar) : ''} xavf={sonlar && c.xavf?.(sonlar)} tanlangan={filtr === c.k}
              onBos={() => setFiltr(filtr === c.k ? '' : c.k)} />
          ))}
        </section>
      )}
      <div className="mijoz-tor">
      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">{nomlar[filtr] || 'Mijozlar'}</h3>
          {rahbar ? (
            <div className="tezkor-tablar" role="tablist" aria-label="Mijozlar">
              {[['', 'Hammasi'], ['qora', "Qora ro'yxat"]].map(([k, nom]) => (
                <button key={nom} type="button" role="tab" aria-selected={filtr === k} className={filtr === k ? 'faol' : ''} onClick={() => setFiltr(k)}>{nom}</button>
              ))}
            </div>
          ) : <span className="tezkor-tablar" />}
          <label className="qidiruv-maydon">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" aria-label="Mijoz qidirish" placeholder="Telefon yoki ism" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
        </div>
        {xato && <p className="xato jadval-bosh">{xato}</p>}
        {qisqa && <p className="malumot jadval-bosh">Qidirish uchun telefon yoki ismning kamida 4 ta belgisini kiriting.</p>}
        {!qisqa && !xato && korinadigan.length === 0 && (
          <p className="malumot jadval-bosh">{filtr === 'qora' ? "Qora ro'yxatda hech kim yo'q." : filtr ? `${nomlar[filtr]} yo'q.` : 'Mijoz topilmadi.'}</p>
        )}
        {korinadigan.length > 0 && (
          <Tasma className="jadval-ora" pastki={84}>
            <table className="zakaz-jadval mijoz-jadval">
              <thead>
                {/* kanvas (MijozBolimShisha) ustunlari: Mijoz │ To'y │ Oxirgi zakaz │ Jami ijara │ Qoldiq */}
                <tr><th>Mijoz</th><th className="tor-yashir">To'y</th><th>Oxirgi zakaz</th><th className="ong tor-yashir">Jami ijara</th><th className="ong">Qoldiq</th></tr>
              </thead>
              <tbody>
                {korinadigan.map((m) => (
                  <tr key={m.id} onClick={() => setTanlangan(m.id)} onMouseEnter={() => setKorilgan(m.id)} onFocus={() => setKorilgan(m.id)}
                    className={korinadiganMijoz?.id === m.id ? 'korilgan' : undefined}>
                    <td>
                      <button type="button" className="zakaz-katak">
                        <span className={`mijoz-belgi${m.qora_royxat ? ' qora' : ''}`} aria-hidden="true">{boshHarf(m)}</span>
                        <span className="zakaz-nom">
                          <b>{m.fio || 'Ismsiz'}{m.qora_royxat && <span className="holat qarz mijoz-qora">Qora ro'yxat</span>}</b>
                          <small>{telefonMatni(m.telefon)}</small>
                        </span>
                      </button>
                    </td>
                    <td className="tor-yashir">{m.toy_sanasi ? (
                      <span className="zakaz-nom"><span>{sanaMatni(m.toy_sanasi)}</span><small>{toyQachon(m.toy_sanasi, bugun)}</small></span>
                    ) : <span className="malumot">—</span>}</td>
                    <td>{m.oxirgi ? (
                      <span className="mijoz-oxirgi"><span>#{m.oxirgi.raqam}{m.oxirgi.libos ? ` · ${m.oxirgi.libos}` : ''}</span>
                        <span className={`holat ${HOLAT_SINF[m.oxirgi.holat] || ''}`}>{ZAKAZ_HOLATLARI[m.oxirgi.holat]}</span></span>
                    ) : <span className="malumot">{m.zakazlar_soni ? `${m.zakazlar_soni} ta` : '—'}</span>}</td>
                    <td className="ong tor-yashir"><b>{som(m.jami_summa)}</b></td>
                    <td className="ong">{m.qoldiq > 0 ? <b className="mijoz-qoldiq">{som(m.qoldiq)}</b> : <span className="malumot">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tasma>
        )}
        {korinadigan.length > 0 && (
          <div className="r2-yana jadval-bosh">
            <span className="malumot">{korinadigan.length} / {jami} ko'rsatildi{jami > korinadigan.length && !rahbar ? ' — aniqroq qidiring' : ''}</span>
            {jami > korinadigan.length && (
              <button type="button" className="ikkinchi kichik" disabled={band} onClick={yana}>Yana {Math.min(SAHIFA, jami - korinadigan.length)} ta</button>
            )}
          </div>
        )}
      </section>
      {/* kanvas: o'ngda — tanlangan (sichqoncha ostidagi yoki birinchi) mijoz va yaqin to'ylar */}
      {korinadiganMijoz && (
        <aside className="mijoz-yon" aria-label="Tanlangan mijoz">
          <MijozOldindan m={korinadiganMijoz} bugun={bugun} onOch={() => setTanlangan(korinadiganMijoz.id)} />
          {rahbar && <YaqinToylar bugun={bugun} onOch={setTanlangan} />}
        </aside>
      )}
      </div>
    </div>
  )
}

// kanvas qutilarida summa «so'm»siz (ixcham)
const sonMatn = (n) => som(n).replace(/\s*so'm$/, '')
const HOLAT_SINF = { vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopilgan: 'yopilgan' }
const bosHarflar = (ism) => (ism || '#').trim().split(/\s+/).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
// «4 kundan keyin», «ertaga», «bugun», «o'tgan»
function toyQachon(sana, bugun) {
  const d = kunlarSoni(bugun, sana)
  return d === 0 ? 'bugun' : d === 1 ? 'ertaga' : d > 1 ? `${d} kundan keyin` : "o'tgan"
}

// O'ng panel: mijoz qisqacha — kanvasdagi «Tanlangan mijoz» kartasi (to'liq karta — «Profilni ochish»)
function MijozOldindan({ m, bugun, onOch }) {
  return (
    <section className="blok mijoz-oldindan">
      <div className="mo-bosh">
        <span className="km-avatar" aria-hidden="true">{bosHarflar(m.fio)}</span>
        <div className="mo-ism"><h3>{m.fio || 'Ismsiz'}</h3><small>{telefonMatni(m.telefon)}</small>
          <span className="mo-teglar">
            {m.zakazlar_soni >= 2 && <span className="holat bron">Doimiy mijoz</span>}
            {m.qora_royxat && <span className="holat qarz">Qora ro'yxat</span>}
          </span>
        </div>
      </div>
      <div className="km-sanalar">
        <div><small>Zakazlar</small><b>{m.zakazlar_soni}</b></div>
        <div><small>Jami ijara</small><b>{sonMatn(m.jami_summa)}</b></div>
        <div><small>Qoldiq</small><b className={m.qoldiq > 0 ? 'mijoz-qoldiq' : undefined}>{sonMatn(m.qoldiq || 0)}</b></div>
      </div>
      {m.oxirgi && (
        <div className="mo-oxirgi"><small>Oxirgi zakaz</small>
          <span><b>#{m.oxirgi.raqam}{m.oxirgi.libos ? ` · ${m.oxirgi.libos}` : ''}</b>
            <span className={`holat ${HOLAT_SINF[m.oxirgi.holat] || ''}`}>{ZAKAZ_HOLATLARI[m.oxirgi.holat]}</span></span>
          <small>{sanaMatni(m.oxirgi.olib_ketish)}</small>
        </div>
      )}
      <div className="mijoz-qator"><span>To'y</span><b>{m.toy_sanasi ? `${sanaMatni(m.toy_sanasi)} · ${toyQachon(m.toy_sanasi, bugun)}` : 'kiritilmagan'}</b></div>
      <div className="qator mo-tugmalar">
        <button type="button" className="ikkinchi kichik" onClick={onOch}>Profilni ochish</button>
        {m.telefon && <a className="mo-qongiroq" href={`tel:${m.telefon}`}><NavIkona nom="telefon" className="tugma-ikon" />Qo'ng'iroq</a>}
      </div>
    </section>
  )
}

// Yaqin to'ylar (30 kun) — rahbarga, o'ng panel ostida
function YaqinToylar({ bugun, onOch }) {
  const [r, setR] = useState(null)
  useEffect(() => {
    mijozlarSahifa(sorov('', 'toy', 0))
      .then((d) => setR([...d.natija].sort((a, b) => String(a.toy_sanasi).localeCompare(String(b.toy_sanasi))).slice(0, 5)))
      .catch(() => setR([]))
  }, [])
  if (!r || r.length === 0) return null
  return (
    <section className="blok mijoz-toylar" aria-label="Yaqin to'ylar">
      <p className="panel-nom">Yaqin to'ylar</p>
      <ul>
        {r.map((m) => (
          <li key={m.id}><button type="button" onClick={() => onOch(m.id)}>
            <span><b>{m.fio || telefonMatni(m.telefon)}</b><small>{sanaMatni(m.toy_sanasi)}</small></span>
            <span className="holat bron">{toyQachon(m.toy_sanasi, bugun)}</span>
          </button></li>
        ))}
      </ul>
    </section>
  )
}

const qoldiMatn = (qoldi) => (qoldi > 0 ? `${qoldi} kun qoldi` : qoldi === 0 ? 'bugun' : "o'tgan")

// To'y kuni — «Profil haqida» panelida ixcham qator: sana, hafta kuni va qancha qolgani (shisha uslubi)
function ToyKuni({ sana }) {
  if (!sana) return <div className="mijoz-qator toy-kuni"><span>To'y kuni</span><b>kiritilmagan</b></div>
  const { y, m, d } = isoOch(sana)
  return (
    <div className="mijoz-qator toy-kuni"><span>To'y kuni</span>
      <b>{d} {OYLAR[m].toLowerCase()} {y}, {HAFTA[ustun(y, m, d)][1].toLowerCase()} · {qoldiMatn(kunlarSoni(bugunIso(), sana))}</b>
    </div>
  )
}

function Karta({ id, rahbar, onOrqaga, onZakaz, onYangiZakaz }) {
  const [m, setM] = useState(null)
  const [f, setF] = useState({})
  const [sabab, setSabab] = useState('')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => mijozKarta(id).then((d) => { setM(d); setF(d) }), [id])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla() } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }
  if (!m) return <p className="malumot">{xabar.matn || 'Yuklanmoqda…'}</p>
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  // Ro'yxatda yo'q eski qiymat o'zgartirilmagan bo'lsa yuborilmaydi (server rad etardi, boshqa maydonlar ham saqlanmasdi)
  const manbaYuboriladi = f.manba !== m.manba || !m.manba || MANBA[m.manba]
  const saqla = () => bajar(() => mijozOzgartir(id, {
    fio: f.fio || '', qoshimcha_telefon: f.qoshimcha_telefon || '', toy_sanasi: f.toy_sanasi || null,
    ...(manbaYuboriladi ? { manba: f.manba || '' } : {}),
    izoh: f.izoh || '', kiyim_olchami: f.kiyim_olchami || '', ...Object.fromEntries(OLCHAMLAR.map(([k]) => [k, f[k] === '' || f[k] == null ? null : Number(f[k])])),
  }), 'Saqlandi.')
  const faol = m.tarix.filter((z) => z.holat !== 'bekor')
  const olchamlar = [...(m.kiyim_olchami ? [["Kiyim o'lchami", m.kiyim_olchami]] : []),
    ...OLCHAMLAR.filter(([k]) => m[k] != null).map(([k, nom]) => [nom, k === 'oyoq_olchami' ? m[k] : `${m[k]} sm`])]

  // Shisha uslubi (kanvas «Mijoz profili»): sarlavha — belgi, ism va ma'lumot qatori; 3 ko'rsatkich; chapda zakazlar, o'ngda profil
  const harf = (m.fio || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0]).join('').toUpperCase()
  const birinchi = faol.length ? faol[faol.length - 1] : null  // tarix raqam bo'yicha kamayib boradi — oxirgisi birinchi zakaz
  // kanvas: to'lanmagan qoldiq (faol zakazlar) va eng yaqin ish (kelgusi yoki mijozdagi zakaz)
  const qoldiqlilar = faol.filter((z) => z.qoldiq > 0)
  const qoldiqJami = qoldiqlilar.reduce((sum, z) => sum + z.qoldiq, 0)
  const keyingi = [...faol].filter((z) => ['vaqtinchalik', 'chegirma_kutilmoqda', 'bron', 'berildi'].includes(z.holat))
    .sort((a, b) => String(a.olib_ketish).localeCompare(String(b.olib_ketish)))[0]
  return (
    <div className="stack karta mijoz-karta">
      <div className="karta-bosh mijoz-sarlavha">
        <button className="ikkinchi karta-orqaga" aria-label="Mijozlar ro'yxatiga qaytish" onClick={onOrqaga}><NavIkona nom="chap" className="tugma-ikon" /></button>
        <span className="mijoz-avatar" aria-hidden="true">{harf}</span>
        <div className="mijoz-sarlavha-matn">
          <h2>{m.fio || telefonMatni(m.telefon)}</h2>
          <div className="mijoz-meta">
            <a href={`tel:${m.telefon}`}><NavIkona nom="telefon" className="tugma-ikon" />{telefonMatni(m.telefon)}</a>
            {m.qoshimcha_telefon && <a href={`tel:${m.qoshimcha_telefon}`}><NavIkona nom="telefon" className="tugma-ikon" />{telefonMatni(m.qoshimcha_telefon)}</a>}
            {m.toy_sanasi && <span>To'y: {sanaMatni(m.toy_sanasi)}</span>}
            {m.manba && <span>{MANBA[m.manba] || m.manba} orqali</span>}
            {faol.length > 1 && <span className="holat-pill bron">Doimiy mijoz · {faol.length} zakaz</span>}
            {m.qora_royxat && <span className="holat qarz">Qora ro'yxat</span>}
          </div>
        </div>
        {/* Qaytgan mijoz: telefon va ism Yangi zakazga o'zi qo'yiladi (qayta terish va xato yo'q) */}
        {onYangiZakaz && (
          <button type="button" className="kichik r2m-yangi" onClick={() => onYangiZakaz({ telefon: m.telefon, fio: m.fio || '' })}>
            <NavIkona nom="qosh" className="tugma-ikon" />Yangi zakaz
          </button>
        )}
      </div>

      {/* kanvas: to'lanmagan qoldiq haqida ogohlantirish qatori */}
      {qoldiqlilar.length > 0 && (
        <p className="ogohlantirish mijoz-ogoh" role="status">
          <span><b>Qoldiq {som(qoldiqJami)} to'lanmagan</b> — #{qoldiqlilar[0].raqam} {qoldiqlilar[0].liboslar[0] || ''}, {sanaMatni(qoldiqlilar[0].olib_ketish)}</span>
          <button type="button" className="ikkinchi kichik" onClick={() => onZakaz(qoldiqlilar[0].id)}>Zakazni ochish</button>
        </p>
      )}
      <section className="dash-kpi mijoz-kpi" aria-label="Mijoz ko'rsatkichlari">
        <div className="dash-kpi-karta">
          <span className="kpi-plitka tilla"><NavIkona nom="zakazlar" className="kpi-ikon" /></span>
          <div className="kpi-matn"><span className="kpi-nom">Zakazlar</span><b>{faol.length}</b>
            <small>{birinchi ? `birinchisi — ${sanaMatni(birinchi.olib_ketish)}` : "hali zakaz yo'q"}</small></div>
        </div>
        <div className="dash-kpi-karta">
          <span className="kpi-plitka kok"><NavIkona nom="kassa" className="kpi-ikon" /></span>
          <div className="kpi-matn"><span className="kpi-nom">Jami ijara</span><b>{som(faol.reduce((s, z) => s + z.jami, 0))}</b>
            <small>bekor qilinganlarsiz</small></div>
        </div>
        <div className={`dash-kpi-karta${qoldiqJami ? ' xavf' : ''}`}>
          <span className="kpi-plitka pushti"><NavIkona nom="kassa" className="kpi-ikon" /></span>
          <div className="kpi-matn"><span className="kpi-nom">Qoldiq</span><b className={qoldiqJami ? 'mijoz-qoldiq' : undefined}>{som(qoldiqJami)}</b>
            <small>{qoldiqlilar.length ? `#${qoldiqlilar[0].raqam} · ${qoldiqlilar[0].liboslar[0] || 'libos'}` : "qarz yo'q"}</small></div>
        </div>
      </section>

      <div className="karta-ong">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        {/* kanvas «Keyingi ish»: eng yaqin faol zakaz — qachon, qancha qoldiq */}
        {keyingi && (
          <section className="blok mijoz-keyingi" aria-label="Keyingi ish">
            <h3>Keyingi ish</h3>
            <button type="button" className="mk-zakaz" onClick={() => onZakaz(keyingi.id)}>
              <span className="mk-rasm" aria-hidden="true">{keyingi.rasm ? <img src={keyingi.rasm} alt="" /> : <NavIkona nom="katalog" />}</span>
              <span className="mk-matn"><b>{keyingi.liboslar[0] || 'Zakaz'} {keyingi.holat === 'berildi' ? 'mijozda' : 'beriladi'}</b>
                <small>#{keyingi.raqam} · {sanaMatni(keyingi.olib_ketish)} – {sanaMatni(keyingi.qaytarish)}</small></span>
            </button>
            <div className="mijoz-qator"><span>Olinadigan qoldiq</span><b className={keyingi.qoldiq ? 'mijoz-qoldiq' : undefined}>{som(keyingi.qoldiq)}</b></div>
            <div className="mijoz-qator"><span>To'langan</span><b>{som(keyingi.tolangan)}</b></div>
          </section>
        )}
        {/* Profil haqida: to'y kuni, qayerdan keldi, o'lchamlar, izoh */}
        <section className="blok mijoz-varaq" aria-label="Profil haqida">
          <h3>Profil haqida</h3>
          <ToyKuni sana={m.toy_sanasi} />
          <div className="mijoz-qator"><span>Qayerdan keldi</span><b>{MANBA[m.manba] || m.manba || '—'}</b></div>
          {m.qoshilgan && <div className="mijoz-qator"><span>Qo'shilgan</span><b>{sanaMatni(String(m.qoshilgan).slice(0, 10))}</b></div>}
          {m.qoshgan && <div className="mijoz-qator"><span>Qo'shgan xodim</span><b>{m.qoshgan}</b></div>}
          {olchamlar.length > 0 && (
            <dl className="mijoz-olchamlar">
              {olchamlar.map(([nom, v]) => <div key={nom}><dt>{nom}</dt><dd>{v}</dd></div>)}
            </dl>
          )}
          {m.izoh && <p className="malumot">{m.izoh}</p>}
          {m.qora_royxat && m.qora_royxat_sabab && <p className="malumot">Qora ro'yxat sababi: {m.qora_royxat_sabab}</p>}
        </section>
        {/* Tahrir bloki yopiq: ma'lumot varaqada ko'rinib turibdi, telefonda sahifa cho'zilmaydi (B-33) */}
        <details className="blok amal">
          <summary>Ma'lumotlarni tahrirlash</summary>
          <div className="stack">
            <label>F.I.O.<input value={f.fio || ''} onChange={set('fio')} /></label>
            <label>Qo'shimcha telefon<input inputMode="tel" value={f.qoshimcha_telefon || ''} onChange={set('qoshimcha_telefon')} /></label>
            <div className="libos-narxlar">
              <label>To'y sanasi<input type="date" value={f.toy_sanasi || ''} onChange={set('toy_sanasi')} /></label>
              <label>Qayerdan keldi
                <select value={f.manba || ''} onChange={set('manba')}>
                  <option value="">— ko'rsatilmagan —</option>
                  {Object.entries(MANBA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  {f.manba && !MANBA[f.manba] && <option value={f.manba}>{f.manba} (eski qiymat)</option>}
                </select>
              </label>
            </div>
            <label>Kiyim o'lchami (libosdagidek: 44, M …)
              <input value={f.kiyim_olchami || ''} onChange={set('kiyim_olchami')} />
            </label>
            <p className="malumot">O'lchamlar, sm (ixtiyoriy) — libos tanlashda filtrga o'zi qo'yiladi</p>
            <div className="olcham-tor">
              {OLCHAMLAR.map(([k, nom]) => (
                <label key={k}>{nom}<input type="number" value={f[k] ?? ''} onChange={set(k)} /></label>
              ))}
            </div>
            <label>Izoh<input value={f.izoh || ''} onChange={set('izoh')} /></label>
            <button onClick={saqla}>Saqlash</button>
          </div>
        </details>

        {rahbar && (
          <details className="blok amal">
            <summary>Qora ro'yxat</summary>
            <div className="stack">
              {m.qora_royxat ? (
                <button className="ikkinchi" onClick={() => bajar(() => mijozQoraRoyxat(id, false), "Qora ro'yxatdan chiqarildi.")}>
                  Qora ro'yxatdan chiqarish
                </button>
              ) : (
                <>
                  <label>Sabab<input placeholder="Masalan: libosni buzib qaytargan" value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
                  <button className="xavfli" disabled={!sabab.trim()}
                    onClick={() => bajar(() => mijozQoraRoyxat(id, true, sabab), "Qora ro'yxatga qo'shildi.")}>Qora ro'yxatga qo'shish</button>
                </>
              )}
            </div>
          </details>
        )}
      </div>

      <section className="blok karta-tolovlar jadval-panel">
        <h3>Zakazlar ({m.tarix.length})</h3>
        {m.tarix.length === 0 && <p className="malumot">Hali zakaz yo'q.</p>}
        {m.tarix.length > 0 && (
          <div className="jadval-ora">
            <table className="zakaz-jadval mijoz-zakazlar">
              <thead><tr><th>Zakaz</th><th>Libos</th><th className="tor-yashir">Ijara muddati</th><th>Holat</th>
                <th className="ong tor-yashir">Ijara</th><th className="ong tor-yashir">To'langan</th><th className="ong">Qoldiq</th></tr></thead>
              <tbody>
                {m.tarix.map((z) => (
                  <tr key={z.id} className="tarix-qator" onClick={() => onZakaz(z.id)}>
                    <td><button type="button" className="mk-raqam">#{z.raqam}</button></td>
                    <td><span className="mk-libos"><span className="mk-rasm" aria-hidden="true">{z.rasm ? <img src={z.rasm} alt="" loading="lazy" /> : <NavIkona nom="katalog" />}</span>
                      <span className="zakaz-nom"><b>{z.liboslar.join(', ') || '—'}</b>{z.olcham && <small>o'lcham {z.olcham}</small>}</span></span></td>
                    <td className="tor-yashir">{sanaMatni(z.olib_ketish).slice(0, 5)}{z.qaytarish && z.qaytarish !== z.olib_ketish ? ` – ${sanaMatni(z.qaytarish).slice(0, 5)}` : ''}</td>
                    <td><span className={`holat ${holatSinfi(z.holat)}`}>{ZAKAZ_HOLATLARI[z.holat] || z.holat}</span></td>
                    <td className="ong tor-yashir">{som(z.jami)}</td>
                    <td className="ong tor-yashir">{som(z.tolangan)}</td>
                    <td className="ong">{z.qoldiq > 0 ? <b className="mijoz-qoldiq">{som(z.qoldiq)}</b> : <span className="malumot">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
