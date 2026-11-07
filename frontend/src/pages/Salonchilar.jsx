import { useCallback, useEffect, useRef, useState } from 'react'
import NavIkona from '../components/NavIkona'
import Oyna from '../components/Oyna'
import { salonchiOzgartir, salonchiQosh, salonchilar, som, xatoMatni } from '../api'

// 4.6: salonchilar (makiyaj ustalari) bazasi. Komissiya berilmaydi — faqat statistika.
// R2 (B-34): Mijozlar kabi `.jadval-panel` jadval, qidiruv; qo'shish va tahrirlash — `Oyna` da.
const telefonMatni = (t) => { const m = /^\+998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(t || ''); return m ? `+998 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : (t || '') }
const BOSH_FORMA = { ism: '', telefon: '', instagram: '', salon_nomi: '', manzil: '', izoh: '' }

export default function Salonchilar({ rahbar }) {
  const [royxat, setRoyxat] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [q, setQ] = useState('')
  const [oyna, setOyna] = useState(null)  // 'yangi' | salonchi (tahrir)

  const yukla = useCallback(() => salonchilar(rahbar ? { hammasi: 1 } : {}).then(setRoyxat), [rahbar])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const t = q.trim().toLowerCase()
  const korinadi = (royxat || []).filter((x) => !t || [x.ism, x.salon_nomi, x.telefon, x.instagram].some((v) => String(v || '').toLowerCase().includes(t)))

  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar">
        <h3 className="panel-nom">Salonchilar</h3>
        <label className="qidiruv-maydon">
          <NavIkona nom="qidiruv" className="tugma-ikon" />
          <input type="search" className="jadval-qidiruv" aria-label="Salonchi qidirish" placeholder="Ism, salon yoki telefon" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <button type="button" className="kichik r2s-oxirgi" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Salonchi</button>
      </div>
      {xabar.matn && <p className={`${xabar.turi === 'xato' ? 'xato' : 'malumot'} jadval-bosh r2s-xabar`} role="status">{xabar.matn}</p>}
      {royxat && royxat.length === 0 && (
        <div className="jadval-bosh r2s-bosh">
          <p>Hali salonchi yo'q. Salonchi — mijoz olib keladigan makiyaj ustasi yoki boshqa salon. Zakazda belgilansa, kim qancha mijoz olib kelgani shu yerda ko'rinadi.</p>
          <button type="button" className="ikkinchi" onClick={() => setOyna('yangi')}>Salonchi qo'shish</button>
        </div>
      )}
      {royxat && royxat.length > 0 && korinadi.length === 0 && <p className="malumot jadval-bosh">Bu qidiruv bo'yicha salonchi yo'q.</p>}
      {korinadi.length > 0 && (
        <div className="jadval-ora">
          <table className="zakaz-jadval r2s-jadval">
            <thead>
              <tr><th>Salonchi</th><th className="tor-yashir">Telefon</th>
                {rahbar && <><th className="ong">Mijozlar</th><th className="ong">Zakazlar summasi</th></>}
                <th aria-label="Amallar" /></tr>
            </thead>
            <tbody>
              {korinadi.map((x) => (
                <tr key={x.id} className={x.faol ? undefined : 'r2s-nofaol'} onClick={() => setOyna(x)}>
                  <td>
                    <span className="zakaz-nom">
                      <b>{x.ism}{!x.faol && <span className="holat qaytarildi r2s-holat">Nofaol</span>}</b>
                      <small>{[x.salon_nomi, x.manzil].filter(Boolean).join(' · ') || '—'}</small>
                    </span>
                  </td>
                  <td className="tor-yashir">{x.telefon ? <a href={`tel:${x.telefon}`} onClick={(e) => e.stopPropagation()}>{telefonMatni(x.telefon)}</a> : <span className="malumot">—</span>}</td>
                  {rahbar && <><td className="ong">{x.mijozlar_soni}</td><td className="ong"><b>{som(x.tushum)}</b></td></>}
                  <td className="ong"><button type="button" className="ikkinchi kichik" onClick={(e) => { e.stopPropagation(); setOyna(x) }}>Tahrirlash</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rahbar && korinadi.length > 0 && <p className="malumot jadval-bosh r2s-izoh">Mijozlar — davrdan qat'i nazar olib kelganlari; summa — ularning zakazlari. Komissiya berilmaydi.</p>}
      {oyna === 'yangi' && (
        <Oyna sarlavha="Salonchi qo'shish" onYop={() => setOyna(null)}>
          <SalonchiMaydonlar boshlangich={BOSH_FORMA} tugma="Qo'shish"
            onSaqla={(b) => bajar(() => salonchiQosh(b), "Salonchi qo'shildi.").then((ok) => { if (ok) setOyna(null); return ok })} />
        </Oyna>
      )}
      {oyna && oyna !== 'yangi' && (
        <Oyna sarlavha={oyna.ism} onYop={() => setOyna(null)}>
          <SalonchiMaydonlar tugma="Saqlash"
            boshlangich={{ ism: oyna.ism, telefon: oyna.telefon || '', instagram: oyna.instagram || '', salon_nomi: oyna.salon_nomi || '', manzil: oyna.manzil || '', izoh: oyna.izoh || '' }}
            onSaqla={(b) => bajar(() => salonchiOzgartir(oyna.id, b), 'Salonchi saqlandi.').then((ok) => { if (ok) setOyna(null); return ok })} />
          <div className="qator r2s-qoshimcha">
            {oyna.instagram && <a className="tugma-havola" href={oyna.instagram} target="_blank" rel="noreferrer">Instagram</a>}
            <button type="button" className="ikkinchi kichik"
              onClick={() => bajar(() => salonchiOzgartir(oyna.id, { faol: !oyna.faol }), oyna.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.').then((ok) => ok && setOyna(null))}>
              {oyna.faol ? 'Nofaol qilish' : 'Faollashtirish'}
            </button>
          </div>
          {oyna.faol && <p className="malumot">Nofaol salonchi yangi zakazda tanlanmaydi; statistikasi saqlanadi.</p>}
        </Oyna>
      )}
    </section>
  )
}

function SalonchiMaydonlar({ boshlangich, tugma, onSaqla }) {
  const [f, setF] = useState(boshlangich)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="stack">
      <label>Ism *<input value={f.ism} maxLength={200} onChange={set('ism')} /></label>
      <div className="libos-narxlar">
        <label>Telefon<input inputMode="tel" value={f.telefon} placeholder="masalan: +998 90 123 45 67" onChange={set('telefon')} /></label>
        <label>Instagram (@nomi yoki havola)<input value={f.instagram} onChange={set('instagram')} /></label>
      </div>
      <div className="libos-narxlar">
        <label>Salon nomi<input value={f.salon_nomi} onChange={set('salon_nomi')} /></label>
        <label>Manzil<input value={f.manzil} onChange={set('manzil')} /></label>
      </div>
      <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <button disabled={!f.ism.trim()} onClick={() => onSaqla({ ...f, ism: f.ism.trim() })}>{tugma}</button>
      {!f.ism.trim() && <p className="malumot">To'ldiring: Ism</p>}
    </div>
  )
}

// onYuborish: true/false qaytaradi yoki xato otadi — xato forma ichida ko'rsatiladi
// (yangi zakazda forma sahifa pastida, tepadagi xabar ko'rinmay qolardi).
export function SalonchiForma({ onYuborish, ochiq }) {
  const [f, setF] = useState({})
  const [yuborilmoqda, setYuborilmoqda] = useState(false)
  const [xato, setXato] = useState('')
  const quti = useRef(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yubor = async () => {
    setXato(''); setYuborilmoqda(true)
    try {
      if (await onYuborish({ ...f, ism: f.ism.trim() })) { setF({}); if (!ochiq && quti.current) quti.current.open = false }
    } catch (e) { setXato(xatoMatni(e)) } finally { setYuborilmoqda(false) }
  }
  return (
    <details ref={quti} className="blok amal" open={ochiq}>
      <summary>Salonchi qo'shish</summary>
      <div className="stack">
        <label>Ism *<input value={f.ism || ''} onChange={set('ism')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon || ''} onChange={set('telefon')} /></label>
        <label>Instagram (@nomi yoki havola)<input value={f.instagram || ''} onChange={set('instagram')} /></label>
        <label>Salon nomi<input value={f.salon_nomi || ''} onChange={set('salon_nomi')} /></label>
        <label>Manzil<input value={f.manzil || ''} onChange={set('manzil')} /></label>
        {xato && <p className="xato">{xato}</p>}
        <button type="button" disabled={!f.ism?.trim() || yuborilmoqda} onClick={yubor}>
          {yuborilmoqda ? "Qo'shilmoqda…" : "Qo'shish"}
        </button>
      </div>
    </details>
  )
}
