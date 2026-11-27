import { useEffect, useState } from 'react'
import { som, tolovCheki, xatoMatni } from '../api'
import Oyna from './Oyna'
import RasmTanlash from './RasmTanlash'
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

// O'tkazma chekini ko'rish (rahbar yoki to'lovni yozgan xodim): fayl maxfiy — token bilan olinib, oynada chiqadi
export function ChekKorish({ id, onYop }) {
  const [url, setUrl] = useState('')
  const [xato, setXato] = useState('')
  useEffect(() => {
    let manzil = ''
    tolovCheki(id).then((u) => { manzil = u; setUrl(u) }).catch((e) => setXato(xatoMatni(e)))
    return () => { if (manzil) URL.revokeObjectURL(manzil) }
  }, [id])
  return (
    <Oyna sarlavha="O'tkazma cheki" onYop={onYop}>
      {xato ? <p className="xato">{xato}</p> : url ? <img className="chek-rasm" src={url} alt="O'tkazma cheki" /> : <p className="malumot">Yuklanmoqda…</p>}
    </Oyna>
  )
}

// O'tkazma cheki (egasi qarori: o'tkazmada majburiy) — mijozning bank ilovasidagi skrinshot yoki rasm.
// Tanlangan rasm kichik ko'rinishda chiqadi; «Boshqasini tanlash» bilan almashtiriladi.
export function ChekMaydoni({ chek, onChek }) {
  const [korinish, setKorinish] = useState('')
  useEffect(() => {
    if (!chek) { setKorinish(''); return undefined }
    const url = URL.createObjectURL(chek)
    setKorinish(url)
    return () => URL.revokeObjectURL(url)
  }, [chek])
  return (
    <div className="chek-maydoni">
      <p className="pos-yorliq">O'tkazma cheki <span className="chek-majburiy">— majburiy</span></p>
      {chek ? (
        <div className="chek-tanlangan">
          {korinish && <img src={korinish} alt="Tanlangan o'tkazma cheki" />}
          <span>{chek.name}</span>
          <button type="button" className="ikkinchi kichik" onClick={() => onChek(null)}>Boshqasini tanlash</button>
        </div>
      ) : (
        <>
          <RasmTanlash matn="O'tkazma chekini qo'shish" onTanla={(f) => onChek(f[0])} />
          <small className="malumot">Mijozning bank ilovasidagi o'tkazma skrinshoti. Rahbar «Keldi» deyishdan oldin shu chekni ko'radi.</small>
        </>
      )}
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
