import { som } from '../api'
import SummaInput from './SummaInput'

// To'lov usullari — Kassa POS dagi bilan bir xil nom va tartib
const TOLOV_USULLARI = [['naqd', 'Naqd'], ['karta', 'Terminal'], ['otkazma', "O'tkazma"]]

// Usul tugmalari (radio): to'lov, pul qaytarish (bekor qilish, ortiqcha to'lov), jarima va qarz to'lovi uchun (C-20)
export function UsulTanlov({ usul, onUsul, yorliq = "To'lov usuli" }) {
  return (
    <div className="pos-usullar" role="radiogroup" aria-label={yorliq}>
      {TOLOV_USULLARI.map(([k, nom]) => (
        <button key={k} type="button" role="radio" aria-checked={usul === k} className={usul === k ? 'tanlandi' : ''} onClick={() => onUsul(k)}>{nom}</button>
      ))}
    </div>
  )
}

// Summa va usul tanlovi (A-12): summa maydoni, «To'liq / 50% / 30%» tezkor tugmalari va usul tugmalari.
// Zakaz kartasidagi to'lov formasi ishlatadi; ko'rinishi Kassa POS dagi (.pos-tez, .pos-usullar) bilan bir xil.
// `maks` — qoldiq; `foizlar` — avansda qismli to'lov tugmalari; `usulsiz` — usul so'ralmaydi.
export default function TolovTanlov({ maks, summa, onSumma, usul, onUsul, foizlar = false, usulsiz = false, yorliq = 'Summa' }) {
  const n = Number(summa) || 0
  const tez = [['toliq', `To'liq: ${som(maks)}`, maks],
    ...(foizlar ? [50, 30].map((f) => [f, `${f}%`, Math.round((maks * f) / 100 / 1000) * 1000]) : [])]
  return (
    <div className="tolov-tanlov">
      <label>{yorliq} (maks. {som(maks)})
        <SummaInput value={summa} onChange={(e) => onSumma(e.target.value)} aria-invalid={n > maks || undefined} />
      </label>
      {n > maks && <p className="xato tolov-tanlov-xato" role="alert">Qoldiqdan oshib ketdi — eng ko'pi {som(maks)}.</p>}
      <div className="pos-tez" role="group" aria-label="Tezkor summa">
        {tez.map(([k, nom, qiymat]) => (
          <button key={k} type="button" className="ikkinchi kichik" aria-pressed={n === qiymat} onClick={() => onSumma(String(qiymat))}>{nom}</button>
        ))}
      </div>
      {!usulsiz && <UsulTanlov usul={usul} onUsul={onUsul} />}
    </div>
  )
}
