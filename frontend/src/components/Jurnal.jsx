import { useEffect, useState } from 'react'
import { amallarJurnali, telegramXabarlari, xatoMatni } from '../api'

// Server vaqti UTC da keladi — mahalliy vaqtda «25.10.2026 14:30»
const vaqtMatni = (s) => {
  const t = new Date(s), n = (x) => String(x).padStart(2, '0')
  return `${n(t.getDate())}.${n(t.getMonth() + 1)}.${t.getFullYear()} ${n(t.getHours())}:${n(t.getMinutes())}`
}
// «xarajat_tuzatildi» → «Xarajat tuzatildi»
const harakatNomi = (h) => { const m = h.replaceAll('_', ' '); return m.charAt(0).toUpperCase() + m.slice(1) }

// Ilova B: rahbar kim nimani o'zgartirganini ko'radi (oxirgi 200 ta). Telegram xabarlari — bot ishlayaptimi,
// kimga yetib bormagan (oxirgi 100 ta). Ikkalasi ham faqat o'qish uchun.
export default function Jurnal() {
  const [amallar, setAmallar] = useState(null)
  const [xabarlar, setXabarlar] = useState(null)
  const [q, setQ] = useState('')
  const [xato, setXato] = useState('')
  useEffect(() => {
    amallarJurnali().then(setAmallar).catch((e) => setXato(xatoMatni(e)))
    telegramXabarlari().then(setXabarlar).catch(() => setXabarlar([]))
  }, [])

  const s = q.trim().toLowerCase()
  const korinadi = (amallar || []).filter((j) => !s || [j.harakat, j.obyekt, j.eski, j.yangi, j.xodim]
    .some((v) => String(v ?? '').toLowerCase().includes(s)))
  const yetmagan = (xabarlar || []).filter((x) => x.holat !== 'yuborildi')

  return (
    <>
      <section className="blok stack">
        <h3>Amallar jurnali</h3>
        {xato && <p className="xato">{xato}</p>}
        <input placeholder="Qidirish: xodim, amal yoki obyekt" aria-label="Jurnaldan qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
        {amallar === null && !xato && <p className="malumot">Yuklanmoqda…</p>}
        {amallar && korinadi.length === 0 && <p className="malumot">Yozuv topilmadi.</p>}
        {korinadi.length > 0 && (
          <table className="jadval"><tbody>
            {korinadi.map((j, i) => (
              <tr key={i} className="kichik-qator">
                <td>{vaqtMatni(j.vaqt)}<br />{j.xodim || '—'}</td>
                <td><b>{harakatNomi(j.harakat)}</b> · {j.obyekt}
                  {(j.eski || j.yangi) && <><br />{j.eski || '—'} → {j.yangi || '—'}</>}
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </section>
      <section className="blok stack">
        <h3>Telegram xabarlari{yetmagan.length > 0 ? ` · yetib bormagan: ${yetmagan.length}` : ''}</h3>
        {xabarlar === null && <p className="malumot">Yuklanmoqda…</p>}
        {xabarlar && xabarlar.length === 0 && <p className="malumot">Hali xabar yuborilmagan.</p>}
        {xabarlar && xabarlar.length > 0 && (
          <table className="jadval"><tbody>
            {xabarlar.map((x, i) => (
              <tr key={i} className="kichik-qator">
                <td>{vaqtMatni(x.vaqt)}<br />{x.xodim}</td>
                <td>{x.matn.length > 120 ? `${x.matn.slice(0, 120)}…` : x.matn}</td>
                <td className={x.holat === 'yuborildi' ? '' : 'qizil'}>{x.holat_nomi}{x.xato ? `: ${x.xato}` : ''}</td>
              </tr>
            ))}
          </tbody></table>
        )}
      </section>
    </>
  )
}
