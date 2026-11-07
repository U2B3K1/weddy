import { useCallback, useEffect, useState } from 'react'
import SummaInput from '../components/SummaInput'
import Tasdiq from '../components/Tasdiq'
import {
  sanaMatni, som, xatoMatni, yetkazibBeruvchi, yetkazibBeruvchilar, yetkazibOzgartir, yetkazibTolov, yetkazibTolovOchir,
  yetkazibYarat,
} from '../api'

// Libos va aksessuar qayerdan olingani va yetkazib beruvchiga qolgan qarz (faqat rahbar).
// Qarz = undan olingan liboslar tannarxi + aksessuarlar (dona tannarxi × soni) − unga to'langan pul. To'lov kassadan emas va foydaga kirmaydi (libos — investitsiya).
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
          <p className="malumot jadval-bosh">Hali yo'q. Qo'shgach, libos va aksessuar qo'shishda «Qayerdan olingan» va «Hozir to'landi» maydonlari chiqadi.</p>
        )}
        {royxat?.map((y) => (
          <div key={y.id} className="tasdiq-qator yetkazib-qator">
            <button type="button" className="havola qator-matn" aria-expanded={ochiq === y.id} onClick={() => setOchiq(ochiq === y.id ? null : y.id)}>
              <b>{y.nomi}</b>{y.telefon ? ` · ${y.telefon}` : ''}
              <small className="malumot"> · {y.liboslar_soni} ta libos{y.aksessuar_donalar > 0 ? `, ${y.aksessuar_donalar} dona aksessuar` : ''} · olingan {som(y.xarid)} · to'langan {som(y.tolangan)}</small>
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
  const [xato, setXato] = useState('')
  const [ochirSurov, setOchirSurov] = useState(null)
  const yukla = useCallback(() => yetkazibBeruvchi(id).then(setD), [id])
  // Xato jimgina yutilmasin: aks holda «Yuklanmoqda…» abadiy turardi (B-35)
  useEffect(() => { yukla().catch((e) => setXato(xatoMatni(e))) }, [yukla])
  const amal = async (fn, ok) => { if (await bajar(fn, ok)) await yukla() }
  if (!d) return xato ? <p className="xato">{xato}</p> : <p className="malumot">Yuklanmoqda…</p>
  return (
    <div className="stack yetkazib-tafsilot">
      <div className="qator r2-yb-tolov">
        <label>To'lov summasi<SummaInput placeholder={d.qarz > 0 ? `qarz: ${som(d.qarz)}` : ''} value={f.summa}
          onChange={(e) => setF({ ...f, summa: e.target.value })} /></label>
        <label>Izoh (ixtiyoriy)<input maxLength={300} value={f.izoh} onChange={(e) => setF({ ...f, izoh: e.target.value })} /></label>
        <button disabled={!(Number(f.summa) > 0)}
          onClick={() => amal(() => yetkazibTolov(id, { summa: Number(f.summa), izoh: f.izoh }).then(() => setF({ summa: '', izoh: '' })), "To'lov yozildi.")}>
          To'lov qilish
        </button>
      </div>
      <h4>Olingan liboslar ({d.liboslar.length})</h4>
      {d.liboslar.length === 0 && <p className="malumot">Libos qo'shishda yoki libos kartasida «Qayerdan olingan» ni tanlang.</p>}
      {d.liboslar.length > 0 && (
        <div className="jadval-ora">
          <table className="hisobot r2-kichik-jadval">
            <thead><tr><th>Sana</th><th>Libos</th><th>Holat</th><th className="ong">Tannarx</th></tr></thead>
            <tbody>
              {d.liboslar.map((l) => (
                <tr key={l.id}>
                  <td>{sanaMatni(l.sana)}</td><td><b>{l.artikul}</b> {l.nomi}</td><td>{l.holat_nomi}</td>
                  <td className="ong">{l.tannarx == null ? <span className="malumot">kiritilmagan</span> : som(l.tannarx)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {d.aksessuarlar.length > 0 && <h4>Olingan aksessuarlar</h4>}
      {d.aksessuarlar.length > 0 && (
        <div className="jadval-ora">
          <table className="hisobot r2-kichik-jadval">
            <thead><tr><th>Sana</th><th>Aksessuar</th><th className="ong">Soni</th><th className="ong">Narx</th><th className="ong">Jami</th></tr></thead>
            <tbody>
              {d.aksessuarlar.map((a) => (
                <tr key={a.id}>
                  <td>{sanaMatni(a.sana)}</td><td><b>{a.kod}</b> {a.nomi}</td><td className="ong">{a.soni}</td>
                  <td className="ong">{a.narx == null ? <span className="malumot">kiritilmagan</span> : som(a.narx)}</td>
                  <td className="ong">{a.narx == null ? '—' : som(a.jami)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <h4>To'lovlar ({d.tolovlar.length})</h4>
      {d.tolovlar.length > 0 && (
        <div className="jadval-ora">
          <table className="hisobot r2-kichik-jadval">
            <thead><tr><th>Sana</th><th className="ong">Summa</th><th>Izoh</th><th aria-label="Amallar" /></tr></thead>
            <tbody>
              {d.tolovlar.map((t) => (
                <tr key={t.id}>
                  <td>{sanaMatni(t.sana)}</td><td className="ong"><b>{som(t.summa)}</b></td><td>{t.izoh || '—'}</td>
                  <td className="ong"><button className="ikkinchi kichik" onClick={() => setOchirSurov(t)}>O'chirish</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {ochirSurov && (
        <Tasdiq sarlavha="To'lov o'chirilsinmi?" tugma="Ha, o'chirish"
          matn={`${sanaMatni(ochirSurov.sana)}dagi ${som(ochirSurov.summa)} to'lov o'chadi — yetkazib beruvchiga qarz shuncha oshadi. Qaytarib bo'lmaydi.`}
          onYop={() => setOchirSurov(null)}
          onTasdiq={() => { const t = ochirSurov; setOchirSurov(null); amal(() => yetkazibTolovOchir(t.id), "To'lov o'chirildi.") }} />
      )}
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
        <label>Nomi *<input value={f.nomi} maxLength={120} placeholder="masalan: Istanbul Bridal" onChange={(e) => setF({ ...f, nomi: e.target.value })} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon} maxLength={30} onChange={(e) => setF({ ...f, telefon: e.target.value })} /></label>
        <button disabled={!f.nomi.trim()} onClick={async () => { if (await onYuborish(f)) setF({ nomi: '', telefon: '' }) }}>Qo'shish</button>
      </div>
    </details>
  )
}
