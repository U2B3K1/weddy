// Halqa diagramma: qismlar bitta doirada, markazda jami. Ranglar yorliqlar bilan birga beriladi (legenda yonida) —
// faqat rangga tayanmaslik uchun legendada son va foiz ham yoziladi.
export default function Halqa({ qismlar, jami, izoh = 'jami', olcham = 156, qalinlik = 18 }) {
  const r = (olcham - qalinlik) / 2
  const C = 2 * Math.PI * r
  const yigindi = qismlar.reduce((s, q) => s + q.son, 0)
  let boshi = 0
  return (
    <svg className="halqa" width={olcham} height={olcham} viewBox={`0 0 ${olcham} ${olcham}`} role="img"
      aria-label={`${jami} ${izoh}: ${qismlar.map((q) => `${q.nom} ${q.son}`).join(', ')}`}>
      <circle cx={olcham / 2} cy={olcham / 2} r={r} fill="none" className="halqa-iz" strokeWidth={qalinlik} />
      {yigindi > 0 && qismlar.filter((q) => q.son > 0).map((q) => {
        const uzun = (q.son / yigindi) * C
        // qismlar orasida ingichka tirqish — qo'shni ranglar bir-biriga qo'shilib ketmasin
        const el = (
          <circle key={q.nom} cx={olcham / 2} cy={olcham / 2} r={r} fill="none" stroke={q.rang} strokeWidth={qalinlik}
            strokeDasharray={`${Math.max(0, uzun - 2)} ${C}`} strokeDashoffset={-boshi}
            transform={`rotate(-90 ${olcham / 2} ${olcham / 2})`} />
        )
        boshi += uzun
        return el
      })}
      <text x="50%" y="48%" textAnchor="middle" className="halqa-son">{jami}</text>
      <text x="50%" y="63%" textAnchor="middle" className="halqa-izoh">{izoh}</text>
    </svg>
  )
}
