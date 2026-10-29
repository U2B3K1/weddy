import { useState } from 'react'
import { smenaQoshilish, xatoMatni } from '../api'

// «Avval smenaga qo'shiling» / «Ochiq smena yo'q» xatosi yonida amalni o'zi bajaradigan tugma:
// foydalanuvchi boshqa sahifaga o'tib, qaytib kelishi shart emas. `kod` — serverdan (`smena_qoshilish` | `smena_yoq`).
export default function SmenaTugma({ kod, onTayyor, onKassa }) {
  const [band, setBand] = useState(false)
  const [xato, setXato] = useState('')
  if (kod === 'smena_qoshilish') {
    const qoshil = async () => {
      setBand(true); setXato('')
      try { await smenaQoshilish(); onTayyor?.() } catch (e) { setXato(xatoMatni(e)); setBand(false) }
    }
    return (
      <>
        <button type="button" className="kichik" disabled={band} onClick={qoshil}>Smenaga qo'shilish</button>
        {xato && <span className="xato"> {xato}</span>}
      </>
    )
  }
  if (kod === 'smena_yoq' && onKassa) return <button type="button" className="kichik" onClick={onKassa}>Smenani ochish</button>
  return null
}
