import { useCallback, useEffect, useRef, useState } from 'react'
import { akademiyaKirish, akademiyaMehmon, saqlangan, xatoMatni } from '../api'
import DarsPaneli from './DarsPaneli.jsx'
import Muqova from './Muqova.jsx'
import './akademiya.css'

const KALIT = '#akademiya='
const REJIM = 'weddy.akademiya_rejim'

// Havoladagi kod bir marta ishlaydi: StrictMode effektni ikki marta chaqirsa ham so'rov bitta bo'lsin
let kirishSorovi = null
function koddanKirish() {
  const h = window.location.hash
  if (!h.startsWith(KALIT)) return null
  if (!kirishSorovi) {
    const kod = decodeURIComponent(h.slice(KALIT.length))
    // kod manzilda qolmasin (tarix, skrinshot, nusxalash)
    window.history.replaceState(null, '', window.location.pathname)
    saqlangan.qurilmaOchir()  // shu manzilda eski sessiya qolgan bo'lsa — yangisi bilan almashadi
    kirishSorovi = akademiyaKirish(kod).then((d) => {
      saqlangan.tokenSaqla(d.token)
      saqlangan.xodimSaqla(d.xodim)
    })
  }
  return kirishSorovi
}

// Akademiya manzilidagi ildiz. Dars paneli va ilova yonma-yon: ilova ichki oynada (iframe) ochiladi —
// shunda u o'z enini «ekran» deb biladi (tor joyda planshet ko'rinishiga o'zi o'tadi) va oynalari panel ustiga chiqmaydi.
export default function Akademiya() {
  // yuklanmoqda (havoladagi kod almashtirilmoqda) | kirilmagan | tayyor
  const [holat, setHolat] = useState(() => (window.location.hash.startsWith(KALIT) ? 'yuklanmoqda'
    : saqlangan.token() ? 'tayyor' : 'kirilmagan'))
  const [xato, setXato] = useState('')
  // Mehmon: ro'yxatdan o'tmasdan sinab ko'rish — server vaqtinchalik o'quv saloni ochadi (uchta ochiq dars)
  const [mehmonBand, setMehmonBand] = useState(false)
  const mehmonKir = () => {
    setMehmonBand(true); setXato('')
    saqlangan.qurilmaOchir()
    akademiyaMehmon().then((d) => { saqlangan.tokenSaqla(d.token); saqlangan.xodimSaqla(d.xodim); setHolat('tayyor') })
      .catch((e) => setXato(xatoMatni(e))).finally(() => setMehmonBand(false))
  }
  // Tor ekranda (planshet, telefon) bir vaqtda bittasi ko'rinadi: dars yoki mashq
  const [rejim, setRejimXom] = useState(() => sessionStorage.getItem(REJIM) || 'dars')
  const setRejim = useCallback((r) => { sessionStorage.setItem(REJIM, r); setRejimXom(r) }, [])
  const ilova = useRef(null)
  // Ilova faqat yo'naltirilgan qadam paytida ochiq: dars boshlanmagan yoki tugagan bo'lsa ustidan parda tushadi —
  // o'quvchi o'quv salonida maqsadsiz kezib, sozlamalarni o'zgartirib yurmaydi
  const [mashqda, setMashqda] = useState(false)
  const mashqHolati = useCallback((aktiv) => setMashqda(aktiv), [])

  useEffect(() => {
    koddanKirish()?.then(() => setHolat('tayyor')).catch((e) => { setXato(xatoMatni(e)); setHolat('kirilmagan') })
  }, [])

  // Panelda o'qib turgan odam «harakatsiz» hisoblanmasin: paneldagi harakat ilovaga ham bildiriladi
  // (ilova 10 daqiqa harakatsizlikdan keyin o'zi chiqadi).
  useEffect(() => {
    if (holat !== 'tayyor') return undefined
    const bildir = () => { try { ilova.current?.contentWindow?.dispatchEvent(new Event('keydown')) } catch { /* yuklanmoqda */ } }
    // g'ildirak va barmoq bilan aylantirish ham «faollik»: bob sahifasi yoki varaqni o'qiyotgan odam hech narsa bosmaydi
    const hodisalar = ['pointerdown', 'keydown', 'wheel', 'touchmove']
    hodisalar.forEach((h) => window.addEventListener(h, bildir, { passive: true }))
    return () => hodisalar.forEach((h) => window.removeEventListener(h, bildir))
  }, [holat])

  // Dars boshlanganda server o'quv salonini qayta tayyorlaydi — ilova ma'lumotni boshidan o'qishi kerak
  const oynaOl = useCallback(() => ilova.current, [])
  const ilovaniYangila = useCallback(() => { ilova.current?.contentWindow?.location.reload() }, [])

  if (holat === 'yuklanmoqda') return <div className="ak-kirish"><p className="ak-xira">Akademiya ochilmoqda…</p></div>
  // Kirish so'ralmaydi: «Boshlash» mehmon sifatida ichkariga olib kiradi; kirish bepul darslar tugaganda so'raladi
  if (holat === 'kirilmagan') return <Muqova xato={xato} band={mehmonBand} onBoshla={mehmonKir} />
  return (
    // Mashq paytida — panel va ilova yonma-yon; qolgan paytda (yo'l xaritasi, hikoya, yakun) akademiya butun ekranda:
    // ilova ko'rinmaydi, shuning uchun o'quv salonida maqsadsiz kezib bo'lmaydi
    <div className="ak-qobiq" data-rejim={rejim} data-mashq={mashqda ? 'ha' : 'yoq'} data-parda={mashqda === 'yakun' ? 'ha' : undefined}>
      <DarsPaneli rejim={rejim} onRejim={setRejim} onIlovaYangila={ilovaniYangila} oynaOl={oynaOl} onMashq={mashqHolati} />
      <div className="ak-oyna">
        {/* doimiy belgi: bu haqiqiy salon emas */}
        <p className="ak-belgi"><b>O'quv saloni</b><span>Bu yerdagi mijoz, zakaz va pullar haqiqiy emas — haqiqiy saloningizga ta'sir qilmaydi</span></p>
        <iframe ref={ilova} className="ak-ilova" src="/?ilova=1" title="O'quv saloni — Libosa ilovasi" />
      </div>
    </div>
  )
}
