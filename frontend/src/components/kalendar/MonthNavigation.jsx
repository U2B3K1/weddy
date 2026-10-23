import { OYLAR } from './sana'

export default function MonthNavigation({ oy, onOzgar }) {
  return (
    <div className="kuz-oy-nav">
      <button type="button" className="kuz-strelka" onClick={() => onOzgar(-1)} aria-label="Oldingi oy">‹</button>
      <div className="kuz-sarlavha">
        <h3 className="kuz-oy">{OYLAR[oy]}</h3>
      </div>
      <button type="button" className="kuz-strelka" onClick={() => onOzgar(1)} aria-label="Keyingi oy">›</button>
    </div>
  )
}
