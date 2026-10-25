import MonthNavigation from './MonthNavigation'
import YearNavigation from './YearNavigation'
import { OYLAR } from './sana'

export default function CalendarHeader({ y, m, onOy, onYil }) {
  return (
    <header className="kuz-bosh">
      <MonthNavigation oy={m} onOzgar={onOy} />
      <YearNavigation yil={y} onOzgar={onYil} />
      <p className="kuz-yashirin" aria-live="polite">{OYLAR[m]} {y}</p>
    </header>
  )
}
