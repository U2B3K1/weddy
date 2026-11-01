import { useCallback, useEffect, useState } from 'react'
import Salonchilar from './Salonchilar'
import NavIkona from '../components/NavIkona'
import { Bezak } from '../components/Varaq'
import { HAFTA, OYLAR, bugunIso, isoOch, kunlarSoni, ustun } from '../components/kalendar/sana'
import { mijozKarta, mijozOzgartir, mijozQoraRoyxat, mijozlar, sanaMatni, som, xatoMatni } from '../api'
import { ZAKAZ_HOLATLARI } from '../nomlar'

const MANBA = { instagram: 'Instagram', tavsiya: 'Tavsiya', salonchi: 'Salonchi', boshqa: 'Boshqa' }
const OLCHAMLAR = [['kokrak', "Ko'krak"], ['bel', 'Bel'], ['son', 'Son'], ['boy', "Bo'y"], ['oyoq_olchami', 'Oyoq kiyim']]
const holatSinfi = (h) => ({ vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopildi: 'qaytarildi', bekor: 'qarz' }[h] || 'bron')
const boshHarf = (m) => (m.fio || '').trim().charAt(0).toUpperCase() || '#'

// Ekran 14: mijozlar. To'liq ro'yxat faqat rahbarga; sotuvchi kamida 4 ta belgi bilan qidiradi (7.4, Ilova B).
// Promokodlar bu yerda emas — Sozlama → Narx va chegirma → Promokodlar (qoidalari bilan bir joyda).
export default function Mijozlar({ rahbar, onZakaz, bolim }) {
  return (
    <div className="stack">
      {bolim === 'mijozlar' && <MijozlarRoyxati rahbar={rahbar} onZakaz={onZakaz} />}
      {bolim === 'salonchilar' && <Salonchilar rahbar={rahbar} />}
    </div>
  )
}

// Ro'yxat — Katalog va Zakazlar jadvallari bilan bir xil panel: tablar, ikonali qidiruv, jadval
function MijozlarRoyxati({ rahbar, onZakaz }) {
  const [q, setQ] = useState('')
  const [qora, setQora] = useState(false)  // rahbar: faqat qora ro'yxat
  const [royxat, setRoyxat] = useState([])
  const [tanlangan, setTanlangan] = useState(null)
  const [xato, setXato] = useState('')

  useEffect(() => {
    if (!rahbar && q.trim().length < 4) return undefined
    let bekor = false
    const t = setTimeout(() => {
      mijozlar({ ...(q.trim() ? { q: q.trim() } : {}), ...(qora ? { qora_royxat: 1 } : {}) })
        .then((d) => { if (!bekor) { setRoyxat(d); setXato('') } })
        .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    }, 300)
    return () => { bekor = true; clearTimeout(t) }
  }, [q, qora, rahbar, tanlangan])

  if (tanlangan) return <Karta id={tanlangan} rahbar={rahbar} onOrqaga={() => setTanlangan(null)} onZakaz={onZakaz} />
  const qisqa = !rahbar && q.trim().length < 4
  const korinadigan = qisqa ? [] : royxat

  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar">
        <h3 className="panel-nom">Mijozlar</h3>
        {rahbar ? (
          <div className="tezkor-tablar" role="tablist" aria-label="Mijozlar">
            {[[false, 'Hammasi'], [true, "Qora ro'yxat"]].map(([k, nom]) => (
              <button key={nom} type="button" role="tab" aria-selected={qora === k} className={qora === k ? 'faol' : ''} onClick={() => setQora(k)}>{nom}</button>
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
      {!qisqa && !xato && korinadigan.length === 0 && <p className="malumot jadval-bosh">{qora ? "Qora ro'yxatda hech kim yo'q." : 'Mijoz topilmadi.'}</p>}
      {korinadigan.length > 0 && (
        <div className="jadval-ora">
          <table className="zakaz-jadval mijoz-jadval">
            <thead>
              <tr><th>Mijoz</th><th className="tor-yashir">To'y sanasi</th><th>Zakazlar</th><th className="ong">Jami</th></tr>
            </thead>
            <tbody>
              {korinadigan.map((m) => (
                <tr key={m.id} onClick={() => setTanlangan(m.id)}>
                  <td>
                    <button type="button" className="zakaz-katak">
                      <span className={`mijoz-belgi${m.qora_royxat ? ' qora' : ''}`} aria-hidden="true">{boshHarf(m)}</span>
                      <span className="zakaz-nom">
                        <b>{m.fio || 'Ismsiz'}{m.qora_royxat && <span className="holat qarz mijoz-qora">Qora ro'yxat</span>}</b>
                        <small>{m.telefon}</small>
                      </span>
                    </button>
                  </td>
                  <td className="tor-yashir">{m.toy_sanasi ? sanaMatni(m.toy_sanasi) : <span className="malumot">—</span>}</td>
                  <td>
                    <span className="zakaz-nom">
                      <span>{m.zakazlar_soni} ta</span>
                      {m.oxirgi_zakaz && <small>oxirgisi {sanaMatni(m.oxirgi_zakaz)}</small>}
                    </span>
                  </td>
                  <td className="ong"><b>{som(m.jami_summa)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

// To'y kuni varaqda — zakaz sanalari kabi katta raqam, ostida qancha qolgani
function ToyKuni({ sana }) {
  if (!sana) return <p className="varaq-izoh">To'y sanasi kiritilmagan.</p>
  const { y, m, d } = isoOch(sana)
  const qoldi = kunlarSoni(bugunIso(), sana)
  return (
    <div className="varaq-sana toy-kuni">
      <div><small>to'y kuni</small><b>{d}</b><span>{OYLAR[m].toLowerCase()} {y}</span><em>{HAFTA[ustun(y, m, d)][1].toLowerCase()}</em></div>
      <i>{qoldi > 0 ? `${qoldi} kun qoldi` : qoldi === 0 ? 'bugun' : "o'tgan"}</i>
    </div>
  )
}

function Karta({ id, rahbar, onOrqaga, onZakaz }) {
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
  const saqla = () => bajar(() => mijozOzgartir(id, {
    fio: f.fio || '', qoshimcha_telefon: f.qoshimcha_telefon || '', toy_sanasi: f.toy_sanasi || null, manba: f.manba,
    izoh: f.izoh || '', kiyim_olchami: f.kiyim_olchami || '', ...Object.fromEntries(OLCHAMLAR.map(([k]) => [k, f[k] === '' || f[k] == null ? null : Number(f[k])])),
  }), 'Saqlandi.')
  const faol = m.tarix.filter((z) => z.holat !== 'bekor')
  const olchamlar = [...(m.kiyim_olchami ? [["Kiyim o'lchami", m.kiyim_olchami]] : []),
    ...OLCHAMLAR.filter(([k]) => m[k] != null).map(([k, nom]) => [nom, k === 'oyoq_olchami' ? m[k] : `${m[k]} sm`])]

  return (
    <div className="stack karta">
      <div className="karta-bosh">
        <button className="ikkinchi karta-orqaga" aria-label="Mijozlar ro'yxatiga qaytish" onClick={onOrqaga}><NavIkona nom="chap" className="tugma-ikon" /></button>
        <h2>{m.fio || m.telefon}</h2>
        {m.qora_royxat && <span className="holat qarz">Qora ro'yxat</span>}
      </div>

      {/* Mijoz varaqasi — zakaz varaqasi bilan bir xil: ism, telefon, to'y kuni, zakazlar va o'lchamlar */}
      <section className="varaq karta-asosiy mijoz-varaq" aria-label="Mijoz ma'lumotlari">
        {m.qora_royxat && <span className="shtamp" aria-hidden="true">Qora ro'yxat</span>}
        {m.fio && <p className="varaq-kimga">{m.fio}</p>}
        <a className="varaq-telefon" href={`tel:${m.telefon}`}>{m.telefon}</a>
        {m.qoshimcha_telefon && <a className="varaq-telefon" href={`tel:${m.qoshimcha_telefon}`}>{m.qoshimcha_telefon}</a>}
        <Bezak />
        <ToyKuni sana={m.toy_sanasi} />
        <div className="mijoz-raqamlar">
          <div><b>{faol.length}</b><span>zakaz</span></div>
          <div><b>{som(faol.reduce((s, z) => s + z.jami, 0))}</b><span>jami</span></div>
          <div><b>{MANBA[m.manba] || '—'}</b><span>qayerdan keldi</span></div>
        </div>
        {olchamlar.length > 0 && (
          <dl className="mijoz-olchamlar">
            {olchamlar.map(([nom, v]) => <div key={nom}><dt>{nom}</dt><dd>{v}</dd></div>)}
          </dl>
        )}
        {m.izoh && <p className="varaq-izoh">{m.izoh}</p>}
        {m.qora_royxat && m.qora_royxat_sabab && <p className="varaq-izoh">Qora ro'yxat sababi: {m.qora_royxat_sabab}</p>}
      </section>

      <div className="karta-ong">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <details className="blok amal" open>
          <summary>Ma'lumotlarni tahrirlash</summary>
          <div className="stack">
            <label>F.I.O.<input value={f.fio || ''} onChange={set('fio')} /></label>
            <label>Qo'shimcha telefon<input inputMode="tel" value={f.qoshimcha_telefon || ''} onChange={set('qoshimcha_telefon')} /></label>
            <div className="libos-narxlar">
              <label>To'y sanasi<input type="date" value={f.toy_sanasi || ''} onChange={set('toy_sanasi')} /></label>
              <label>Qayerdan keldi
                <select value={f.manba} onChange={set('manba')}>
                  {Object.entries(MANBA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
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

      <section className="blok karta-tolovlar">
        <h3>Zakazlar tarixi ({m.tarix.length})</h3>
        {m.tarix.length === 0 && <p className="malumot">Hali zakaz yo'q.</p>}
        {m.tarix.map((z) => (
          <button key={z.id} type="button" className="tolov-qator tarix-qator" onClick={() => onZakaz(z.id)}>
            <span className="tolov-nom">
              <b>#{z.raqam} {z.liboslar.join(', ')}</b>
              <small>{sanaMatni(z.olib_ketish)}</small>
            </span>
            <span className="tarix-ong">
              <span className={`holat ${holatSinfi(z.holat)}`}>{ZAKAZ_HOLATLARI[z.holat] || z.holat}</span>
              <b className="tolov-summa">{som(z.jami)}</b>
            </span>
          </button>
        ))}
      </section>
    </div>
  )
}
