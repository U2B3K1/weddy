import { useEffect, useState } from 'react'
import Reklama from './pages/Reklama'
import { saqlangan } from './api'
import { AKADEMIYA } from './akademiya/host'

// Ildiz: bosh sahifa mehmoniga faqat reklama taqdimoti ko'rsatiladi, ilovaning o'zi (App.jsx — kirish ekrani va
// barcha ichki sahifalar, ≈0,7 MB kod) esa kerak bo'lgandagina yuklanadi. Avval mehmon ham butun ilovani yuklab olardi —
// telefonda birinchi ko'rinish shundan kechikardi.
//
// Ilova bitta bo'lak bo'lib yuklanadi: ichkarida sahifalar alohida-alohida yuklanmaydi, shuning uchun salonda internet
// uzilib qolsa ham ochilgan ilovaning hamma sahifasi ishlayveradi (oflayn rejim).

let Ilova = null   // yuklangach — App komponenti
let yuklanmoqda = null
const ilovaYukla = () => {
  if (!yuklanmoqda) yuklanmoqda = import('./App.jsx').then((m) => { Ilova = m.default }).catch((e) => { yuklanmoqda = null; throw e })
  return yuklanmoqda
}

// Mehmon — kirmagan va manzilda kirish/platforma belgisi yo'q odam. Qolgan hollarda ilova darhol kerak.
const mehmon = () => !saqlangan.token() && window.location.hash !== '#kirish' && window.location.hash !== '#platforma'
const QAYTA = 'weddy.ilova_qayta'   // bo'lak yuklanmay qolganda sahifa bir marta yangilanadi (shu belgining vaqti bilan)

// Ilova kerakligi oldindan ma'lum bo'lsa — kutmasdan yuklana boshlaydi (akademiya manzilida bu fayl ishlatilmaydi)
if (!AKADEMIYA && !mehmon()) ilovaYukla().catch(() => {})

export default function Ildiz() {
  const [holat, setHolat] = useState(() => (mehmon() ? 'reklama' : Ilova ? 'ilova' : 'kutish'))

  // Ilovani ochish: bo'lak yuklangach ko'rsatiladi. Yuklanmasa — odatda yangi versiya chiqqan va eski bo'lak serverda
  // qolmagan: sahifa bir marta yangilanadi (yangi index.html yangi bo'lakni oladi). Yana bo'lmasa — xabar.
  // kirishga=true — bosh sahifadagi «Kirish»: manzilga «#kirish» qo'yiladi (App shu belgiga qarab kirish ekranini ochadi).
  // Belgi ilova tayyor bo'lgandagina qo'yiladi — ungacha mehmon bosh sahifada o'z joyida qoladi.
  const och = (kirishga) => {
    const belgi = () => { if (kirishga) { window.location.hash = '#kirish'; window.scrollTo(0, 0) } }
    ilovaYukla().then(() => { belgi(); setHolat('ilova') }).catch(() => {
      let oldingi = 0
      try { oldingi = Number(sessionStorage.getItem(QAYTA)) || 0 } catch { /* saqlanmasa ham ishlaydi */ }
      if (Date.now() - oldingi > 15000) {
        try { sessionStorage.setItem(QAYTA, String(Date.now())) } catch { /* — */ }
        belgi(); window.location.reload()
      } else setHolat('xato')
    })
  }
  useEffect(() => { if (holat === 'kutish') och(false) }, [holat])   // eslint-disable-line react-hooks/exhaustive-deps

  // Bosh sahifada: mehmon birinchi marta biror narsaga tegishi bilan ilova fonda yuklana boshlaydi —
  // «Kirish» bosilganda u odatda tayyor turadi. Tegmagan mehmonga (va tezlik o'lchagichlarga) u yuklanmaydi.
  useEffect(() => {
    if (holat !== 'reklama') return undefined
    const hodisalar = ['pointerdown', 'keydown', 'wheel', 'touchstart']
    const boshla = () => { tozala(); ilovaYukla().catch(() => {}) }
    const tozala = () => hodisalar.forEach((h) => window.removeEventListener(h, boshla))
    hodisalar.forEach((h) => window.addEventListener(h, boshla, { passive: true }))
    return tozala
  }, [holat])

  if (holat === 'ilova' && Ilova) return <Ilova />
  if (holat === 'xato') {
    return (
      <p role="alert" style={{ position: 'fixed', inset: 0, display: 'grid', placeItems: 'center', margin: 0, padding: 24, textAlign: 'center', color: '#F5F2EE', background: '#0e1a2b', fontSize: 18 }}>
        Sahifani ochib bo'lmadi. Internet aloqasini tekshirib, sahifani yangilang.
      </p>
    )
  }
  if (holat === 'kutish') return null
  return <Reklama onKirish={() => och(true)} />
}
