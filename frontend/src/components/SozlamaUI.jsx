import NavIkona from './NavIkona'
import { guruhla } from '../api'

// Kanvas «Sozlama» (SozlamaBolimShisha) qismlari: guruh sahifasida har bo'lim — alohida panel,
// ichida qatorlar «nom + izoh | boshqaruv» (almashtirgich, «− qiymat +», tanlov). Mantiq Sozlamalar.jsx da qoladi.

// Panel: tepada belgi plitkasi, sarlavha, izoh; o'ngda — almashtirgich yoki tugma
export function SPanel({ id, ikon, nomi, izoh, ong, children, className = '' }) {
  return (
    <section id={id ? `soz-${id}` : undefined} className={`blok soz-panel ${className}`.trim()} aria-label={nomi}>
      <div className="soz-bosh">
        <span className="soz-plitka" aria-hidden="true"><NavIkona nom={ikon} className="tugma-ikon" /></span>
        <div className="soz-bosh-matn"><h2>{nomi}</h2>{izoh && <p>{izoh}</p>}</div>
        {ong && <div className="soz-bosh-ong">{ong}</div>}
      </div>
      {children && <div className="soz-tana">{children}</div>}
    </section>
  )
}

// Qator: chapda nom va izoh, o'ngda boshqaruv
export function SQator({ nomi, izoh, children, className = '' }) {
  return (
    <div className={`soz-qator ${className}`.trim()}>
      <span className="soz-matn"><b>{nomi}</b>{izoh && <small>{izoh}</small>}</span>
      {children && <span className="soz-ong">{children}</span>}
    </div>
  )
}

// Almashtirgich — haqiqiy checkbox (klaviatura, ekran o'qigich, testlar uchun), ko'rinishi tilla «switch»
export function Almash({ checked, onChange, nomi }) {
  return <input type="checkbox" role="switch" className="soz-switch" aria-label={nomi} checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
}

// «− qiymat +»: qiymatni yozish ham mumkin; `summa` bo'lsa raqam guruhlab ko'rsatiladi
// `kasr` — o'nli qiymat (bonus foizi 2.5): yozilgan matn o'zicha uzatiladi (5. yozish mumkin bo'lsin), tugmalar 0.1 aniqlikda
export function Qadam({ qiymat, onChange, nomi, min = 0, max = Infinity, qadam = 1, birlik, summa = false, kasr = false, disabled = false }) {
  const v = Number(qiymat) || 0
  const chek = (x) => Math.min(max, Math.max(min, kasr ? Math.round(x * 10) / 10 : x))
  const korinish = summa ? guruhla(v) : String(qiymat ?? '')
  const yoz = (e) => {
    if (kasr) { onChange(e.target.value.replace(',', '.').replace(/[^\d.]/g, '').replace(/(\..*)\./g, '$1')); return }
    const r = e.target.value.replace(/\D/g, '')
    onChange(r === '' ? min : chek(Number(r)))
  }
  return (
    <span className={`soz-qadam${disabled ? ' ochiq-emas' : ''}`}>
      <button type="button" aria-label="Kamaytirish" title={`${nomi}: kamaytirish`} disabled={disabled || v <= min} onClick={() => onChange(chek(v - qadam))}>−</button>
      <span className="soz-qadam-q">
        <input inputMode={kasr ? 'decimal' : 'numeric'} aria-label={nomi} value={korinish} disabled={disabled} style={{ width: `${Math.max(2, korinish.length) + 0.5}ch` }}
          onChange={yoz} />
        {birlik && <span>{birlik}</span>}
      </span>
      <button type="button" aria-label="Oshirish" title={`${nomi}: oshirish`} disabled={disabled || v >= max} onClick={() => onChange(chek(v + qadam))}>+</button>
    </span>
  )
}

// Belgilanadigan karta (garov turlari): katak + nom + izoh
export function BelgiKarta({ checked, onChange, nomi, izoh }) {
  return (
    <label className={`soz-belgi${checked ? ' on' : ''}`}>
      <input type="checkbox" className="ustki-input" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="soz-katak" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5 9-10" /></svg></span>
      <span className="soz-matn"><b>{nomi}</b>{izoh && <small>{izoh}</small>}</span>
    </label>
  )
}

// Radio karta (kassa rejimi): doira + nom + izoh
export function RadioKarta({ name, checked, onChange, nomi, izoh }) {
  return (
    <label className={`soz-radio${checked ? ' on' : ''}`}>
      <input type="radio" className="ustki-input" name={name} checked={!!checked} onChange={onChange} />
      <span className="soz-doira" aria-hidden="true" />
      <span className="soz-matn"><b>{nomi}</b>{izoh && <small>{izoh}</small>}</span>
    </label>
  )
}

// Kichik holat yorlig'i (Faol, ulangan, Rejada…)
export const Yorliq = ({ tur = 'yopiq', children, ...rest }) => <span className={`soz-holat ${tur}`} {...rest}>{children}</span>
