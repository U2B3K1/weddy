import { useCallback, useEffect, useState } from 'react'
import { som, tayyorChegirmaOzgartir, tayyorChegirmaQosh, tayyorChegirmalarHammasi, xatoMatni } from '../api'
import SummaInput from './SummaInput'
import { SPanel, Yorliq } from './SozlamaUI'

const qiymat = (t) => (t.foiz != null ? `${Number(t.foiz)}%` : som(t.summa))

// FT-11.7: rahbar oldindan tasdiqlagan chegirmalar — sotuvchi zakazda tanlasa tasdiqsiz qo'llanadi.
// Kanvas: panel, har chegirma — qator «nom · qiymat» va «Tahrirlash»; «Qo'shish» — panel tepasida.
export default function TayyorChegirmalar() {
  const [royxat, setRoyxat] = useState([])
  const [f, setF] = useState({ nomi: '', turi: 'foiz', qiymat: '' })
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [forma, setForma] = useState(false)
  const [ochiq, setOchiq] = useState(null)  // tahrirlanayotgan chegirma id si (saqlangach ham ochiq qoladi)

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
    return bajar(() => tayyorChegirmaQosh(b), "Tayyor chegirma qo'shildi.").then((ok) => { if (ok) { setF({ nomi: '', turi: 'foiz', qiymat: '' }); setForma(false) } })
  }

  return (
    <SPanel id="chegirmalar" ikon="foiz" nomi="Tayyor chegirmalar" izoh="Sotuvchi bir bosishda beradi — rahbar tasdig'isiz"
      ong={<button type="button" className="ikkinchi kichik" aria-expanded={forma} onClick={() => setForma(!forma)}>{forma ? 'Yopish' : 'Chegirma qo\'shish'}</button>}>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'soz-izoh'}>{xabar.matn}</p>}
      {forma && (
        <div className="soz-tahrir soz-qosh">
          <input placeholder="Nomi (masalan, Doimiy mijoz)" aria-label="Chegirma nomi" value={f.nomi} maxLength={100} onChange={(e) => setF({ ...f, nomi: e.target.value })} />
          <div className="soz-tugmalar">
            <select className="soz-tanlov" value={f.turi} aria-label="Chegirma turi" onChange={(e) => setF({ ...f, turi: e.target.value, qiymat: '' })}>
              <option value="foiz">Foiz, %</option><option value="summa">Summa, so'm</option>
            </select>
            {f.turi === 'foiz'
              ? <input type="number" min="1" max="100" value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />
              : <SummaInput value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />}
            <button type="button" className="kichik" disabled={!yaroqli(f)} onClick={qosh}>Qo'shish</button>
          </div>
        </div>
      )}
      {royxat.length === 0 && <p className="soz-izoh">Tayyor chegirma yo'q.</p>}
      {royxat.map((t) => (
        <Qator key={t.id} t={t} tana={tana} yaroqli={yaroqli} ochiq={ochiq === t.id} onOch={() => setOchiq(ochiq === t.id ? null : t.id)}
          onSaqla={(b, ok) => bajar(() => tayyorChegirmaOzgartir(t.id, b), ok)} />
      ))}
      <p className="soz-izoh">Ro'yxatda yo'q chegirma (masalan, sotuvchining o'z taklifi) rahbar tasdig'iga boradi.</p>
    </SPanel>
  )
}

function Qator({ t, tana, yaroqli, ochiq, onOch, onSaqla }) {
  const [f, setF] = useState({ nomi: t.nomi, turi: t.foiz != null ? 'foiz' : 'summa', qiymat: t.foiz != null ? Number(t.foiz) : t.summa })
  return (
    <div className={`tasdiq soz-royxat-q${t.faol ? '' : ' bajarilgan'}`}>
      <div className="soz-qator">
        <span className="soz-matn"><b>{t.nomi} · {qiymat(t)}</b><small>{t.faol ? 'Sotuvchi zakazda tanlaydi' : 'nofaol — sotuvchiga ko\'rinmaydi'}</small></span>
        <span className="soz-ong">
          {!t.faol && <Yorliq>Nofaol</Yorliq>}
          <button type="button" className="havola" aria-expanded={ochiq} onClick={onOch}>Tahrirlash</button>
        </span>
      </div>
      {ochiq && (
        <div className="soz-tahrir">
          <div className="soz-tugmalar">
            <input value={f.nomi} maxLength={100} aria-label="Nomi" onChange={(e) => setF({ ...f, nomi: e.target.value })} />
            <select className="soz-tanlov" value={f.turi} aria-label="Chegirma turi" onChange={(e) => setF({ ...f, turi: e.target.value, qiymat: '' })}>
              <option value="foiz">%</option><option value="summa">so'm</option>
            </select>
            {f.turi === 'foiz'
              ? <input type="number" min="1" value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />
              : <SummaInput value={f.qiymat} aria-label="Qiymat" onChange={(e) => setF({ ...f, qiymat: e.target.value })} />}
          </div>
          <div className="soz-tugmalar">
            <button type="button" className="kichik" disabled={!yaroqli(f)} onClick={() => onSaqla(tana(f), 'Chegirma saqlandi.')}>Saqlash</button>
            <button type="button" className="ikkinchi kichik" onClick={() => onSaqla({ faol: !t.faol }, t.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')}>
              {t.faol ? 'Nofaol qilish' : 'Faollashtirish'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
