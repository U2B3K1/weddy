// Yarim doira o'lchagich — bitta ulush (masalan, bandlik %). Bitta qiymat: legenda kerak emas, raqam markazda yoziladi.
// Rang qorong'i fon uchun validatsiyadan o'tgan (#B9833A); yo'lak — yuza tusi.
const R = 70
const C = Math.PI * R  // yarim aylana uzunligi

export default function Olchagich({ foiz, izoh, rang = '#B9833A' }) {
  const f = Math.max(0, Math.min(100, Number(foiz) || 0))
  return (
    <figure className="olchagich" role="img" aria-label={`${f}% ${izoh || ''}`}>
      <svg viewBox="0 0 180 104" aria-hidden="true">
        <path d="M20 94 A70 70 0 0 1 160 94" fill="none" stroke="var(--yuza-3)" strokeWidth="14" strokeLinecap="round" />
        {f > 0 && (
          <path d="M20 94 A70 70 0 0 1 160 94" fill="none" stroke={rang} strokeWidth="14" strokeLinecap="round"
            strokeDasharray={`${(f / 100) * C} ${C}`} />
        )}
      </svg>
      <figcaption><b>{f}%</b>{izoh && <span>{izoh}</span>}</figcaption>
    </figure>
  )
}
