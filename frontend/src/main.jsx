import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import './uslublar.js'   // barcha uslublar, qat'iy tartibda — birinchi import bo'lib turishi shart
import Ildiz from './Ildiz.jsx'
import { AKADEMIYA } from './akademiya/host'

// Google shriftlari uslubi index.html da oldindan yuklanadi (preload) va shu yerda ulanadi — birinchi ko'rinishni to'smaydi
const shriftlar = document.getElementById('shriftlar')
if (shriftlar) shriftlar.rel = 'stylesheet'

// Akademiya manzili o'sha index.html ni oladi — nomi va tavsifi o'ziniki bo'lsin (qidiruvda alohida sahifa bo'lib chiqadi)
if (AKADEMIYA) {
  document.title = "Libosa Academy — kelin liboslari saloni xodimlari uchun bepul darslar"
  const tavsif = "Salon ishini haqiqiy ilovaning o'zida o'rganing: hikoya ichida, qadam-baqadam. Bron, zakaz, kassa va mijoz bilan ishlash — 46 ta bepul dars."
  document.querySelector('meta[name="description"]')?.setAttribute('content', tavsif)
  document.querySelector('meta[property="og:title"]')?.setAttribute('content', 'Libosa Academy — salon xodimlari uchun bepul darslar')
  document.querySelector('meta[property="og:description"]')?.setAttribute('content', tavsif)
}

// Akademiya kodi faqat akademiya manzilida yuklanadi (asosiy saytga kerak emas)
const Akademiya = lazy(() => import('./akademiya/Akademiya.jsx'))
const IchkiIlova = lazy(() => import('./akademiya/IchkiIlova.jsx'))

// Akademiya manzilida: tashqi sahifa — dars paneli va ichki oyna; ichki oyna (`?ilova`) — ilovaning o'zi
const ICHKI = new URLSearchParams(window.location.search).has('ilova')

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {!AKADEMIYA ? <Ildiz /> : <Suspense fallback={null}>{ICHKI ? <IchkiIlova /> : <Akademiya />}</Suspense>}
  </StrictMode>,
)
