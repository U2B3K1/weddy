import { useCallback, useEffect, useState } from 'react'
import { mavsumiyOchir, mavsumiyOzgartir, mavsumiyQosh, mavsumiyNarxlar, sanaMatni, xatoMatni } from '../api'
import Tasdiq from './Tasdiq'

const KUNLAR = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']
const BOSH = { nomi: '', foiz: '', boshlanish: '', tugash: '' }

// Mavjud qoidaning nomi, foizi va sanalarini tuzatish (hafta kunlari o'zgarmaydi — buning uchun qoidani qayta yarating).
function QoidaTahrir({ q, onSaqla }) {
  const [f, setF] = useState({ nomi: q.nomi, foiz: Number(q.foiz), boshlanish: q.boshlanish || '', tugash: q.tugash || '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tayyor = f.nomi.trim() && Number(f.foiz) > 0 && (!!f.boshlanish === !!f.tugash) && (f.boshlanish || q.hafta_kunlari)
  return (
    <div className="stack soz-tahrir">
      <label>Nomi<input value={f.nomi} maxLength={100} onChange={set('nomi')} /></label>
      <label>Ustama, %<input type="number" min="1" max="500" value={f.foiz} onChange={set('foiz')} /></label>
      <div className="qator keng">
        <label>Boshlanish<input type="date" value={f.boshlanish} onChange={set('boshlanish')} /></label>
        <label>Tugash<input type="date" value={f.tugash} min={f.boshlanish || undefined} onChange={set('tugash')} /></label>
      </div>
      <div className="soz-tugmalar">
        <button type="button" className="kichik" disabled={!tayyor}
          onClick={() => onSaqla({ nomi: f.nomi.trim(), foiz: f.foiz, boshlanish: f.boshlanish || null, tugash: f.tugash || null })}>Saqlash</button>
      </div>
    </div>
  )
}

// Kanvas qatori: «nom · +10% · kunlar» va holat; o'ngda Tahrirlash / O'chirish / Olib tashlash
function QoidaQator({ q, bajar, onOlibTashla }) {
  const [tahrir, setTahrir] = useState(false)
  return (
    <div className={`tasdiq soz-royxat-q${q.faol ? '' : ' bajarilgan'}`}>
      <div className="soz-qator">
        <span className="soz-matn">
          <b>
            {q.nomi} · +{Number(q.foiz)}%
            {q.boshlanish && ` · ${sanaMatni(q.boshlanish)} – ${sanaMatni(q.tugash)}`}
            {q.hafta_kunlari && ` · ${q.hafta_kunlari.map((k) => KUNLAR[k]).join(', ')}`}
          </b>
          <small>{q.faol ? "yoqilgan — mos kunda zakaz narxiga qo'shiladi" : "o'chirilgan — narxga ta'sir qilmaydi"}</small>
        </span>
        <span className="soz-ong">
          <button type="button" className="havola" aria-expanded={tahrir} onClick={() => setTahrir(!tahrir)}>Tahrirlash</button>
          <button type="button" className="havola soz-mute-havola" onClick={() => bajar(() => mavsumiyOzgartir(q.id, { faol: !q.faol }), q.faol ? "Qoida o'chirildi." : 'Qoida yoqildi.')}>
            {q.faol ? "O'chirish" : 'Yoqish'}
          </button>
          <button type="button" className="havola soz-mute-havola" onClick={onOlibTashla}>Olib tashlash</button>
        </span>
      </div>
      {tahrir && <QoidaTahrir q={q} onSaqla={(b) => bajar(() => mavsumiyOzgartir(q.id, b), 'Qoida saqlandi.').then((ok) => ok && setTahrir(false))} />}
    </div>
  )
}

// FT-15.2: rahbar sanalar oralig'i va hafta kunlari uchun ustama foizini kiritadi.
export default function MavsumiyNarx() {
  const [qoidalar, setQoidalar] = useState([])
  const [f, setF] = useState(BOSH)
  const [kunlar, setKunlar] = useState([])
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [olibTashla, setOlibTashla] = useState(null)

  const yukla = useCallback(() => mavsumiyNarxlar().then((r) => setQoidalar(r.qoidalar)), [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const kun = (i) => setKunlar(kunlar.includes(i) ? kunlar.filter((x) => x !== i) : [...kunlar, i])
  const tayyor = f.nomi.trim() && Number(f.foiz) > 0 && ((f.boshlanish && f.tugash) || (!f.boshlanish && !f.tugash && kunlar.length > 0))

  const qosh = () => bajar(() => mavsumiyQosh({
    nomi: f.nomi.trim(), foiz: f.foiz, boshlanish: f.boshlanish || null, tugash: f.tugash || null,
    hafta_kunlari: kunlar.length > 0 ? kunlar : null,
  }), "Qoida qo'shildi.").then((ok) => { if (ok) { setF(BOSH); setKunlar([]) } })

  return (
    <>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'soz-izoh'}>{xabar.matn}</p>}
      {qoidalar.length === 0 && <p className="soz-izoh">Qoida yo'q — ustama qo'shilmaydi.</p>}
      {qoidalar.map((q) => <QoidaQator key={q.id} q={q} bajar={bajar} onOlibTashla={() => setOlibTashla(q)} />)}
      {olibTashla && (
        <Tasdiq sarlavha={`«${olibTashla.nomi}» qoidasi olib tashlansinmi?`} tugma="Ha, olib tashlash"
          matn="Qaytarib bo'lmaydi. Vaqtincha to'xtatish uchun «O'chirish» yetarli — qoida saqlanib qoladi."
          onYop={() => setOlibTashla(null)}
          onTasdiq={() => { const q = olibTashla; setOlibTashla(null); bajar(() => mavsumiyOchir(q.id), 'Qoida olib tashlandi.') }} />
      )}
      <details className="amal soz-qosh-details">
        <summary>Qoida qo'shish</summary>
        <div className="stack">
          <label>Nomi *<input value={f.nomi} maxLength={100} placeholder="masalan: To'y mavsumi" onChange={set('nomi')} /></label>
          <label>Ustama, % *<input type="number" min="1" max="500" value={f.foiz} onChange={set('foiz')} /></label>
          <div className="qator keng">
            <label>Boshlanish<input type="date" value={f.boshlanish} onChange={set('boshlanish')} /></label>
            <label>Tugash<input type="date" value={f.tugash} min={f.boshlanish || undefined} onChange={set('tugash')} /></label>
          </div>
          <fieldset className="guruh">
            <legend>Hafta kunlari (belgilanmasa — har kuni)</legend>
            <div className="qator kunlar">
              {KUNLAR.map((nom, i) => (
                <label key={nom}><input type="checkbox" checked={kunlar.includes(i)} onChange={() => kun(i)} />{nom}</label>
              ))}
            </div>
          </fieldset>
          <p className="malumot">Sanalar bo'sh qolsa, qoida butun yil tanlangan hafta kunlarida ishlaydi. Bir kunga bir nechta qoida to'g'ri kelsa, eng kattasi olinadi.</p>
          <button disabled={!tayyor} onClick={qosh}>Qo'shish</button>
          {!tayyor && <p className="malumot r2-sabab">To'ldiring: {[!f.nomi.trim() && 'Nomi', !(Number(f.foiz) > 0) && 'Ustama',
            !((f.boshlanish && f.tugash) || (!f.boshlanish && !f.tugash && kunlar.length > 0)) && 'ikkala sana yoki hafta kunlari'].filter(Boolean).join(', ')}</p>}
        </div>
      </details>
    </>
  )
}
