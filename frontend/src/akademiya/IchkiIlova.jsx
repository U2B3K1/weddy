import { useEffect } from 'react'
import App from '../App.jsx'
import { saqlangan } from '../api'

// Akademiya ichki oynasidagi ilova (manzilda `?ilova`). Ilovaning o'zi o'zgarmagan — faqat chiqish boshqacha:
// akademiyada salon logini ekrani yo'q, shuning uchun sessiya tugasa butun sahifa akademiyaning kirish sahifasiga qaytadi.
export default function IchkiIlova() {
  useEffect(() => {
    const chiq = () => { window.top.location.replace('/') }
    if (!saqlangan.token()) { chiq(); return undefined }
    // Ilova chiqishda (yoki harakatsizlikdan keyin) tokenni o'chirib, manzilni «#kirish» ga o'tkazadi
    const tekshir = () => { if (!saqlangan.token()) chiq() }
    window.addEventListener('hashchange', tekshir)
    return () => window.removeEventListener('hashchange', tekshir)
  }, [])
  return <App />
}
