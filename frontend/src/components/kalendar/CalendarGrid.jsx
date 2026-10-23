import { useEffect, useRef } from 'react'
import { HAFTA, OYLAR, haftalar, iso, isoOch, kunQosh, oyKunlari, oyQosh } from './sana'

const QADAM = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }

// Klaviatura: strelkalar — kun/hafta, PageUp/PageDown — oy. Faqat bitta kun Tab bilan tanlanadi (roving tabindex).
export default function CalendarGrid({ y, m, dan, gacha, bugun, fokus, klaviatura, yon, onTanla, onFokus }) {
  const jadval = useRef(null)
  const oyBoshi = iso(y, m, 1).slice(0, 8)
  const shuOyda = (k) => k && k.startsWith(oyBoshi)
  const tabKun = [fokus, dan, gacha, bugun].find(shuOyda) || iso(y, m, 1)

  useEffect(() => {
    if (klaviatura.current && fokus) jadval.current?.querySelector(`[data-kun="${fokus}"]`)?.focus()
  }, [fokus, klaviatura])

  const tugma = (e, k) => {
    let keyingi = null
    if (e.key in QADAM) keyingi = kunQosh(k, QADAM[e.key])
    else if (e.key === 'PageUp' || e.key === 'PageDown') {
      const s = isoOch(k)
      const o = oyQosh(s, e.key === 'PageUp' ? -1 : 1)
      keyingi = iso(o.y, o.m, Math.min(s.d, oyKunlari(o.y, o.m)))
    }
    if (!keyingi) return
    e.preventDefault()
    klaviatura.current = true
    onFokus(keyingi)
  }

  const yorliq = (k, ustun) => {
    const rol = k === dan && k === gacha ? ', olib ketish va qaytarish' : k === dan ? ', olib ketish' : k === gacha ? ', qaytarish' : ''
    return `${Number(k.slice(8))}-${OYLAR[m].toLowerCase()}, ${HAFTA[ustun][1]}${rol}`
  }

  return (
    <table ref={jadval} className={`kuz-jadval${yon > 0 ? ' kuz-otish-old' : yon < 0 ? ' kuz-otish-orqa' : ''}`}
      onMouseDown={() => { klaviatura.current = false }}>
      <caption className="kuz-yashirin">{OYLAR[m]} {y}</caption>
      <thead>
        <tr>{HAFTA.map(([q, t]) => <th key={q} scope="col" abbr={t}>{q}</th>)}</tr>
      </thead>
      <tbody>
        {haftalar(y, m).map((hafta, i) => (
          <tr key={i}>
            {hafta.map((k, ustun) => {
              if (!k) return <td key={`b${ustun}`} className="kuz-bosh-katak" />
              const otgan = k < bugun
              const chet = k === dan || k === gacha
              const ichida = dan && gacha && k > dan && k < gacha
              const lenta = dan && gacha && dan !== gacha // oraliq lentasi bitta kunlik tanlovda chizilmaydi
              const sinf = [chet && 'kuz-chet', lenta && k === dan && 'kuz-bosh-chet', lenta && k === gacha && 'kuz-oxir-chet',
                ichida && 'kuz-ichida', k === bugun && 'kuz-bugun'].filter(Boolean).join(' ')
              return (
                <td key={k} className={sinf || undefined}>
                  <button type="button" className="kuz-kun" data-kun={k} tabIndex={k === tabKun ? 0 : -1}
                    aria-label={yorliq(k, ustun)} aria-pressed={Boolean(chet || ichida)} aria-disabled={otgan || undefined}
                    aria-current={k === bugun ? 'date' : undefined}
                    onClick={() => { if (!otgan) { onFokus(k); onTanla(k) } }} onKeyDown={(e) => tugma(e, k)}>
                    <span className="kuz-raqam">{Number(k.slice(8))}</span>
                  </button>
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
