import { useCallback, useEffect, useState } from 'react'
import { som, tamirBer, tamirTugat, tamirlar, xatoMatni } from '../api'

// FT-3.10: ta'mir va moslash jurnali — nima qilindi, kim qildi, narxi, libos necha kun ta'mirda turdi.
export default function TamirBlok({ libosId, rahbar, onOzgardi }) {
  const [royxat, setRoyxat] = useState([])
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => tamirlar(libosId).then(setRoyxat), [libosId])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      await fn()
      setF({})
      setXabar({ turi: 'ok', matn: ok })
      await yukla()
      onOzgardi?.()
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
    }
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const ochiq = royxat.find((t) => t.ochiq)

  return (
    <details className="amal tamir">
      <summary>Ta'mir jurnali ({royxat.length}){ochiq ? ' · hozir ta\'mirda' : ''}</summary>
      <div className="stack">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

        {ochiq ? (
          <div className="stack">
            <p className="ogohlantirish">
              Ta'mirda: {ochiq.ish_turi}{ochiq.kim ? ` (${ochiq.kim})` : ''} · {ochiq.boshlangan} dan, {ochiq.kunlar} kun
            </p>
            <label>Ta'mir narxi<input type="number" min="0" value={f.narx || ''} onChange={set('narx')} /></label>
            {!rahbar && <p className="malumot">Narx kassadan chiqim bo'ladi va rahbar tasdig'ini kutadi (ochiq smena kerak).</p>}
            <button onClick={() => bajar(() => tamirTugat(ochiq.id, { narx: Number(f.narx || 0) }), "Ta'mir tugatildi, libos bo'sh.")}>
              Ta'mirni tugatish
            </button>
          </div>
        ) : (
          <div className="stack">
            <label>Nima qilinadi<input placeholder="Masalan: etagini qisqartirish" value={f.ish_turi || ''} onChange={set('ish_turi')} /></label>
            <label>Kim qiladi (usta)<input value={f.kim || ''} onChange={set('kim')} /></label>
            <button className="ikkinchi" disabled={!f.ish_turi?.trim()}
              onClick={() => bajar(() => tamirBer(libosId, { ish_turi: f.ish_turi, kim: f.kim || '' }), "Libos ta'mirga berildi.")}>
              Ta'mirga berish
            </button>
          </div>
        )}

        {royxat.filter((t) => !t.ochiq).map((t) => (
          <p key={t.id} className="qator-matn">
            {t.boshlangan} – {t.tugagan} · {t.kunlar} kun · {t.ish_turi}{t.kim ? ` (${t.kim})` : ''} · {som(t.narx)}
          </p>
        ))}
      </div>
    </details>
  )
}
