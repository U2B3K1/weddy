import { useCallback, useEffect, useState } from 'react'
import SummaInput from '../components/SummaInput'
import {
  sanaMatni, som, xatoMatni, yetkazibBeruvchi, yetkazibBeruvchilar, yetkazibOzgartir, yetkazibTolov, yetkazibTolovOchir,
  yetkazibYarat,
} from '../api'

// Libos qayerdan olingani va yetkazib beruvchiga qolgan qarz (faqat rahbar).
// Qarz = undan olingan liboslar tannarxi − unga to'langan pul. To'lov kassadan emas va foydaga kirmaydi (libos — investitsiya).
export default function YetkazibBeruvchilar() {
  const [royxat, setRoyxat] = useState(null)
  const [ochiq, setOchiq] = useState(null)  // tanlangan yetkazib beruvchi id
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => yetkazibBeruvchilar().then(setRoyxat), [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const jamiQarz = (royxat || []).reduce((s, y) => s + Math.max(y.qarz, 0), 0)

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      <div className="stat-qator">
        <div className="stat"><span>Yetkazib beruvchilar</span><b>{royxat?.length ?? '—'}</b></div>
        <div className="stat"><span>Jami qarz</span><b className={jamiQarz > 0 ? 'qizil' : ''}>{som(jamiQarz)}</b></div>
      </div>
      <YangiForma onYuborish={(b) => bajar(() => yetkazibYarat(b), "Yetkazib beruvchi qo'shildi.")} />
      <section className="blok jadval-panel">
        <div className="jadval-asboblar"><h3 className="panel-nom">Yetkazib beruvchilar</h3></div>
        {royxat && royxat.length === 0 && (
          <p className="malumot jadval-bosh">Hali yo'q. Qo'shgach, libos qo'shishda «Qayerdan olingan» va «Hozir to'landi» maydonlari chiqadi.</p>
        )}
        {royxat?.map((y) => (
          <div key={y.id} className="tasdiq-qator yetkazib-qator">
            <button type="button" className="havola qator-matn" aria-expanded={ochiq === y.id} onClick={() => setOchiq(ochiq === y.id ? null : y.id)}>
              <b>{y.nomi}</b>{y.telefon ? ` · ${y.telefon}` : ''}
              <small className="malumot"> · {y.liboslar_soni} ta libos · olingan {som(y.xarid)} · to'langan {som(y.tolangan)}</small>
            </button>
            <b className={y.qarz > 0 ? 'qizil' : ''}>{y.qarz > 0 ? `qarz ${som(y.qarz)}` : y.qarz < 0 ? `oldindan ${som(-y.qarz)}` : "qarz yo'q"}</b>
            {ochiq === y.id && <Tafsilot id={y.id} bajar={bajar} />}
          </div>
        ))}
      </section>
    </div>
  )
}

function Tafsilot({ id, bajar }) {
  const [d, setD] = useState(null)
  const [f, setF] = useState({ summa: '', izoh: '' })
  const yukla = useCallback(() => yetkazibBeruvchi(id).then(setD), [id])
  useEffect(() => { yukla().catch(() => {}) }, [yukla])
  const amal = async (fn, ok) => { if (await bajar(fn, ok)) await yukla() }
  if (!d) return <p className="malumot">Yuklanmoqda…</p>
  return (
    <div className="stack yetkazib-tafsilot">
      <div className="qator">
        <SummaInput placeholder={d.qarz > 0 ? `qarz: ${som(d.qarz)}` : 'Summa'} aria-label="To'lov summasi" value={f.summa}
          onChange={(e) => setF({ ...f, summa: e.target.value })} />
        <input placeholder="Izoh (ixtiyoriy)" aria-label="To'lov izohi" maxLength={300} value={f.izoh} onChange={(e) => setF({ ...f, izoh: e.target.value })} />
        <button disabled={!(Number(f.summa) > 0)}
          onClick={() => amal(() => yetkazibTolov(id, { summa: Number(f.summa), izoh: f.izoh }).then(() => setF({ summa: '', izoh: '' })), "To'lov yozildi.")}>
          To'lov qilish
        </button>
      </div>
      <h4>Olingan liboslar ({d.liboslar.length})</h4>
      {d.liboslar.length === 0 && <p className="malumot">Libos qo'shishda yoki libos kartasida «Qayerdan olingan» ni tanlang.</p>}
      {d.liboslar.map((l) => (
        <p key={l.id} className="qator-matn">{sanaMatni(l.sana)} · <b>{l.artikul}</b> {l.nomi} · {l.tannarx == null ? 'tannarx kiritilmagan' : som(l.tannarx)}
          {l.holat !== 'bosh' && <span className="malumot"> · {l.holat_nomi}</span>}</p>
      ))}
      <h4>To'lovlar ({d.tolovlar.length})</h4>
      {d.tolovlar.map((t) => (
        <div key={t.id} className="qator yetkazib-tolov">
          <span className="qator-matn">{sanaMatni(t.sana)} · <b>{som(t.summa)}</b>{t.izoh ? ` · ${t.izoh}` : ''}</span>
          <button className="ikkinchi kichik" onClick={() => amal(() => yetkazibTolovOchir(t.id), "To'lov o'chirildi.")}>O'chirish</button>
        </div>
      ))}
      <Tahrir d={d} onSaqla={(b) => amal(() => yetkazibOzgartir(id, b), 'Saqlandi.')} />
    </div>
  )
}

function Tahrir({ d, onSaqla }) {
  const [f, setF] = useState({ nomi: d.nomi, telefon: d.telefon, izoh: d.izoh })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <details className="amal">
      <summary>Tahrirlash</summary>
      <div className="stack">
        <label>Nomi<input value={f.nomi} maxLength={120} onChange={set('nomi')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon} maxLength={30} onChange={set('telefon')} /></label>
        <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
        <button className="ikkinchi" disabled={!f.nomi.trim()} onClick={() => onSaqla(f)}>Saqlash</button>
      </div>
    </details>
  )
}

function YangiForma({ onYuborish }) {
  const [f, setF] = useState({ nomi: '', telefon: '' })
  return (
    <details className="blok amal">
      <summary>Yetkazib beruvchi qo'shish</summary>
      <div className="stack">
        <label>Nomi<input value={f.nomi} maxLength={120} placeholder="masalan: Istanbul Bridal" onChange={(e) => setF({ ...f, nomi: e.target.value })} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon} maxLength={30} onChange={(e) => setF({ ...f, telefon: e.target.value })} /></label>
        <button disabled={!f.nomi.trim()} onClick={async () => { if (await onYuborish(f)) setF({ nomi: '', telefon: '' }) }}>Qo'shish</button>
      </div>
    </details>
  )
}
