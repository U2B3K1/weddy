import { useEffect, useRef, useState } from 'react'
import { som } from '../api'
import { OYLAR, isoOch } from './kalendar/sana'

// Kunlik tushum chizig'i: tilla chiziq va ostida yumshoq nur — tanlangan davr; uzuq kulrang chiziq — undan oldingi
// xuddi shuncha kun (taqqoslash). Nuqta ustida (yoki ←/→ bilan) — o'sha kun summasi va o'tgan davrdagi juft kuni.
const ENG_PAST = 220  // grafik balandligi kamida; karta cho'zilsa grafik ham to'ldiradi
const CHAP = 52   // y o'qi yozuvlari
const PAST = 26   // x o'qi yozuvlari
const TEPA = 12

const qisqaSumma = (n) => {
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('uz-UZ', { maximumFractionDigits: 1 })} mln`
  if (n >= 1e3) return `${Math.round(n / 1e3)} ming`
  return String(n)
}
const qisqaSana = (iso) => { const s = isoOch(iso); return `${s.d} ${OYLAR[s.m].slice(0, 3).toLowerCase()}` }

// Y o'qi uchun «yumaloq» qadam: 1, 2, 2.5, 5 × 10^n
function qadam(maks) {
  const xom = maks / 4
  const daraja = 10 ** Math.floor(Math.log10(xom || 1))
  return [1, 2, 2.5, 5, 10].map((k) => k * daraja).find((q) => q >= xom) || daraja * 10
}

export default function TushumChizigi({ kunlar, rang = '#B9833A' }) {
  const ref = useRef(null)
  const [en, setEn] = useState(600)
  const [BALAND, setBaland] = useState(ENG_PAST)
  const [tanlangan, setTanlangan] = useState(null)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined
    const k = new ResizeObserver(([e]) => {
      setEn(Math.max(280, Math.round(e.contentRect.width)))
      setBaland(Math.max(ENG_PAST, Math.round(e.contentRect.height)))
    })
    k.observe(el)
    return () => k.disconnect()
  }, [])

  const n = kunlar.length
  const maks = Math.max(1, ...kunlar.map((k) => Math.max(k.summa, k.oldingi)))
  const q = qadam(maks)
  const yuqori = Math.ceil(maks / q) * q
  const w = en - CHAP - 8
  const h = BALAND - TEPA - PAST
  const x = (i) => CHAP + (n > 1 ? (i * w) / (n - 1) : w / 2)
  const y = (v) => TEPA + h - (Math.max(0, v) / yuqori) * h
  const yol = (kalit) => kunlar.map((k, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(k[kalit]).toFixed(1)}`).join(' ')
  const chiziq = yol('summa')
  const maydon = `${chiziq} L${x(n - 1).toFixed(1)},${TEPA + h} L${x(0).toFixed(1)},${TEPA + h} Z`
  const yBelgilar = Array.from({ length: Math.round(yuqori / q) + 1 }, (_, i) => i * q)
  const xBelgilar = n <= 1 ? [0] : [0, Math.round((n - 1) / 4), Math.round((n - 1) / 2), Math.round((3 * (n - 1)) / 4), n - 1]

  const tanla = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const i = Math.round(((e.clientX - r.left - CHAP) / w) * (n - 1))
    setTanlangan(Math.min(n - 1, Math.max(0, i)))
  }
  const tugma = (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    setTanlangan((t) => Math.min(n - 1, Math.max(0, (t ?? n - 1) + (e.key === 'ArrowRight' ? 1 : -1))))
  }
  const k = tanlangan != null ? kunlar[tanlangan] : null
  const jami = kunlar.reduce((s, d) => s + d.summa, 0)
  const gradId = 'tushum-nur'

  return (
    <div className="tushum-chizigi" ref={ref}>
      <svg width={en} height={BALAND} role="img" tabIndex={0} onPointerMove={tanla} onPointerLeave={() => setTanlangan(null)}
        onKeyDown={tugma} onBlur={() => setTanlangan(null)}
        aria-label={`Kunlik tushum, ${qisqaSana(kunlar[0].sana)} – ${qisqaSana(kunlar[n - 1].sana)}: jami ${som(jami)}. Kunlarni ko'rish uchun ← va → tugmalari.`}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={rang} stopOpacity=".32" />
            <stop offset="100%" stopColor={rang} stopOpacity="0" />
          </linearGradient>
        </defs>
        {yBelgilar.map((v) => (
          <g key={v}>
            <line x1={CHAP} x2={CHAP + w} y1={y(v)} y2={y(v)} className="tc-tor" />
            <text x={CHAP - 8} y={y(v) + 4} textAnchor="end" className="tc-yozuv">{v ? qisqaSumma(v) : '0'}</text>
          </g>
        ))}
        {xBelgilar.map((i) => (
          <text key={i} x={x(i)} y={BALAND - 6} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} className="tc-yozuv">
            {qisqaSana(kunlar[i].sana)}
          </text>
        ))}
        <path d={yol('oldingi')} className="tc-oldingi" />
        <path d={maydon} fill={`url(#${gradId})`} />
        <path d={chiziq} fill="none" stroke={rang} strokeWidth="2.25" strokeLinejoin="round" strokeLinecap="round" />
        {k && (
          <g>
            <line x1={x(tanlangan)} x2={x(tanlangan)} y1={TEPA} y2={TEPA + h} className="tc-chiziq" />
            <circle cx={x(tanlangan)} cy={y(k.oldingi)} r="3.5" className="tc-nuqta-oldingi" />
            <circle cx={x(tanlangan)} cy={y(k.summa)} r="5" fill={rang} className="tc-nuqta" />
          </g>
        )}
      </svg>
      {k && (
        <div className="tc-izoh" role="status" style={{ left: Math.min(en - 190, Math.max(0, x(tanlangan) - 95)) }}>
          <small>{qisqaSana(k.sana)}</small>
          <b>{som(k.summa)}</b>
          <span>oldingi davr: {som(k.oldingi)}</span>
        </div>
      )}
    </div>
  )
}
