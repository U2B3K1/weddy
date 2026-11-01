import { HAFTA, OYLAR, isoOch, ustun } from './kalendar/sana'

// Zakaz varaqasi (to'y taklifnomasidek fil suyagi qog'oz) uchun umumiy bo'laklar: «Yangi zakaz» va zakaz kartasi.
// Stillar: ichki.css → «Zakaz varaqasi».

// Olib ketish va qaytarish kunlari (ikkalasi ham hisobga olinadi): 11 → 12 = 2 kun
const kunlar = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000) + 1
// «11», «dekabr», «payshanba»
const sanaQismlari = (s) => { const { y, m, d } = isoOch(s); return { kun: d, oy: OYLAR[m].toLowerCase(), hafta: HAFTA[ustun(y, m, d)][1].toLowerCase() } }

export function VaraqSana({ dan, gacha }) {
  if (!dan || !gacha || gacha < dan) {
    return <p className="varaq-izoh">Olib ketish va qaytarish kunini kalendarda belgilang.</p>
  }
  const a = sanaQismlari(dan), b = sanaQismlari(gacha)
  return (
    <div className="varaq-sana">
      <div><small>olib ketish</small><b>{a.kun}</b><span>{a.oy}</span><em>{a.hafta}</em></div>
      <i>{kunlar(dan, gacha)} kun</i>
      <div><small>qaytarish</small><b>{b.kun}</b><span>{b.oy}</span><em>{b.hafta}</em></div>
    </div>
  )
}

export const Bezak = () => (
  <svg className="varaq-bezak" viewBox="0 0 120 12" aria-hidden="true">
    <path d="M0 6h48M72 6h48" /><path d="M60 1.5 64.5 6 60 10.5 55.5 6Z" /><circle cx="51" cy="6" r="1.2" /><circle cx="69" cy="6" r="1.2" />
  </svg>
)

// Surg'uch muhr «№N». `bosildi` — shu zahoti bosilgan (animatsiya bilan), aks holda allaqachon turibdi
export const Muhr = ({ raqam, bosildi = true, className = '' }) => (
  <div className={`muhr ${bosildi ? 'muhr-bosildi' : ''} ${className}`} aria-hidden="true"><span>№</span>{raqam}</div>
)

// Jadval qatori uchun ixcham sana: «12 – 14 dekabr», oylar har xil bo'lsa «30 noyabr – 2 dekabr», bir kunlik — «27 oktabr»
export function IjaraSana({ dan, gacha }) {
  const a = sanaQismlari(dan), b = sanaQismlari(gacha)
  return (
    <span className="ijara-sana">
      {dan !== gacha && <><b>{a.kun}</b>{a.oy !== b.oy && <> {a.oy}</>}<i>–</i></>}<b>{b.kun}</b> {b.oy}
    </span>
  )
}
