import { useEffect, useState } from 'react'
import { boshlash, boshlashYop, dashbord, me, oflaynKesh, oflaynToplam, saqlangan, som, tarmoqXatosi } from './api'
import BoshEkran from './pages/BoshEkran'
import Tasdiq from './components/Tasdiq'
import NavIkona from './components/NavIkona'
import Shapka from './components/Shapka'
import UstkiPanel from './components/UstkiPanel'
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
import Sozlamalar from './pages/Sozlamalar'
import YangiZakaz from './pages/YangiZakaz'
import Zakazlar from './pages/Zakazlar'
import { BELGI_D } from './pages/ezazBelgi'
import { GURUHLAR, SOZLAMA_BOLIMLAR } from './pages/sozlamaBolimlari'

const HARAKATSIZLIK_MS = 10 * 60 * 1000
const OGOHLANTIRISH_MS = 30 * 1000 // chiqishdan 30 soniya oldin «Davom etyapsizmi?»
const OFLAYN_KESH_MS = 5 * 60 * 1000

export default function App() {
  const [xodim, setXodim] = useState(null)
  const [tayyor, setTayyor] = useState(!saqlangan.token())
  // Asosiy bo'limlar: bosh, yangi, zakazlar, mijozlar, katalog, kassa, hisobotlar, sozlamalar
  const [sahifa, setSahifaXom] = useState('bosh')
  const [zakazId, setZakazId] = useState(null)
  const [onlayn, setOnlayn] = useState(() => navigator.onLine)
  const [platforma, setPlatforma] = useState(() => window.location.hash === '#platforma')
  // Bosh sahifa — reklama taqdimoti; kirish ekrani «Kirish» tugmasi yoki #kirish manzili bilan ochiladi.
  // Xodim chiqqanda (yoki harakatsizlikdan keyin) reklamaga emas, to'g'ridan-to'g'ri kirish ekraniga qaytadi.
  const [kirish, setKirish] = useState(() => window.location.hash === '#kirish')
  // Sozlama ichidagi tanlangan bo'lim (bo'limlar ro'yxati Sozlamalar sahifasining o'zida).
  const [sozlamaBolim, setSozlamaBolim] = useState('bandlik')
  // Chap panel rejimi: Kassa, Hisobot yoki Sozlama bosilganda panel o'sha bo'lim menyusiga aylanadi; «Asosiy» — asosiy menyuga qaytish
  const [navRejim, setNavRejim] = useState(null)
  // Sozlama menyusida ochiq guruh (akkordeon — bir vaqtda bittasi)
  const [sozlamaGuruh, setSozlamaGuruh] = useState(null)
  // Ichki bo'limlar faqat sahifa tepasidagi segmentda chiqadi; chap panel doim asosiy bo'limlarni ko'rsatadi.
  const [zakazlarBolim, setZakazlarBolim] = useState('royxat')
  const [katalogBolim, setKatalogBolim] = useState('liboslar')
  const [mijozlarBolim, setMijozlarBolim] = useState('mijozlar')
  // Kassa — POS ish joyi; «Yangi zakaz» ham uning ichki bo'limi
  const [kassaBolim, setKassaBolim] = useState('yangi')
  // Zakaz yaratilgach to'g'ridan-to'g'ri to'lovga: shu zakaz tanlangan holda (n — har safar yangi)
  const [tolovZakaz, setTolovZakaz] = useState(null)
  const [hisobotlarBolim, setHisobotlarBolim] = useState('hisobot')
  // Rahbar uchun boshlash ro'yxati (bosh sahifadagi bosqichma-bosqich sozlash yo'riqnomasi).
  const [bosh, setBosh] = useState(null)
  // Telefonda nav chapdan chiqadigan menyu: shapkadagi tugma ochadi, bo'lim tanlanganda yopiladi.
  const [menyu, setMenyu] = useState(false)
  const [uxlayapti, setUxlayapti] = useState(false)
  // Yuqori paneldagi global qidiruv Zakazlar ro'yxatiga uzatiladi (n — bir xil matnni qayta qidirish uchun)
  const [qidiruv, setQidiruv] = useState(null)
  // Rahbar bildirishnomalari (qo'ng'iroqcha): qaror kutayotganlar va ogohlantirishlar — har 2 daqiqada
  const [xabarD, setXabarD] = useState(null)
  useEffect(() => {
    if (xodim?.rol !== 'rahbar') return undefined
    const yukla = () => dashbord('oy', '').then(setXabarD).catch(() => {})
    yukla()
    const t = setInterval(yukla, 120000)
    return () => clearInterval(t)
  }, [xodim?.rol])

  // Boshlash ro'yxatini faqat rahbar ko'radi — nav tarkibiga qarab yuklanadi.
  useEffect(() => {
    if (xodim?.rol !== 'rahbar') return
    boshlash().then(setBosh).catch(() => {})
  }, [xodim?.rol])


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
    let t, t0
    const chiq = () => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setUxlayapti(false); setXodim(null) }
    const qayta = () => {
      clearTimeout(t); clearTimeout(t0); setUxlayapti(false)
      t0 = setTimeout(() => setUxlayapti(true), HARAKATSIZLIK_MS - OGOHLANTIRISH_MS)
      t = setTimeout(chiq, HARAKATSIZLIK_MS)
    }
    const hodisalar = ['pointerdown', 'keydown', 'scroll', 'touchstart']
    hodisalar.forEach((h) => window.addEventListener(h, qayta, { passive: true }))
    qayta()
    return () => { clearTimeout(t); clearTimeout(t0); hodisalar.forEach((h) => window.removeEventListener(h, qayta)) }
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
      <PlatformaFon bezak={false} />
      <Platforma onOrqaga={() => { window.location.hash = ''; setPlatforma(false) }} />
    </div>
  )
  const kirishga = (ochiq) => { window.location.hash = ochiq ? '#kirish' : ''; window.scrollTo(0, 0); setKirish(ochiq) }
  if (!xodim && !kirish) return <Reklama onKirish={() => kirishga(true)} />
  if (!xodim) {
    return (
      <>
        <PlatformaFon nurli />
        <button className="kirish-orqaga ikkinchi kichik" onClick={() => kirishga(false)}>← Bosh sahifa</button>
        <Kirish onKirdi={(x) => { setXodim(x); setSahifaXom('bosh'); me().then(setXodim).catch(() => {}) }} />
      </>
    )
  }

  const rahbar = xodim.rol === 'rahbar'
  // Bo'limga o'tish. «kassa:zalog» ko'rinishida ichki bo'lim ham beriladi (ogohlantirish aynan kerakli joyni ochsin).
  // Eski nomlar ham qabul qilinadi: «dashbord» — bosh sahifa, «kalendar» — zakazlardagi bandlik
  // (backend «boshlash» ro'yxati shu nomlarni yuborishi mumkin).
  const setSahifa = (manzil) => {
    let [k, ich] = manzil.split(':')
    if (k === 'dashbord') k = 'bosh'
    if (k === 'yangi') { k = 'kassa'; ich = 'yangi' }  // «Yangi zakaz» endi Kassa ichida
    if (ich) {
      ({ zakazlar: setZakazlarBolim, katalog: setKatalogBolim, mijozlar: setMijozlarBolim, kassa: setKassaBolim,
        hisobotlar: setHisobotlarBolim, sozlamalar: setSozlamaBolim })[k]?.(ich)
    }
    if (k === 'kalendar') { k = 'zakazlar'; setZakazlarBolim('bandlik') }
    if (k === 'zakazlar') setZakazId(null)
    // Kassa / Hisobot / Sozlamaga kirilsa chap panel o'sha bo'lim menyusiga o'tadi; Sozlamada tanlangan bo'lim guruhi ochiladi
    setNavRejim(['kassa', 'hisobotlar', 'sozlamalar'].includes(k) ? k : null)
    if (k === 'sozlamalar') {
      const b = ich || sozlamaBolim
      setSozlamaGuruh(SOZLAMA_BOLIMLAR.find((x) => x.id === b)?.guruh || GURUHLAR[0].nomi)
    }
    setSahifaXom(k)
    setMenyu(false)
    window.scrollTo(0, 0)
  }
  // Zakaz kartasi ochiladi; «‹» bosilganda qaysi ichki bo'limdan (ro'yxat yoki bandlik) kelgan bo'lsa, o'shanga qaytadi
  const zakaz = (id) => { setZakazId(id); if (sahifa !== 'zakazlar') setZakazlarBolim('royxat'); setSahifaXom('zakazlar'); window.scrollTo(0, 0) }
  // Hisobot bo'limlari: [id, nomi, ikonka] — chap paneldagi Hisobot menyusi va telefondagi segment
  const HISOBOT_ROYXAT = [['hisobot', 'Umumiy hisobot', 'hisobotlar'], ['pnl', 'Foyda va zarar', 'tarozi'], ['xarajat', 'Xarajatlar', 'hamyon'],
    ['bonus', 'Sotuvchi bonusi', 'sovga'], ['bank', 'Bank solishtirish', 'bank'], ['grafik', 'Grafik', 'ustun']]
  const bolimlar = [
    ['bosh', 'Dashboard'], ['kassa', 'Kassa'], ['katalog', 'Katalog'], ['zakazlar', 'Zakazlar'], ['mijozlar', 'Mijozlar'],
    ...(rahbar ? [['hisobotlar', 'Hisobot'], ['sozlamalar', 'Sozlama']] : []),
  ]

  // Ichki bo'limlar — sahifa tepasidagi segment (barcha ekranlarda bir xil joyda). Sozlama o'z menyusiga ega.
  // Kassa (POS): smena amallari (ochish, chiqish, yopish) — smena panelida; bu yerda ish ekranlari
  const kassaRoyxat = [['yangi', 'Yangi zakaz', 'yangi'], ['tolov', "To'lov qabul", 'kassa'], ['xarajat', 'Xarajat', 'hamyon'],
    ['inkassatsiya', 'Inkassatsiya', 'seyf'], ['zalog', 'Zaloglar', 'qalqon'], ['hisobot', 'Smena hisoboti', 'hujjat'],
    ...(rahbar ? [['tarix', 'Smenalar tarixi', 'tarix']] : [])]
  const ichki = {
    zakazlar: { joriy: zakazlarBolim, tanla: (b) => { setZakazlarBolim(b); setZakazId(null) }, royxat: [['royxat', "Ro'yxat"], ['bandlik', 'Bandlik kalendari']] },
    katalog: { joriy: katalogBolim, tanla: setKatalogBolim, royxat: [['liboslar', 'Liboslar'], ['aksessuarlar', 'Aksessuarlar']] },
    mijozlar: { joriy: mijozlarBolim, tanla: setMijozlarBolim, royxat: [['mijozlar', 'Mijozlar'], ['salonchilar', 'Salonchilar']] },
    kassa: { joriy: kassaBolim, tanla: setKassaBolim, royxat: kassaRoyxat },
    hisobotlar: { joriy: hisobotlarBolim, tanla: setHisobotlarBolim, royxat: HISOBOT_ROYXAT },
  }[sahifa]
  // Chap paneldagi guruhsiz bo'lim menyulari (Kassa, Hisobot); Sozlama — guruhlangan, alohida
  const navTekis = {
    kassa: { nomi: 'Kassa', royxat: kassaRoyxat, joriy: kassaBolim, tanla: setKassaBolim },
    ...(rahbar ? { hisobotlar: { nomi: 'Hisobot', royxat: HISOBOT_ROYXAT, joriy: hisobotlarBolim, tanla: setHisobotlarBolim } } : {}),
  }[navRejim]
  const tabBar = [['bosh', 'Dashboard'], ['zakazlar', 'Zakazlar'], ['kassa', 'Kassa']]
  // Qo'ng'iroqcha ro'yxati: har biri bosilganda aynan kerakli bo'limni ochadi
  const t = xabarD?.tasdiq_kutmoqda, og = xabarD?.ogohlantirishlar
  const xabarlar = !xabarD ? [] : [
    t.chegirmalar > 0 && { matn: `${t.chegirmalar} ta chegirma so'rovi qaror kutmoqda`, soni: t.chegirmalar, bolim: 'bosh', tur: 'vaqt' },
    t.liboslar > 0 && { matn: `${t.liboslar} ta yangi libos tasdiq kutmoqda`, soni: t.liboslar, bolim: 'katalog:liboslar', tur: 'vaqt' },
    t.xarajatlar > 0 && { matn: `${t.xarajatlar} ta xarajat tasdiq kutmoqda`, soni: t.xarajatlar, bolim: 'hisobotlar:xarajat', tur: 'vaqt' },
    xabarD.bugun.kechikkan > 0 && { matn: `${xabarD.bugun.kechikkan} ta kechikkan qaytarish`, soni: xabarD.bugun.kechikkan, bolim: 'bosh', tur: 'qarz' },
    og.kassa_farqi !== 0 && { matn: `Kassa farqi (${og.kassa_farqi_sana}): ${som(og.kassa_farqi)}`, soni: 1, bolim: 'kassa:tarix', tur: 'qarz' },
    og.tannarxsiz_liboslar > 0 && { matn: `${og.tannarxsiz_liboslar} ta libosning tannarxi kiritilmagan`, soni: 1, bolim: 'katalog', tur: 'vaqt' },
    og.saqlanayotgan_zaloglar > 0 && { matn: `${og.saqlanayotgan_zaloglar} ta hujjat/tillo zalog saqlanmoqda`, soni: 1, bolim: 'kassa:zalog', tur: 'yopildi' },
    og.tugayotgan_promokodlar > 0 && { matn: `${og.tugayotgan_promokodlar} ta promokod muddati 7 kun ichida tugaydi`, soni: 1, bolim: 'sozlamalar:promokod', tur: 'yopildi' },
  ].filter(Boolean)
  const hozir = new Date()
  const KUN = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba']
  const OY = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
  const soat = hozir.getHours()
  const panelNomi = sahifa === 'bosh' ? `${soat < 11 ? 'Xayrli tong' : soat < 18 ? 'Xayrli kun' : 'Xayrli kech'}, ${xodim.ism}`
    : Object.fromEntries(bolimlar)[sahifa]
  const panelIzoh = sahifa === 'bosh' ? `${KUN[hozir.getDay()]}, ${hozir.getDate()}-${OY[hozir.getMonth()]}` : null
  // Boshlash ro'yxati: ixcham progress karta — bajarilganlar soni va faqat qolgan qadamlar
  const bajarilgan = bosh?.qadamlar.filter((q) => q.bajarildi).length || 0
  const boshlashPanel = rahbar && bosh?.korsatilsin && (
    <section className="blok boshlash">
      <div className="boshlash-bosh">
        <b>Salonni sozlash</b>
        <span className="malumot">{bajarilgan} / {bosh.qadamlar.length} bajarildi</span>
        <button type="button" className="havola" onClick={() => boshlashYop().then(setBosh)}>Yashirish</button>
      </div>
      <div className="progress" aria-hidden="true"><i style={{ '--foiz': `${(bajarilgan / bosh.qadamlar.length) * 100}%` }} /></div>
      <ul className="boshlash-qadamlar">
        {bosh.qadamlar.map((q) => (
          <li key={q.kalit} className={q.bajarildi ? 'bajarildi' : ''}>
            <button type="button" onClick={() => setSahifa(q.bolim)} disabled={q.bajarildi}>
              <NavIkona nom={q.bajarildi ? 'bajarildi' : 'doira'} className="tugma-ikon" />
              <span>{q.nomi}</span>
              {!q.bajarildi && <NavIkona nom="ong" className="tugma-ikon oxirgi" />}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
  const almashtir = () => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setXodim(null) }
  const harf = (xodim.ism || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="ilova">
      <PlatformaFon bezak={false} />
      <Shapka ochiq={menyu} onMenyu={() => setMenyu(!menyu)}>
        {/* Telefon shapkasi; keng ekranda xodim chap panel pastida */}
        <span className="xodim-chip"><i aria-hidden="true">{harf}</i></span>
        <button className="ikkinchi kichik" onClick={almashtir}>Almashtirish</button>
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
        <UstkiPanel sarlavha={panelNomi} izoh={panelIzoh} xodim={xodim} rahbar={rahbar} xabarlar={xabarlar}
          onBolim={setSahifa} onAlmashtir={almashtir}
          onQidir={(q) => { setQidiruv({ q, n: Date.now() }); setZakazlarBolim('royxat'); setSahifa('zakazlar') }} />
        {ichki && ichki.royxat.length > 1 && !(sahifa === 'zakazlar' && zakazId) && (
          <div className={`ichki-segment${sahifa === 'hisobotlar' || sahifa === 'kassa' ? ' faqat-telefon' : ''}`} role="tablist">
            {ichki.royxat.map(([id, nomi]) => (
              <button key={id} type="button" role="tab" aria-selected={ichki.joriy === id} className={ichki.joriy === id ? 'faol' : ''}
                onClick={() => ichki.tanla(id)}>{nomi}</button>
            ))}
          </div>
        )}
        {sahifa === 'bosh' && (
          <BoshEkran rahbar={rahbar} onZakaz={zakaz} onKassa={() => setSahifa('kassa')} boshlash={boshlashPanel}
            yuqori={rahbar && <Dashbord />} tasdiqSoni={t} onBolim={setSahifa} />
        )}
        {sahifa === 'zakazlar' && (zakazlarBolim === 'bandlik' && !zakazId
          ? <Kalendar onZakaz={zakaz} />
          : <Zakazlar key={qidiruv?.n} tanlangan={zakazId} onTanla={setZakazId} onYangi={() => setSahifa('yangi')} boshQ={qidiruv?.q} />)}
        {sahifa === 'mijozlar' && <Mijozlar rahbar={rahbar} onZakaz={zakaz} bolim={mijozlarBolim} />}
        {sahifa === 'katalog' && <Katalog rahbar={rahbar} bolim={katalogBolim} />}
        {sahifa === 'kassa' && (
          <Kassa rahbar={rahbar} bolim={kassaBolim} onBolim={setKassaBolim} tolovZakaz={tolovZakaz}
            yangiZakaz={<YangiZakaz onTayyor={zakaz}
              onTolov={(id) => { setTolovZakaz({ id, n: Date.now() }); setKassaBolim('tolov'); window.scrollTo(0, 0) }} />} />
        )}
        {sahifa === 'hisobotlar' && rahbar && <Hisobotlar bolim={hisobotlarBolim} />}
        {sahifa === 'sozlamalar' && rahbar && <Sozlamalar menId={xodim.id} bolim={sozlamaBolim} onBolim={setSozlamaBolim} />}
      </main>
      {/* Telefon: pastki panel — eng ko'p ishlatiladigan bo'limlar, qolgani «Ko'proq» menyusida */}
      <nav className="tab-bar" aria-label="Asosiy bo'limlar">
        {tabBar.slice(0, 2).map(([k, nom]) => (
          <button key={k} type="button" className={sahifa === k ? 'faol' : ''} onClick={() => setSahifa(k)}><NavIkona nom={k} /><span>{nom}</span></button>
        ))}
        <button type="button" className="tab-qoshish" aria-label="Yangi zakaz" onClick={() => setSahifa('yangi')}><NavIkona nom="yangi" /></button>
        {tabBar.slice(2).map(([k, nom]) => (
          <button key={k} type="button" className={sahifa === k ? 'faol' : ''} onClick={() => setSahifa(k)}><NavIkona nom={k} /><span>{nom}</span></button>
        ))}
        <button type="button" className={menyu ? 'faol' : ''} aria-expanded={menyu} onClick={() => setMenyu(!menyu)}><NavIkona nom="koproq" /><span>Ko'proq</span></button>
      </nav>
      {uxlayapti && (
        <Tasdiq sarlavha="Davom etyapsizmi?" tugma="Ha, davom etaman" xavfli={false}
          matn="30 soniyadan keyin xavfsizlik uchun tizimdan chiqiladi. Yarim to'ldirilgan zakaz qoralama sifatida saqlanadi."
          onYop={() => setUxlayapti(false)} onTasdiq={() => setUxlayapti(false)} />
      )}
      {menyu && <div className="menyu-parda" onClick={() => setMenyu(false)} />}
      {/* Chap panel (planshet va kompyuter) / telefonda chapdan chiqadigan menyu — doim bir xil asosiy bo'limlar */}
      <nav className={`pastki ${menyu ? 'ochiq' : ''}`} aria-label="Bo'limlar">
        <div className="nav-brend">
          <svg viewBox="-60 -40 640 640" aria-hidden="true"><path d={BELGI_D} fill="currentColor" /></svg>
          <span className="nav-brend-matn"><b>LIBOSA</b>{xodim.salon && <small>{xodim.salon}</small>}</span>
        </div>
        {navTekis ? (
          <div className="nav-asosiy nav-sozlama">
            <button type="button" className="nav-orqaga" onClick={() => setNavRejim(null)}>
              <NavIkona nom="chap" /><span className="nav-nom">Asosiy</span>
            </button>
            <p className="nav-bolim-nom">{navTekis.nomi}</p>
            {navTekis.royxat.map(([id, nomi, ikon]) => (
              <button key={id} type="button" className={sahifa === navRejim && navTekis.joriy === id ? 'faol' : undefined}
                aria-current={sahifa === navRejim && navTekis.joriy === id ? 'page' : undefined}
                onClick={() => { navTekis.tanla(id); setSahifaXom(navRejim); setMenyu(false); window.scrollTo(0, 0) }}>
                <NavIkona nom={ikon} /><span className="nav-nom">{nomi}</span>
              </button>
            ))}
          </div>
        ) : navRejim === 'sozlamalar' && rahbar ? (
          <div className="nav-asosiy nav-sozlama">
            <button type="button" className="nav-orqaga" onClick={() => setNavRejim(null)}>
              <NavIkona nom="chap" /><span className="nav-nom">Asosiy</span>
            </button>
            <p className="nav-bolim-nom">Sozlama</p>
            {GURUHLAR.map((g) => {
              const ochiq = sozlamaGuruh === g.nomi
              return (
                <div key={g.nomi} className={`nav-guruh${ochiq ? ' ochiq' : ''}`}>
                  <button type="button" className="nav-guruh-tugma" aria-expanded={ochiq} onClick={() => setSozlamaGuruh(ochiq ? null : g.nomi)}>
                    <NavIkona nom={g.ikon} /><span className="nav-nom">{g.nomi}</span><NavIkona nom="ong" className="tugma-ikon nav-chevron" />
                  </button>
                  {ochiq && (
                    <div className="nav-guruh-ichi">
                      {SOZLAMA_BOLIMLAR.filter((b) => b.guruh === g.nomi).map((b) => (
                        <button key={b.id} type="button" className={sahifa === 'sozlamalar' && sozlamaBolim === b.id ? 'faol' : undefined}
                          aria-current={sahifa === 'sozlamalar' && sozlamaBolim === b.id ? 'page' : undefined}
                          onClick={() => { setSozlamaBolim(b.id); setSahifaXom('sozlamalar'); setMenyu(false); window.scrollTo(0, 0) }}>
                          <NavIkona nom={b.ikon} /><span className="nav-nom">{b.nomi}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
        <div className="nav-asosiy">
            {bolimlar.map(([k, nom]) => (
              <button key={k} type="button" className={sahifa === k ? 'faol' : undefined} aria-label={nom}
                aria-current={sahifa === k ? 'page' : undefined} onClick={() => setSahifa(k)}>
                <NavIkona nom={k} /><span className="nav-nom">{nom}</span>
              </button>
            ))}
          </div>
        )}
      </nav>
      </>)}
    </div>
  )
}
