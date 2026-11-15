import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import './uslublar.js'   // barcha uslublar, qat'iy tartibda — birinchi import bo'lib turishi shart
import Ildiz from './Ildiz.jsx'
import { AKADEMIYA } from './akademiya/host'

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
