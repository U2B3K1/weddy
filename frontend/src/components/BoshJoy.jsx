import { useContext } from 'react'
import { createPortal } from 'react-dom'
import { BoshJoyi } from './boshJoyi'

// Bo'lim boshi (kanvas «sarlavha» qolipi): sarlavha ostida bir qatorli xulosa, tablar qatorining o'ngida asosiy tugma.
// App ikki joy beradi; sahifa o'zi bilgan narsani o'sha joyga chizadi (masalan, Zakazlar ro'yxatida «+ Yangi zakaz»,
// kartasi ochilganda — yo'q). Joy hali tayyor bo'lmasa (birinchi chizish) — hech narsa chiqmaydi.
export function BoshXulosa({ children }) {
  const { xulosa } = useContext(BoshJoyi)
  return xulosa ? createPortal(children, xulosa) : null
}

export function BoshAmal({ children }) {
  const { amal } = useContext(BoshJoyi)
  return amal ? createPortal(children, amal) : null
}
