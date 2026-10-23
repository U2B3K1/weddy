export default function YearNavigation({ yil, onOzgar }) {
  return (
    <div className="kuz-yil-nav">
      <button type="button" className="kuz-strelka kuz-strelka-kichik" onClick={() => onOzgar(-1)} aria-label="Oldingi yil">‹</button>
      <span className="kuz-yil">{yil}</span>
      <button type="button" className="kuz-strelka kuz-strelka-kichik" onClick={() => onOzgar(1)} aria-label="Keyingi yil">›</button>
    </div>
  )
}
