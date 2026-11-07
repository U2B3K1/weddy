import NavIkona from './NavIkona'
import { OYLAR } from './kalendar/sana'

const ikki = (n) => String(n).padStart(2, '0')
// Joriy oy mahalliy vaqtda («YYYY-MM»). toISOString() UTC beradi: oyning 1-kuni 00:00–05:00 orasida o'tgan oy chiqardi.
const joriyOy = () => { const d = new Date(); return `${d.getFullYear()}-${ikki(d.getMonth() + 1)}` }
// «2026-11» → «Noyabr 2026» (brauzer tilidagi «Ноябрь 2026» o'rniga)
const oyNomi = (oy) => { const [y, m] = String(oy).split('-').map(Number); return `${OYLAR[m - 1]} ${y}` }
const siljit = (oy, n) => { const [y, m] = oy.split('-').map(Number); const d = new Date(y, m - 1 + n, 1); return `${d.getFullYear()}-${ikki(d.getMonth() + 1)}` }

// Oy tanlash: «‹ Noyabr 2026 ›». `type="month"` o'rniga — hamma brauzerda o'zbekcha, telefonda ham bir xil.
// Kelajak oylariga o'tilmaydi (`max`, standart — joriy oy). Yordamchilar: OyTanlash.joriy(), OyTanlash.nomi('2026-11').
export default function OyTanlash({ value, onChange, max = joriyOy(), yorliq = 'Oy' }) {
  const keyingi = siljit(value, 1)
  return (
    <div className="oy-tanlash" role="group" aria-label={yorliq}>
      <button type="button" className="ikkinchi kichik" aria-label="Oldingi oy" onClick={() => onChange(siljit(value, -1))}>
        <NavIkona nom="chap" className="tugma-ikon" />
      </button>
      <output aria-live="polite">{oyNomi(value)}</output>
      <button type="button" className="ikkinchi kichik" aria-label="Keyingi oy" disabled={Boolean(max) && keyingi > max}
        onClick={() => onChange(keyingi)}>
        <NavIkona nom="ong" className="tugma-ikon" />
      </button>
    </div>
  )
}
OyTanlash.joriy = joriyOy
OyTanlash.nomi = oyNomi
