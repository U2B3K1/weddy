import { useCallback, useEffect, useState } from 'react'
import { som, tayyorChegirmaOzgartir, tayyorChegirmaQosh, tayyorChegirmalarHammasi, xatoMatni } from '../api'
import SummaInput from './SummaInput'

const qiymat = (t) => (t.foiz != null ? `${Number(t.foiz)}%` : som(t.summa))

// FT-11.7: rahbar oldindan tasdiqlagan chegirmalar — sotuvchi zakazda tanlasa tasdiqsiz qo'llanadi.
export default function TayyorChegirmalar() {
  const [royxat, setRoyxat] = useState([])
  const [f, setF] = useState({ nomi: '', turi: 'foiz', qiymat: '' })
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => tayyorChegirmalarHammasi().then(setRoyxat), [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const tana = (x) => ({ nomi: x.nomi.trim(), ...(x.turi === 'foiz' ? { foiz: x.qiymat, summa: null } : { summa: Number(x.qiymat), foiz: null }) })
  const yaroqli = (x) => x.nomi.trim() && Number(x.qiymat) > 0 && (x.turi !== 'foiz' || Number(x.qiymat) <= 100)
  const qosh = () => {
    const b = tana(f)
    if (b.foiz === null) delete b.foiz; else delete b.summa
    return bajar(() => tayyorChegirmaQosh(b), "Tayyor chegirma qo'shildi.").then((ok) => ok && setF({ nomi: '', turi: 'foiz', qiymat: '' }))
  }

  return (
    <section className="blok stack">
      <h3>Tayyor chegirmalar</h3>
      <p className="malumot">Sotuvchi zakazda shu ro'yxatdan tanlasa, chegirma sizning tasdig'ingizsiz darhol qo'llanadi.</p>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {royxat.length === 0 && <p className="malumot">Tayyor chegirma yo'q.</p>}
      {royxat.map((t) => (
        <Qator key={`${t.id}-${t.nomi}-${t.foiz}-${t.summa}`} t={t} tana={tana} yaroqli={yaroqli}
          onSaqla={(b, ok) => bajar(() => tayyorChegirmaOzgartir(t.id, b), ok)} />
      ))}
      <div className="stack">
        <input placeholder="Nomi (masalan, Doimiy mijoz)" value={f.nomi} maxLength={100} onChange={(e) => setF({ ...f, nomi: e.target.value })} />
        <div className="qator">
          <select value={f.turi} aria-label="Chegirma turi" onChange={(e) => setF({ ...f, turi: e.target.value, qiymat: '' })}>
            <option value="foiz">Foiz, %</option><option value="summa">Summa, so'm</option>
          </select>
          {f.turi === 'foiz'
            ? <input type="number" min="1" max="100" value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />
            : <SummaInput value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />}
        </div>
        <button className="ikkinchi" disabled={!yaroqli(f)} onClick={qosh}>Qo'shish</button>
      </div>
    </section>
  )
}

function Qator({ t, tana, yaroqli, onSaqla }) {
  const [f, setF] = useState({ nomi: t.nomi, turi: t.foiz != null ? 'foiz' : 'summa', qiymat: t.foiz != null ? Number(t.foiz) : t.summa })
  return (
    <div className={`tasdiq ${t.faol ? '' : 'bajarilgan'}`}>
      <span><b>{t.nomi}</b> · {qiymat(t)}{t.faol ? '' : ' · nofaol'}</span>
      <div className="qator">
        <input value={f.nomi} maxLength={100} aria-label="Nomi" onChange={(e) => setF({ ...f, nomi: e.target.value })} />
        <select value={f.turi} aria-label="Chegirma turi" onChange={(e) => setF({ ...f, turi: e.target.value, qiymat: '' })}>
          <option value="foiz">%</option><option value="summa">so'm</option>
        </select>
        {f.turi === 'foiz'
          ? <input type="number" min="1" value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />
          : <SummaInput value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />}
      </div>
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!yaroqli(f)} onClick={() => onSaqla(tana(f), 'Chegirma saqlandi.')}>Saqlash</button>
        <button className="ikkinchi kichik" onClick={() => onSaqla({ faol: !t.faol }, t.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')}>
          {t.faol ? 'Nofaol qilish' : 'Faollashtirish'}
        </button>
      </div>
    </div>
  )
}
