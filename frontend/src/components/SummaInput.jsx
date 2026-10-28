import { useRef, useState } from 'react'
import { guruhla } from '../api'

// Summa maydoni: 2400000 yozilsa «2 400 000» ko'rinadi. onChange ga oddiy input kabi hodisa keladi,
// faqat e.target.value toza raqam ('2400000') — mavjud set(k) yordamchilari o'zgarishsiz ishlaydi.
// value berilmasa (forma faqat onChange bilan yig'ilsa) — qiymatni o'zi saqlaydi.
export default function SummaInput({ value, onChange, className = '', ...rest }) {
  const ref = useRef(null)
  const [ichki, setIchki] = useState('')
  const xom = value === undefined ? ichki : value
  const matn = xom === '' || xom == null ? '' : guruhla(xom)

  const ozgar = (e) => {
    const el = e.target
    const raqam = el.value.replace(/\D/g, '').replace(/^0+(?=\d)/, '').slice(0, 15)
    // Bo'shliqlar qo'shilganda kursor oxiriga sakramasin: undan oldingi raqamlar soni saqlanadi
    let oldin = el.value.slice(0, el.selectionStart).replace(/\D/g, '').length
    if (value === undefined) setIchki(raqam)
    onChange?.({ target: { value: raqam, name: el.name } })
    requestAnimationFrame(() => {
      const t = ref.current
      if (!t || document.activeElement !== t) return
      let i = 0
      while (oldin > 0 && i < t.value.length) { if (/\d/.test(t.value[i])) oldin--; i++ }
      t.setSelectionRange(i, i)
    })
  }

  return (
    <input ref={ref} {...rest} className={`summa-input ${className}`.trim()} type="text" inputMode="numeric"
      autoComplete="off" value={matn} onChange={ozgar} />
  )
}
