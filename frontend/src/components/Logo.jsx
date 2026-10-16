import { BELGI_D } from '../pages/ezazBelgi'

// Bosh sahifadagi (Reklama) logo: malika belgisi, atrofida nuqtali halqa, yonida LIBOSA yozuvi.
export default function Logo({ className = '' }) {
  return (
    <span className={`logo ${className}`} role="img" aria-label="Libosa">
      <svg viewBox="-60 -40 640 640" aria-hidden="true">
        <circle cx="260" cy="280" r="300" fill="none" stroke="currentColor" strokeWidth="10" strokeDasharray="20 52" />
        <path d={BELGI_D} fill="currentColor" />
      </svg>
      <span aria-hidden="true">LIBOSA</span>
    </span>
  )
}
