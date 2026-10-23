import { sanaMatni } from '../../api'
import { kunlarSoni } from './sana'

// Tanlangan oraliq: ikki kartochka. Navbatdagi tanlanadigan sana ajratib ko'rsatiladi.
// Kartochka bosilsa — o'sha sanadan qayta tanlash (olib ketish → ikkalasi tozalanadi).
export default function TanlovPaneli({ dan, gacha, onTozala }) {
  const navbat = !dan ? 'dan' : !gacha ? 'gacha' : null
  const kun = dan && gacha ? kunlarSoni(dan, gacha) + 1 : null
  const karta = (kalit, nomi, qiymat, izoh) => (
    <button type="button" className={`kuz-karta${navbat === kalit ? ' kuz-karta-navbat' : ''}`}
      onClick={() => onTozala(kalit)} disabled={!qiymat}
      aria-label={qiymat ? `${nomi}: ${sanaMatni(qiymat)}. Qayta tanlash` : `${nomi}: tanlanmagan`}>
      <span className="kuz-karta-nomi">{nomi}</span>
      <span className="kuz-karta-sana">{qiymat ? sanaMatni(qiymat) : izoh}</span>
    </button>
  )
  return (
    <div className="kuz-tanlov" aria-live="polite">
      {karta('dan', 'Olib ketish', dan, 'Kunni tanlang')}
      <span className="kuz-tanlov-kun">{kun ? `${kun} kun` : '→'}</span>
      {karta('gacha', 'Qaytarish', gacha, dan ? 'Kunni tanlang' : '—')}
    </div>
  )
}
