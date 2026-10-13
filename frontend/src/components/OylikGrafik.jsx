import { useState } from 'react'
import { som } from '../api'

// 12 oylik ustunli grafik (6.5). Bitta o'lchov — bitta grafik: tushum va sof foyda alohida chiziladi (ikki o'qli grafik emas).
// Rang validatsiyadan o'tgan (#9a4c95, och fon uchun); matn doim matn rangida, ustun rangida emas.
const RANG = '#9a4c95'
const OYLAR = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
const W = 440
const H = 150
const CHAP = 4
const TEPA = 18
const PAST = 22

const qisqa = (n) => {
  const a = Math.abs(n)
  if (a >= 1e9) return `${(n / 1e9).toFixed(1)} mlrd`
  if (a >= 1e6) return `${(n / 1e6).toFixed(a >= 1e7 ? 0 : 1)} mln`
  if (a >= 1e3) return `${Math.round(n / 1e3)} ming`
  return String(n)
}

export default function OylikGrafik({ sarlavha, qator, kalit }) {
  const [hover, setHover] = useState(null)
  const qiymatlar = qator.map((q) => q[kalit])
  const maks = Math.max(0, ...qiymatlar)
  const min = Math.min(0, ...qiymatlar)
  const oraliq = maks - min || 1
  // manfiy ustun qiymati ustun ostiga yoziladi: oy nomlari bilan ustma-ust tushmasligi uchun joy qoldiriladi
  const plotH = H - TEPA - PAST - (min < 0 ? 12 : 0)
  const y = (v) => TEPA + ((maks - v) / oraliq) * plotH
  const nol = y(0)
  const qadam = (W - CHAP * 2) / qator.length
  const eni = Math.min(24, qadam - 2) // ustun 24px dan qalin emas; qo'shni ustunlar orasida kamida 2px
  const engKatta = qiymatlar.indexOf(Math.max(...qiymatlar))
  const oxirgi = qator.length - 1
  const hammasiNol = qiymatlar.every((v) => v === 0)

  // Ustunning ma'lumot uchi 4px yumaloq, asos chizig'i tomoni to'g'ri
  const ustun = (x, v) => {
    const r = Math.min(4, Math.abs(y(v) - nol))
    const tepa = y(v)
    if (v >= 0) {
      return `M${x},${nol} V${tepa + r} Q${x},${tepa} ${x + r},${tepa} H${x + eni - r} Q${x + eni},${tepa} ${x + eni},${tepa + r} V${nol} Z`
    }
    return `M${x},${nol} V${tepa - r} Q${x},${tepa} ${x + r},${tepa} H${x + eni - r} Q${x + eni},${tepa} ${x + eni},${tepa - r} V${nol} Z`
  }

  return (
    <figure className="grafik">
      <figcaption>{sarlavha}{hover !== null && <span> · {qator[hover].oy}: <b>{som(qator[hover][kalit])}</b></span>}</figcaption>
      {hammasiNol ? <p className="malumot">Bu davrda ma'lumot yo'q.</p> : (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${sarlavha}, oxirgi 12 oy`} onMouseLeave={() => setHover(null)}>
          <line x1={CHAP} x2={W - CHAP} y1={nol} y2={nol} className="grafik-oq" />
          {qator.map((q, i) => {
            const x = CHAP + i * qadam + (qadam - eni) / 2
            const v = q[kalit]
            const oy = OYLAR[Number(q.oy.slice(5)) - 1]
            return (
              <g key={q.oy}>
                {v !== 0 && <path d={ustun(x, v)} fill={RANG} opacity={hover === null || hover === i ? 1 : 0.45} />}
                {/* faqat eng katta va oxirgi oy yoziladi; qolgani — ustiga olib borganda */}
                {(i === engKatta || i === oxirgi) && v !== 0 && (
                  <text x={x + eni / 2} y={v >= 0 ? y(v) - 4 : y(v) + 11} className="grafik-qiymat">{qisqa(v)}</text>
                )}
                <text x={x + eni / 2} y={H - 6} className="grafik-oy">{oy}</text>
                {/* bosish/ko'rsatish maydoni ustundan kattaroq */}
                <rect x={CHAP + i * qadam} y={0} width={qadam} height={H} fill="transparent"
                  onMouseEnter={() => setHover(i)} onClick={() => setHover(i)}>
                  <title>{`${q.oy}: ${som(v)}`}</title>
                </rect>
              </g>
            )
          })}
        </svg>
      )}
    </figure>
  )
}
