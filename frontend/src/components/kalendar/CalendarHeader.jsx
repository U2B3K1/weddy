import MonthNavigation from './MonthNavigation'
import YearNavigation from './YearNavigation'
import { OYLAR } from './sana'

export default function CalendarHeader({ y, m, fasl, onOy, onYil, onBugun, bugunOyida }) {
  return (
    <header className="kuz-bosh">
      <MonthNavigation oy={m} onOzgar={onOy} />
      <YearNavigation yil={y} onOzgar={onYil} />
      <div className="kuz-tag">
        <span className="kuz-fasl">{fasl}</span>
        <button type="button" className="kuz-bugun-tugma" onClick={onBugun} disabled={bugunOyida}>Bugun</button>
      </div>
      <p className="kuz-yashirin" aria-live="polite">{OYLAR[m]} {y}</p>
    </header>
  )
}
