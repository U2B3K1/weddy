import { useCallback, useEffect, useState } from 'react'
import Promokodlar from './Promokodlar'
import Salonchilar from './Salonchilar'
import { mijozKarta, mijozOzgartir, mijozQoraRoyxat, mijozlar, sanaMatni, som, xatoMatni } from '../api'
import { ZAKAZ_HOLATLARI } from '../nomlar'

const MANBA = { instagram: 'Instagram', tavsiya: 'Tavsiya', salonchi: 'Salonchi', boshqa: 'Boshqa' }
const OLCHAMLAR = [['kokrak', "Ko'krak"], ['bel', 'Bel'], ['son', 'Son'], ['boy', "Bo'y"], ['oyoq_olchami', 'Oyoq kiyim']]

// Ekran 14: mijozlar. To'liq ro'yxat faqat rahbarga; sotuvchi kamida 4 ta belgi bilan qidiradi (7.4, Ilova B).
export default function Mijozlar({ rahbar, onZakaz, bolim, promoYoq }) {
  return (
    <div className="stack">
      {bolim === 'mijozlar' && <MijozlarRoyxati rahbar={rahbar} onZakaz={onZakaz} />}
      {bolim === 'salonchilar' && <Salonchilar rahbar={rahbar} />}
      {bolim === 'promokodlar' && rahbar && promoYoq && <Promokodlar />}
    </div>
  )
}

function MijozlarRoyxati({ rahbar, onZakaz }) {
  const [q, setQ] = useState('')
  const [royxat, setRoyxat] = useState([])
  const [tanlangan, setTanlangan] = useState(null)
  const [xato, setXato] = useState('')

  useEffect(() => {
    if (!rahbar && q.trim().length < 4) return undefined
    let bekor = false
    const t = setTimeout(() => {
      mijozlar(q.trim() ? { q: q.trim() } : {})
        .then((d) => { if (!bekor) { setRoyxat(d); setXato('') } })
        .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    }, 300)
    return () => { bekor = true; clearTimeout(t) }
  }, [q, rahbar, tanlangan])

  if (tanlangan) return <Karta id={tanlangan} rahbar={rahbar} onOrqaga={() => setTanlangan(null)} onZakaz={onZakaz} />
  const korinadigan = !rahbar && q.trim().length < 4 ? [] : royxat

  return (
    <div className="stack">
      <input placeholder="Telefon yoki ism" value={q} onChange={(e) => setQ(e.target.value)} />
      {!rahbar && q.trim().length < 4 && <p className="malumot">Qidirish uchun telefon yoki ismning kamida 4 ta belgisini kiriting.</p>}
      {xato && <p className="xato">{xato}</p>}
      {korinadigan.map((m) => (
        <button key={m.id} className={`qator-btn ${m.qora_royxat ? 'qizil' : ''}`} onClick={() => setTanlangan(m.id)}>
          <span><b>{m.fio || 'Ismsiz'}</b> · {m.telefon}{m.qora_royxat ? " · qora ro'yxat" : ''}</span>
          <span>{m.zakazlar_soni} ta zakaz</span>
        </button>
      ))}
      {(rahbar || q.trim().length >= 4) && korinadigan.length === 0 && <p className="malumot">Mijoz topilmadi.</p>}
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

  return (
    <div className="stack">
      <button className="ikkinchi" onClick={onOrqaga}>← Mijozlar</button>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {m.qora_royxat && <p className="ogohlantirish"><b>Qora ro'yxat:</b> {m.qora_royxat_sabab}</p>}

      <section className="blok stack">
        <h3>{m.telefon}</h3>
        <label>F.I.O.<input value={f.fio || ''} onChange={set('fio')} /></label>
        <label>Qo'shimcha telefon<input inputMode="tel" value={f.qoshimcha_telefon || ''} onChange={set('qoshimcha_telefon')} /></label>
        <label>To'y sanasi<input type="date" value={f.toy_sanasi || ''} onChange={set('toy_sanasi')} /></label>
        <label>Manba
          <select value={f.manba} onChange={set('manba')}>
            {Object.entries(MANBA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label>Kiyim o'lchami (libosdagidek: 44, M …) — libos tanlashda filtrga o'zi qo'yiladi
          <input value={f.kiyim_olchami || ''} onChange={set('kiyim_olchami')} />
        </label>
        <p className="malumot">O'lchamlar (sm, ixtiyoriy)</p>
        <div className="olcham-tor">
          {OLCHAMLAR.map(([k, nom]) => (
            <label key={k}>{nom}<input type="number" value={f[k] ?? ''} onChange={set(k)} /></label>
          ))}
        </div>
        <label>Izoh<input value={f.izoh || ''} onChange={set('izoh')} /></label>
        <button onClick={saqla}>Saqlash</button>
      </section>

      {rahbar && (
        <section className="blok stack">
          <h3>Qora ro'yxat</h3>
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
        </section>
      )}

      <section className="blok">
        <h3>Zakazlar tarixi ({m.tarix.length})</h3>
        {m.tarix.length === 0 && <p className="malumot">Hali zakaz yo'q</p>}
        {m.tarix.map((z) => (
          <button key={z.id} className="qator-btn" onClick={() => onZakaz(z.id)}>
            <span><b>#{z.raqam}</b> {sanaMatni(z.olib_ketish)} · {z.liboslar.join(', ')}</span>
            <span>{ZAKAZ_HOLATLARI[z.holat] || z.holat} · {som(z.jami)}</span>
          </button>
        ))}
      </section>
    </div>
  )
}
