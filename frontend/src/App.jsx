import { useCallback, useEffect, useState } from 'react'
import { boshlash, boshlashYop, me, oflaynKesh, oflaynToplam, saqlangan, smenaHolati, sozlamalar, tarmoqXatosi } from './api'
import BoshEkran from './pages/BoshEkran'
import DashbordYon from './components/DashbordYon'
import Shapka from './components/Shapka'
import Dashbord from './pages/Dashbord'
import Hisobotlar from './pages/Hisobotlar'
import Kalendar from './pages/Kalendar'
import Kassa from './pages/Kassa'
import Katalog from './pages/Katalog'
import Kirish from './pages/Kirish'
import Mijozlar from './pages/Mijozlar'
import Oflayn from './pages/Oflayn'
import Platforma from './pages/Platforma'
import PlatformaFon from './pages/PlatformaFon'
import Reklama from './pages/Reklama'
import Sozlamalar, { SOZLAMA_BOLIMLAR } from './pages/Sozlamalar'
import YangiZakaz from './pages/YangiZakaz'
import Zakazlar from './pages/Zakazlar'

const HARAKATSIZLIK_MS = 10 * 60 * 1000
const OFLAYN_KESH_MS = 5 * 60 * 1000

export default function App() {
  const [xodim, setXodim] = useState(null)
  const [tayyor, setTayyor] = useState(!saqlangan.token())
  const [sahifa, setSahifa] = useState('bosh')
  const [zakazId, setZakazId] = useState(null)
  const [onlayn, setOnlayn] = useState(() => navigator.onLine)
  const [platforma, setPlatforma] = useState(() => window.location.hash === '#platforma')
  // Bosh sahifa — reklama taqdimoti; kirish ekrani «Kirish» tugmasi yoki #kirish manzili bilan ochiladi.
  // Xodim chiqqanda (yoki harakatsizlikdan keyin) reklamaga emas, to'g'ridan-to'g'ri kirish ekraniga qaytadi.
  const [kirish, setKirish] = useState(() => window.location.hash === '#kirish')
  // Sozlama ichidagi tanlangan bo'lim va «Orqaga» qaytadigan oldingi sahifa.
  const [sozlamaBolim, setSozlamaBolim] = useState('bandlik')
  // Katalog va mijozlar sahifalarining ichki bo'limlari ham chap paneldagi navda tugma ko'rinishida chiqadi.
  const [katalogBolim, setKatalogBolim] = useState('liboslar')
  const [mijozlarBolim, setMijozlarBolim] = useState('mijozlar')
  const [kassaBolim, setKassaBolim] = useState('hisobot')
  const [hisobotlarBolim, setHisobotlarBolim] = useState('hisobot')
  // Kassa smena ochiqligini App ham biladi — navdagi bo'lim tugmalari shunga qarab ko'rsatiladi (null = hali aniqlanmagan).
  const [kassaOchiq, setKassaOchiq] = useState(null)
  // 4.16: promokodlar bo'limi sozlamada o'chirilishi mumkin — navdagi «Promokodlar» tugmasi shunga qarab ko'rinadi.
  const [promoYoq, setPromoYoq] = useState(true)
  // «Orqaga» tugmasi qaytadigan oldingi asosiy sahifa.
  const [oldin, setOldin] = useState('bosh')
  // Rahbar uchun boshlash ro'yxati (chap paneldagi bosqichma-bosqich sozlash yo'riqnomasi).
  const [bosh, setBosh] = useState(null)
  // Telefonda nav chapdan chiqadigan menyu: shapkadagi tugma ochadi, bo'lim tanlanganda yopiladi.
  const [menyu, setMenyu] = useState(false)

  useEffect(() => { sozlamalar().then((s) => setPromoYoq(s.promokodlar_bolimi !== false)).catch(() => {}) }, [])
  // Boshlash ro'yxatini faqat rahbar ko'radi — nav tarkibiga qarab yuklanadi.
  useEffect(() => {
    if (xodim?.rol !== 'rahbar') return
    boshlash().then(setBosh).catch(() => {})
  }, [xodim?.rol])

  // Kassa smena ochilganda/yopilganda App'dagi nav tugmalarini yangilash uchun.
  const kassaYukla = useCallback(() => smenaHolati().then((s) => setKassaOchiq(s.ochiq)).catch(() => {}), [])

  // Sahifa yangilanganda mavjud sessiyani tiklash.
  useEffect(() => {
    if (!saqlangan.token()) return
    me().then((x) => { setXodim(x); saqlangan.xodimSaqla(x) })
      .catch((e) => {
        // Internet yo'q bo'lsa sessiya o'chirilmaydi: oflayn ko'rish rejimi uchun xodim keshdan tiklanadi.
        if (tarmoqXatosi(e) && saqlangan.xodim()) setXodim(saqlangan.xodim())
        else saqlangan.chiqish()
      })
      .finally(() => setTayyor(true))
  }, [])

  // 7-bo'lim: internet uzilsa «faqat ko'rish» rejimi; aloqa tiklansa o'zi qaytadi.
  useEffect(() => {
    const yoq = () => setOnlayn(true)
    const ochir = () => setOnlayn(false)
    window.addEventListener('online', yoq); window.addEventListener('weddy-onlayn', yoq)
    window.addEventListener('offline', ochir); window.addEventListener('weddy-oflayn', ochir)
    return () => {
      window.removeEventListener('online', yoq); window.removeEventListener('weddy-onlayn', yoq)
      window.removeEventListener('offline', ochir); window.removeEventListener('weddy-oflayn', ochir)
    }
  }, [])

  // FT-1.6: 10 daqiqa harakatsizlikdan keyin xodim avtomatik chiqadi; salon logini qurilmada qoladi.
  const kirgan = xodim !== null
  useEffect(() => {
    if (!kirgan) return undefined
    let t
    const chiq = () => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setXodim(null) }
    const qayta = () => { clearTimeout(t); t = setTimeout(chiq, HARAKATSIZLIK_MS) }
    const hodisalar = ['pointerdown', 'keydown', 'scroll', 'touchstart']
    hodisalar.forEach((h) => window.addEventListener(h, qayta, { passive: true }))
    qayta()
    return () => { clearTimeout(t); hodisalar.forEach((h) => window.removeEventListener(h, qayta)) }
  }, [kirgan])

  // Onlayn paytda oflayn keshni yangilab turadi; oflaynda esa aloqa tiklanganini tekshiradi.
  useEffect(() => {
    if (!kirgan) return undefined
    const yangila = () => oflaynToplam().then(oflaynKesh.saqla).catch(() => {})
    yangila()
    const t = setInterval(yangila, onlayn ? OFLAYN_KESH_MS : 10000)
    return () => clearInterval(t)
  }, [kirgan, onlayn])

  if (!tayyor) return null
  if (platforma) return (
    <div className="ilova">
      <PlatformaFon />
      <Platforma onOrqaga={() => { window.location.hash = ''; setPlatforma(false) }} />
    </div>
  )
  const platformaga = () => { window.location.hash = '#platforma'; setPlatforma(true) }
  const kirishga = (ochiq) => { window.location.hash = ochiq ? '#kirish' : ''; window.scrollTo(0, 0); setKirish(ochiq) }
  if (!xodim && !kirish) return <Reklama onKirish={() => kirishga(true)} onPlatforma={platformaga} />
  if (!xodim) {
    return (
      <>
        <PlatformaFon />
        <button className="kirish-orqaga ikkinchi kichik" onClick={() => kirishga(false)}>← Bosh sahifa</button>
        <Kirish onKirdi={(x) => { setXodim(x); setSahifa(x.rol === 'rahbar' ? 'dashbord' : 'bosh'); me().then(setXodim).catch(() => {}) }} />
      </>
    )
  }

  const rahbar = xodim.rol === 'rahbar'
  const zakaz = (id) => { setZakazId(id); setSahifa('zakazlar') }
  const bolimlar = [
    ...(rahbar ? [['dashbord', 'Dashbord']] : []),
    ['bosh', 'Bosh'], ['yangi', 'Yangi zakaz'], ['zakazlar', 'Zakazlar'], ['mijozlar', 'Mijozlar'], ['kalendar', 'Bandlik'], ['katalog', 'Katalog'], ['kassa', 'Kassa'],
    ...(rahbar ? [['hisobotlar', 'Hisobot'], ['sozlamalar', 'Sozlama']] : []),
  ]

  return (
    <div className="ilova">
      <PlatformaFon />
      <Shapka ochiq={menyu} onMenyu={() => setMenyu(!menyu)}>
        <span>{xodim.ism}</span>
        <button className="ikkinchi kichik" onClick={() => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setXodim(null) }}>
          <span className="faqat-keng">Xodimni almashtirish</span><span className="faqat-tor">Almashtirish</span>
        </button>
      </Shapka>
      {xodim.salon_holati === 'faqat_korish' && (
        <p className="ogohlantirish obuna-banner">Obuna muddati tugagan: salon «faqat ko'rish» rejimida, yangi zakaz yaratilmaydi.</p>
      )}
      {xodim.obuna_ogohlantirish_kun != null && rahbar && (
        <p className="ogohlantirish obuna-banner">
          Obuna to'lovi muddati o'tgan. {xodim.obuna_ogohlantirish_kun} kundan keyin salon «faqat ko'rish» rejimiga o'tadi.
        </p>
      )}
      {!onlayn && <p className="ogohlantirish obuna-banner">Internet yo'q: faqat ko'rish rejimi.</p>}
      {!onlayn ? <main><Oflayn /></main> : (<>
      <main>
        {sahifa === 'dashbord' && rahbar && <Dashbord onBolim={setSahifa} />}
        {sahifa === 'bosh' && <BoshEkran rahbar={rahbar} onZakaz={zakaz} onYangi={() => setSahifa('yangi')} onKassa={() => setSahifa('kassa')} />}
        {sahifa === 'yangi' && <YangiZakaz onTayyor={zakaz} />}
        {sahifa === 'zakazlar' && <Zakazlar tanlangan={zakazId} onTanla={setZakazId} />}
        {sahifa === 'mijozlar' && <Mijozlar rahbar={rahbar} onZakaz={zakaz} bolim={mijozlarBolim} promoYoq={promoYoq} />}
        {sahifa === 'kalendar' && <Kalendar onZakaz={zakaz} />}
        {sahifa === 'katalog' && <Katalog rahbar={rahbar} bolim={katalogBolim} />}
        {sahifa === 'kassa' && <Kassa rahbar={rahbar} bolim={kassaBolim} onHolatOzgardi={kassaYukla} />}
        {sahifa === 'hisobotlar' && rahbar && <Hisobotlar bolim={hisobotlarBolim} onBolim={setSahifa} />}
        {sahifa === 'sozlamalar' && rahbar && <Sozlamalar menId={xodim.id} bolim={sozlamaBolim} onBolim={setSozlamaBolim} />}
      </main>
      {menyu && <div className="menyu-parda" onClick={() => setMenyu(false)} />}
      <nav className={`pastki ${menyu ? 'ochiq' : ''}`}
        onClick={(e) => { const b = e.target.closest('button'); if (b && !b.classList.contains('orqaga')) setMenyu(false) }}>
        {rahbar && bosh?.korsatilsin && (
          <div className="boshlash-panel">
            <h4>Boshlash</h4>
            {bosh.qadamlar.map((q) => (
              <button key={q.kalit} type="button" className="qator-btn" onClick={() => setSahifa(q.bolim)}>
                <span>{q.bajarildi ? '✓' : '○'} {q.nomi}</span>
              </button>
            ))}
            <button className="ikkinchi kichik" onClick={() => boshlashYop().then(setBosh)}>Ro'yxatni yashirish</button>
          </div>
        )}
        {rahbar && sahifa === 'dashbord' && <DashbordYon onBolim={setSahifa} />}
        {sahifa === 'sozlamalar' ? (
          <>
            <button type="button" className="orqaga" onClick={() => setSahifa(oldin)}>← Orqaga</button>
            {SOZLAMA_BOLIMLAR.map((b) => (
              <button key={b.id} type="button" className={`sozlama-bolim ${sozlamaBolim === b.id ? 'faol' : ''}`}
                onClick={() => setSozlamaBolim(b.id)}>{b.nomi}</button>
            ))}
          </>
        ) : sahifa === 'katalog' ? (
          <>
            <button type="button" className="orqaga" onClick={() => setSahifa(oldin)}>← Orqaga</button>
            {[['liboslar', 'Liboslar'], ['aksessuarlar', 'Aksessuarlar']].map(([id, nomi]) => (
              <button key={id} type="button" className={katalogBolim === id ? 'faol' : ''}
                onClick={() => setKatalogBolim(id)}>{nomi}</button>
            ))}
          </>
        ) : sahifa === 'mijozlar' ? (
          <>
            <button type="button" className="orqaga" onClick={() => setSahifa(oldin)}>← Orqaga</button>
            {[['mijozlar', 'Mijozlar'], ['salonchilar', 'Salonchilar'], ...(rahbar && promoYoq ? [['promokodlar', 'Promokodlar']] : [])].map(([id, nomi]) => (
              <button key={id} type="button" className={mijozlarBolim === id ? 'faol' : ''}
                onClick={() => setMijozlarBolim(id)}>{nomi}</button>
            ))}
          </>
        ) : sahifa === 'kassa' ? (
          <>
            <button type="button" className="orqaga" onClick={() => setSahifa(oldin)}>← Orqaga</button>
            {kassaOchiq && [['hisobot', 'Hisobot'], ['xarajat', 'Xarajat'], ['inkassatsiya', 'Inkassatsiya'], ['zalog', 'Zaloglar'], ['chiqish', 'Chiqish'], ['yopish', 'Yopish']].map(([id, nomi]) => (
              <button key={id} type="button" className={kassaBolim === id ? 'faol' : ''}
                onClick={() => setKassaBolim(id)}>{nomi}</button>
            ))}
            {rahbar && (
              <button type="button" className={kassaBolim === 'tarix' ? 'faol' : ''}
                onClick={() => setKassaBolim('tarix')}>Tarix</button>
            )}
          </>
        ) : sahifa === 'hisobotlar' ? (
          <>
            <button type="button" className="orqaga" onClick={() => setSahifa(oldin)}>← Orqaga</button>
            {[['hisobot', 'Hisobot'], ['pnl', 'Foyda va zarar'], ['bildirishnoma', 'Bildirishnomalar'], ['grafik', 'Grafik']].map(([id, nomi]) => (
              <button key={id} type="button" className={hisobotlarBolim === id ? 'faol' : ''}
                onClick={() => setHisobotlarBolim(id)}>{nomi}</button>
            ))}
          </>
        ) : (
          bolimlar.map(([k, nom]) => (
            <button key={k} className={sahifa === k ? 'faol' : ''}
              onClick={() => {
                if (k === 'sozlamalar' || k === 'katalog' || k === 'mijozlar') setOldin(sahifa)
                setSahifa(k)
                if (k === 'zakazlar') setZakazId(null)
              }}>{nom}</button>
          ))
        )}
      </nav>
      </>)}
    </div>
  )
}
