import { useCallback, useEffect, useState } from 'react'
import { mavsumiyOchir, mavsumiyOzgartir, mavsumiyQosh, mavsumiyNarxlar, xatoMatni } from '../api'

const KUNLAR = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']
const BOSH = { nomi: '', foiz: '', boshlanish: '', tugash: '' }

// Mavjud qoidaning nomi, foizi va sanalarini tuzatish (hafta kunlari o'zgarmaydi — buning uchun qoidani qayta yarating).
function QoidaTahrir({ q, onSaqla }) {
  const [f, setF] = useState({ nomi: q.nomi, foiz: Number(q.foiz), boshlanish: q.boshlanish || '', tugash: q.tugash || '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tayyor = f.nomi.trim() && Number(f.foiz) > 0 && (!!f.boshlanish === !!f.tugash) && (f.boshlanish || q.hafta_kunlari)
  return (
    <details className="amal">
      <summary>Tahrirlash</summary>
      <div className="stack">
        <label>Nomi<input value={f.nomi} maxLength={100} onChange={set('nomi')} /></label>
        <label>Ustama, %<input type="number" min="1" max="500" value={f.foiz} onChange={set('foiz')} /></label>
        <div className="qator keng">
          <label>Boshlanish<input type="date" value={f.boshlanish} onChange={set('boshlanish')} /></label>
          <label>Tugash<input type="date" value={f.tugash} min={f.boshlanish || undefined} onChange={set('tugash')} /></label>
        </div>
        <button className="ikkinchi" disabled={!tayyor}
          onClick={() => onSaqla({ nomi: f.nomi.trim(), foiz: f.foiz, boshlanish: f.boshlanish || null, tugash: f.tugash || null })}>Saqlash</button>
      </div>
    </details>
  )
}

// FT-15.2: rahbar sanalar oralig'i va hafta kunlari uchun ustama foizini kiritadi.
export default function MavsumiyNarx() {
  const [qoidalar, setQoidalar] = useState([])
  const [f, setF] = useState(BOSH)
  const [kunlar, setKunlar] = useState([])
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

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
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {qoidalar.length === 0 && <p className="malumot">Qoida yo'q — ustama qo'shilmaydi.</p>}
      {qoidalar.map((q) => (
        <div key={q.id} className={`tasdiq ${q.faol ? '' : 'bajarilgan'}`}>
          <span>
            <b>{q.nomi}</b> · +{Number(q.foiz)}%
            {q.boshlanish && ` · ${q.boshlanish} – ${q.tugash}`}
            {q.hafta_kunlari && ` · ${q.hafta_kunlari.map((k) => KUNLAR[k]).join(', ')}`}
            {!q.faol && " · o'chirilgan"}
          </span>
          <div className="qator">
            <button className="ikkinchi kichik" onClick={() => bajar(() => mavsumiyOzgartir(q.id, { faol: !q.faol }), q.faol ? "Qoida o'chirildi." : 'Qoida yoqildi.')}>
              {q.faol ? "O'chirish" : 'Yoqish'}
            </button>
            <button className="ikkinchi kichik" onClick={() => bajar(() => mavsumiyOchir(q.id), 'Qoida olib tashlandi.')}>Olib tashlash</button>
          </div>
          <QoidaTahrir key={`${q.nomi}-${q.foiz}-${q.boshlanish}-${q.tugash}`} q={q}
            onSaqla={(b) => bajar(() => mavsumiyOzgartir(q.id, b), 'Qoida saqlandi.')} />
        </div>
      ))}
      <details className="amal">
        <summary>Qoida qo'shish</summary>
        <div className="stack">
          <label>Nomi (masalan, To'y mavsumi)<input value={f.nomi} maxLength={100} onChange={set('nomi')} /></label>
          <label>Ustama, %<input type="number" min="1" max="500" value={f.foiz} onChange={set('foiz')} /></label>
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
        </div>
      </details>
    </div>
  )
}
