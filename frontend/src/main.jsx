import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './ichki.css'
import './yangi-dizayn.css'
import App from './App.jsx'
import Akademiya from './akademiya/Akademiya.jsx'
import IchkiIlova from './akademiya/IchkiIlova.jsx'
import { AKADEMIYA } from './akademiya/host'

// Akademiya manzilida: tashqi sahifa — dars paneli va ichki oyna; ichki oyna (`?ilova`) — ilovaning o'zi
const ICHKI = new URLSearchParams(window.location.search).has('ilova')

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {!AKADEMIYA ? <App /> : ICHKI ? <IchkiIlova /> : <Akademiya />}
  </StrictMode>,
)
