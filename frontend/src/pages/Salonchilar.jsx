import { useCallback, useEffect, useState } from 'react'
import { salonchiOzgartir, salonchiQosh, salonchilar, som, xatoMatni } from '../api'

// 4.6: salonchilar (makiyaj ustalari) bazasi. Komissiya berilmaydi — faqat statistika (FT-6.5).
export default function Salonchilar({ rahbar }) {
  const [royxat, setRoyxat] = useState([])
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => salonchilar(rahbar ? { hammasi: 1 } : {}).then(setRoyxat), [rahbar])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      <SalonchiForma onYuborish={(b) => bajar(() => salonchiQosh(b), "Salonchi qo'shildi.")} />
      {royxat.length === 0 && <p className="malumot">Salonchi yo'q.</p>}
      {royxat.map((s) => (
        <div key={s.id} className={`blok stack ${s.faol ? '' : 'bajarilgan'}`}>
          <div>
            <b>{s.ism}</b>{s.salon_nomi ? ` · ${s.salon_nomi}` : ''}{!s.faol ? ' · nofaol' : ''}
            {s.telefon && <> · <a href={`tel:${s.telefon}`}>{s.telefon}</a></>}
          </div>
          {s.manzil && <p className="malumot">{s.manzil}</p>}
          {rahbar && <p className="malumot">Olib kelgan mijozlar: {s.mijozlar_soni} · tushum: {som(s.tushum)}</p>}
          <div className="qator">
            {s.instagram && <a className="tugma-havola" href={s.instagram} target="_blank" rel="noreferrer">Instagram</a>}
            <button className="ikkinchi kichik" onClick={() => bajar(() => salonchiOzgartir(s.id, { faol: !s.faol }), s.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')}>
              {s.faol ? 'Nofaol qilish' : 'Faollashtirish'}
            </button>
          </div>
          <SalonchiTahrir s={s} onSaqla={(b) => bajar(() => salonchiOzgartir(s.id, b), 'Salonchi saqlandi.')} />
        </div>
      ))}
    </div>
  )
}

function SalonchiTahrir({ s, onSaqla }) {
  const [f, setF] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const och = (e) => e.target.open && !f && setF({
    ism: s.ism, telefon: s.telefon || '', instagram: s.instagram || '', salon_nomi: s.salon_nomi || '',
    manzil: s.manzil || '', izoh: s.izoh || '',
  })
  return (
    <details className="amal" onToggle={och}>
      <summary>Tahrirlash</summary>
      {f && (
        <div className="stack">
          <label>Ism<input value={f.ism} onChange={set('ism')} /></label>
          <label>Telefon<input inputMode="tel" value={f.telefon} onChange={set('telefon')} /></label>
          <label>Instagram (@nomi yoki havola)<input value={f.instagram} onChange={set('instagram')} /></label>
          <label>Salon nomi<input value={f.salon_nomi} onChange={set('salon_nomi')} /></label>
          <label>Manzil<input value={f.manzil} onChange={set('manzil')} /></label>
          <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
          <button className="ikkinchi" disabled={!f.ism.trim()} onClick={() => onSaqla({ ...f, ism: f.ism.trim() })}>Saqlash</button>
        </div>
      )}
    </details>
  )
}

export function SalonchiForma({ onYuborish, ochiq }) {
  const [f, setF] = useState({})
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <details className="blok amal" open={ochiq}>
      <summary>Salonchi qo'shish</summary>
      <div className="stack">
        <label>Ism<input value={f.ism || ''} onChange={set('ism')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon || ''} onChange={set('telefon')} /></label>
        <label>Instagram (@nomi yoki havola)<input value={f.instagram || ''} onChange={set('instagram')} /></label>
        <label>Salon nomi<input value={f.salon_nomi || ''} onChange={set('salon_nomi')} /></label>
        <label>Manzil<input value={f.manzil || ''} onChange={set('manzil')} /></label>
        <button disabled={!f.ism?.trim()} onClick={() => onYuborish({ ...f, ism: f.ism.trim() }).then((ok) => ok && setF({}))}>Qo'shish</button>
      </div>
    </details>
  )
}
