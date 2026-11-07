import { useState } from 'react'

// Bosh sahifa kartalari va Zakazlar → «Bugun» ustuni uchun umumiy qismlar: zakaz qatorlari (avatar) va karta belgilari.

const bosHarf = (ism) => (ism || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0]).join('').toUpperCase()

// Karta belgilari — ixcham stroke SVG (dashboard kartalari bilan bir xil uslub)
const BELGI = {
  diqqat: (<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>),
  chiqdi: (<><path d="M14 4h6v6" /><path d="M20 4 10 14" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>),
  qaytdi: (<><path d="M9 14 4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" /></>),
  soat: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  telefon: (<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.8 2Z" />),
  hamyon: (<><path d="M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3" /><path d="M21 11h-5a2 2 0 0 0 0 4h5Z" /></>),
  kassa: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></>),
  bajarildi: (<><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></>),
  kun: (<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>),
  libos: (<><path d="M9 3c1 1.5 2 2 3 2s2-.5 3-2M9 3 8 6l2 6h4l2-6-1-3" /><path d="M10 12c-1 4-3 7-6 9 3 1 5 1.5 8 1.5s5-.5 8-1.5c-3-2-5-5-6-9" /></>),
  mijoz: (<><circle cx="9" cy="8" r="3.5" /><path d="M2 21a7 7 0 0 1 14 0" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 21a7 7 0 0 0-4-6.3" /></>),
  tamir: (<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9Z" />),
  filtr: (<path d="M3 4h18l-7 8.5V19l-4 2v-8.5Z" />),
  tushum: (<><path d="M22 7l-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>),
  terminal: (<><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20M6 15h4" /></>),
  son: (<path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18" />),
  foiz: (<><path d="M19 5 5 19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></>),
}
export const Belgi = ({ nom, className = 'dash-karta-ikon' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {BELGI[nom]}
  </svg>
)

// Karta ichidagi zakaz qatorlari (maketdagi «Faol bronlar» kabi): avatar, mijoz, zakaz va libos, o'ngda summa/holat.
// Ko'pi bilan `kop` ta, qolgani «Yana N ta» bilan ochiladi; qator bosilsa zakaz kartasi.
export function Qatorlar({ royxat, onZakaz, ong, kop = 4 }) {
  const [hammasi, setHammasi] = useState(false)
  const korinadi = hammasi ? royxat : royxat.slice(0, kop)
  return (
    <>
      <ul className="dash-bron-royxat">
        {korinadi.map((z) => (
          <li key={z.id}>
            <button type="button" onClick={() => onZakaz(z.id)}>
              <span className="dash-avatar" aria-hidden="true">{bosHarf(z.mijoz)}</span>
              <span className="dash-bron-matn">
                <b>{z.mijoz}</b>
                <small>#{z.raqam} · {(z.liboslar || []).join(', ') || '—'}</small>
              </span>
              <span className="dash-bron-ong">{ong(z)}</span>
            </button>
          </li>
        ))}
      </ul>
      {royxat.length > kop && (
        <button type="button" className="havola dash-karta-oxir" onClick={() => setHammasi(!hammasi)}>
          {hammasi ? 'Yig\'ish' : `Yana ${royxat.length - kop} ta`}
        </button>
      )}
    </>
  )
}
