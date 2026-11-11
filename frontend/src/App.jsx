import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { BoshAmal } from './components/BoshJoy'
import { BoshJoyi } from './components/boshJoyi'
import { bildirishnomalar, boshlash, boshlashYop, dashbord, me, oflaynKesh, oflaynToplam, profilRasmOchir, profilRasmYukla, saqlangan, som, tarmoqXatosi, xatoMatni } from './api'
import BoshEkran from './pages/BoshEkran'
import Tasdiq from './components/Tasdiq'
import NavIkona from './components/NavIkona'
import Shapka from './components/Shapka'
import UstkiPanel from './components/UstkiPanel'
import FilialTanlov from './components/FilialTanlov'
import XodimMenyu from './components/XodimMenyu'
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

const HARAKATSIZLIK_MS = 10 * 60 * 1000
const OGOHLANTIRISH_MS = 30 * 1000 // chiqishdan 30 soniya oldin «Davom etyapsizmi?»
const OFLAYN_KESH_MS = 5 * 60 * 1000
const KORILGAN = 'weddy.korilgan_xabarlar'  // xodim qo'ng'iroqchasida ochilgan chegirma natijalari (shu qurilmada)
const korilganOqi = () => { try { return JSON.parse(localStorage.getItem(KORILGAN)) || [] } catch { return [] } }

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
  const [sozlamaBolim, setSozlamaBolim] = useState('bosh')  // 'bosh' — «Barcha sozlamalar» (guruhlar kartalar to'rida)
  // Chap panel rejimi: Kassa, Hisobotlar yoki Sozlama bosilganda panel o'sha bo'lim menyusiga aylanadi; «Asosiy» — asosiy menyuga qaytish
  const [navRejim, setNavRejim] = useState(null)
  // Sozlama ochiq bo'lsa keng ekranda (≥1200, matnli chap panel) chap panel Sozlama bo'limlari ro'yxatiga aylanadi (foydalanuvchi
  // qarori, 2026-11-10). «‹ Asosiy» — asosiy menyuni ko'rsatadi (boshqa bo'limga o'tilganda yana avvalgidek).
  // 768–1199 px da panel 80 px'lik belgilar — ro'yxat sig'maydi, u sahifaning o'zida qoladi.
  const [kengPanel, setKengPanel] = useState(() => window.matchMedia('(min-width: 1200px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(min-width: 1200px)'); const h = (e) => setKengPanel(e.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])
  const [asosiyMenyu, setAsosiyMenyu] = useState(false)
  const [sozlamaYonJoy, setSozlamaYonJoy] = useState(null)  // chap paneldagi joy — Sozlamalar ro'yxatini portal orqali chizadi
  // Ichki bo'limlar faqat sahifa tepasidagi segmentda chiqadi; chap panel doim asosiy bo'limlarni ko'rsatadi.
  const [zakazlarBolim, setZakazlarBolim] = useState('royxat')
  // Dashboard «Tezkor amallar» → «Libos qo'shish»: Liboslar ochilib qo'shish oynasi ko'rinadi (n — har bosishda yangi)
  const [libosQosh, setLibosQosh] = useState(false)
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
  const [filialKalit, setFilialKalit] = useState(0) // yuqori panelda filial almashtirilganda sahifa qayta yuklanadi
  // Bo'lim boshidagi joylar (xulosa va o'ngdagi tugma) — sahifalar BoshXulosa/BoshAmal bilan to'ldiradi
  const [xulosaJoy, setXulosaJoy] = useState(null)
  const [amalJoy, setAmalJoy] = useState(null)
  const boshJoyi = useMemo(() => ({ xulosa: xulosaJoy, amal: amalJoy, sozlamaYon: sozlamaYonJoy }), [xulosaJoy, amalJoy, sozlamaYonJoy])
  // «Davom etyapsizmi?» — chiqish vaqti (ms) yoki null; faollikRef — taymerni qayta boshlash (oynadagi «Davom etish»)
  const [uxlayapti, setUxlayapti] = useState(null)
  const faollikRef = useRef(null)
  // Yuqori paneldagi global qidiruv Zakazlar ro'yxatiga uzatiladi (n — bir xil matnni qayta qidirish uchun)
  const [qidiruv, setQidiruv] = useState(null)
  // Qo'ng'iroqchadan aniq ro'yxatga (A-09): Zakazlar holat filtri («kechikkan») yoki bosh sahifa tabi («tasdiq»)
  const [zakazFiltr, setZakazFiltr] = useState(null)
  const [boshTab, setBoshTab] = useState(null)
  // R2: Yangi zakaz oldindan to'ldirilgan holda (kalendar bo'sh katagi, mijoz kartasi) — YangiZakaz `boshlangich`:
  // { n, dan?, gacha?, libos_id?, mijoz?: { telefon, fio } }; n — har safar yangi
  const [yangiBosh, setYangiBosh] = useState(null)
  // Kassadan zakaz kartasiga: { id, amal } — amal 'berish' bo'lsa karta berish formasiga suriladi
  const [zakazAmal, setZakazAmal] = useState(null)
  // Xodim (sotuvchi) qo'ng'iroqchasi: chegirma natijasi, topshirilgan pul, bugungi qo'ng'iroqlar — har 2 daqiqada
  const [xodimXabar, setXodimXabar] = useState(null)
  const [korilgan, setKorilgan] = useState(korilganOqi)
  // Rahbar bildirishnomalari (qo'ng'iroqcha): qaror kutayotganlar va ogohlantirishlar — har 2 daqiqada
  const [xabarD, setXabarD] = useState(null)
  useEffect(() => {
    if (xodim?.rol !== 'rahbar') return undefined
    const yukla = () => dashbord('oy', '').then(setXabarD).catch(() => {})
    yukla()
    const t = setInterval(yukla, 120000)
    return () => clearInterval(t)
  }, [xodim?.rol])

  // Shaxsiy xabarlar va «Bugungi ishlar» (olib ketadi, qaytaradi, kechikkan, qo'ng'iroq, rahbarga — qarzdorlar) — hamma xodimga
  useEffect(() => {
    if (!xodim) return undefined
    const yukla = () => bildirishnomalar().then(setXodimXabar).catch(() => {})
    yukla()
    const t = setInterval(yukla, 120000)
    return () => clearInterval(t)
  }, [xodim])

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
    // kirgach manzilda «#kirish» qolmaydi (chiqishda qayta qo'yiladi); tarixga yangi qadam qo'shilmaydi
    if (window.location.hash === '#kirish') window.history.replaceState(null, '', window.location.pathname + window.location.search)
    let t, t0
    const chiq = () => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setUxlayapti(null); setXodim(null) }
    const qayta = (e) => {
      // oyna tugmalari («Chiqish» / «Davom etish») o'z ishini qiladi — bosish oynani oldindan yopib yubormasin
      if (e?.target?.closest?.('[role="alertdialog"][aria-label="Davom etyapsizmi?"]')) return
      clearTimeout(t); clearTimeout(t0); setUxlayapti(null)
      t0 = setTimeout(() => setUxlayapti(Date.now() + OGOHLANTIRISH_MS), HARAKATSIZLIK_MS - OGOHLANTIRISH_MS)
      t = setTimeout(chiq, HARAKATSIZLIK_MS)
    }
    faollikRef.current = qayta
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

  // Telefonda tepadagi segment suriladi: tanlangan bo'lim yarim kesilib qolmasin (sahifa vertikal surilmaydi)
  const segmentRef = useRef(null)
  useEffect(() => {
    const s = segmentRef.current, b = s?.querySelector('.faol')
    if (!b) return
    const d = b.getBoundingClientRect().left - s.getBoundingClientRect().left
    s.scrollLeft += d - (s.clientWidth - b.offsetWidth) / 2
  }, [sahifa, zakazlarBolim, katalogBolim, mijozlarBolim, kassaBolim, hisobotlarBolim])

  if (!tayyor) return null
  if (platforma) return (
    <>
      <PlatformaFon nurli />
      <Platforma onOrqaga={() => { window.location.hash = ''; setPlatforma(false) }} />
    </>
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
  // C-12: obuna tugagan — yangi zakaz ochiladigan tugmalar o'chiq (sababi sarlavhada); mavjud zakaz bilan ishlash ochiq
  const faqatKorish = xodim.salon_holati === 'faqat_korish'
  const YOPIQ_SABAB = "Obuna muddati tugagan: yangi zakaz ochib bo'lmaydi"
  // Bo'limga o'tish. «kassa:zalog» ko'rinishida ichki bo'lim ham beriladi (ogohlantirish aynan kerakli joyni ochsin).
  // Eski nomlar ham qabul qilinadi: «dashbord» — bosh sahifa, «kalendar» — zakazlardagi bandlik
  // (backend «boshlash» ro'yxati shu nomlarni yuborishi mumkin).
  const setSahifa = (manzil) => {
    let [k, ich] = manzil.split(':')
    if (k === 'dashbord') k = 'bosh'
    if (k === 'yangi') { k = 'kassa'; ich = 'yangi' }  // «Yangi zakaz» endi Kassa ichida
    // «zakazlar:kechikkan» — ro'yxat shu filtr bilan; «bosh:tasdiq» — bosh sahifadagi shu tab (A-09)
    if (k === 'zakazlar') {
      const filtr = ich && !['royxat', 'bandlik'].includes(ich) ? ich : null
      setZakazFiltr((eski) => (filtr ? { holat: filtr, n: (eski?.n || 0) + 1 } : null))
      if (filtr) ich = 'royxat'
    }
    if (k === 'hisobotlar' && ich === 'grafik') ich = 'pnl'  // B-14: «Grafik» bo'limi yo'q — 12 oylik grafik P&L ostida
    if (k === 'bosh') { const tab = ich; setBoshTab((eski) => (tab ? { tab, n: (eski?.n || 0) + 1 } : null)); ich = undefined }
    if (ich) {
      ({ zakazlar: setZakazlarBolim, katalog: setKatalogBolim, mijozlar: setMijozlarBolim, kassa: setKassaBolim,
        hisobotlar: setHisobotlarBolim, sozlamalar: setSozlamaBolim })[k]?.(ich)
    }
    if (k === 'kalendar') { k = 'zakazlar'; setZakazlarBolim('bandlik') }
    if (k === 'zakazlar') setZakazId(null)
    // Shisha uslubi (Ndiz): Kassa va Hisobotlar bo'limlari — sahifa tepasidagi ikonkali tablar; Sozlama bo'limlari — keng ekranda
    // chap panelda (Sozlamalar.jsx ro'yxati portal orqali), torroqda sahifaning o'zida
    setNavRejim(null)
    setAsosiyMenyu(false)
    setSahifaXom(k)
    setLibosQosh(false)  // Dashboard'dan «Libos qo'shish» belgisi faqat o'sha o'tishga tegishli
    setMenyu(false)
    window.scrollTo(0, 0)
  }
  // Zakaz kartasi ochiladi; «‹» bosilganda qaysi ichki bo'limdan (ro'yxat yoki bandlik) kelgan bo'lsa, o'shanga qaytadi
  const zakaz = (id) => { setZakazId(id); if (sahifa !== 'zakazlar') setZakazlarBolim('royxat'); setNavRejim(null); setSahifaXom('zakazlar'); window.scrollTo(0, 0) }
  // Kassa → «Libosni berish →»: karta ochilib, berish formasiga suriladi
  const zakazOch = (id, amal) => { setZakazAmal(amal ? { id, amal } : null); zakaz(id) }
  // Kalendar bo'sh katagi / mijoz kartasi → oldindan to'ldirilgan Yangi zakaz
  const yangiZakazga = (bosh) => { setYangiBosh((eski) => ({ ...bosh, n: (eski?.n || 0) + 1 })); setSahifa('kassa:yangi') }
  // Qo'ng'iroqcha bandi: «zakaz:12» — zakaz kartasi, aks holda bo'lim; ochilgan chegirma natijasi qayta chiqmaydi
  const xabargaOt = (manzil, x) => {
    // bir martalik xabarlar (chegirma natijasi, o'tkazma kelmadi, rad etilgan xarajat) ochilgach qayta chiqmaydi
    if (/^(chegirma|kelmadi|xarajat-rad)-/.test(x?.kalit || '')) {
      const yangi = [...korilgan.filter((k) => k !== x.kalit), x.kalit].slice(-50)
      setKorilgan(yangi)
      try { localStorage.setItem(KORILGAN, JSON.stringify(yangi)) } catch { /* saqlanmasa — keyingi safar yana ko'rinadi */ }
    }
    if (manzil.startsWith('zakaz:')) zakaz(Number(manzil.slice(6)))
    else setSahifa(manzil)
  }
  // Hisobotlar bo'limlari: [id, nomi, ikonka] — chap paneldagi Hisobotlar menyusi va telefondagi segment.
  // B-14: «Grafik» olib tashlandi (Dashboard grafigini takrorlardi; 12 oylik sof foyda grafigi — «Oylik foyda» ostida).
  // QA-07: nav nomi sahifa sarlavhasi bilan bir xil — «Oylik foyda»
  const HISOBOT_ROYXAT = [['hisobot', 'Umumiy hisobot', 'hisobotlar'], ['pnl', 'Oylik foyda', 'tarozi'], ['xarajat', 'Xarajatlar', 'hamyon'],
    ['bonus', 'Sotuvchi bonusi', 'sovga'], ['bank', 'Bank solishtirish', 'bank']]
  const bolimlar = [
    ['bosh', 'Dashboard'], ['kassa', 'Kassa'], ['katalog', 'Liboslar'], ['zakazlar', 'Zakazlar'], ['mijozlar', 'Mijozlar'],
    ...(rahbar ? [['hisobotlar', 'Hisobotlar'], ['sozlamalar', 'Sozlama']] : []),
  ]

  // Ichki bo'limlar — sahifa tepasidagi segment (barcha ekranlarda bir xil joyda). Sozlama o'z menyusiga ega.
  // Kassa (POS): smena amallari (ochish, chiqish, yopish) — smena panelida; bu yerda ish ekranlari
  // «Alohida kassir» rejimida sotuvchi pul bilan ishlamaydi — faqat zakaz oladi
  const pulOladi = !(xodim.rol === 'sotuvchi' && xodim.kassa_rejimi === 'kassir')
  const kassaRoyxat = [['yangi', 'Yangi zakaz', 'yangi'], ...(pulOladi ? [['tolov', "To'lov qabul", 'kassa'], ['xarajat', 'Xarajat', 'hamyon'],
    ['inkassatsiya', 'Inkassatsiya', 'seyf'], ['zalog', 'Garovlar', 'qalqon'], ['hisobot', 'Smena hisoboti', 'hujjat']] : []),
    ...(rahbar ? [['tarix', 'Smenalar tarixi', 'tarix']] : [])]
  const ichki = {
    zakazlar: { joriy: zakazlarBolim, tanla: (b) => { setZakazlarBolim(b); setZakazId(null) }, royxat: [['royxat', "Ro'yxat"], ['bandlik', 'Bandlik kalendari']] },
    katalog: { joriy: katalogBolim, tanla: setKatalogBolim, royxat: [['liboslar', "Ro'yxat"], ['aksessuarlar', 'Aksessuarlar'], ['sanoq', 'Sanoq'], ...(rahbar ? [['yetkazib', 'Yetkazib beruvchilar']] : [])] },
    mijozlar: { joriy: mijozlarBolim, tanla: setMijozlarBolim, royxat: [['mijozlar', 'Mijozlar'], ['salonchilar', 'Salonchilar']] },
    kassa: { joriy: kassaBolim, tanla: setKassaBolim, royxat: kassaRoyxat },
    hisobotlar: { joriy: hisobotlarBolim, tanla: setHisobotlarBolim, royxat: HISOBOT_ROYXAT },
  }[sahifa]
  // Keng ekranda (≥1200) ko'p bo'limli sahifalarning ichki bo'limlari Sozlama kabi chap panelda (foydalanuvchi so'rovi, 2026-11-10):
  // Kassa, Hisobotlar, Liboslar. Zakazlar va Mijozlar (2 tadan) — tepada tab: sotuvchi ular orasida bir bosishda o'tadi.
  // «‹ Asosiy» — asosiy menyu (asosiyMenyu); boshqa bo'limga o'tilganda yana avvalgidek. Torroqda — tepadagi tablar.
  const LIBOS_IKON = { liboslar: 'katalog', aksessuarlar: 'yorliq', sanoq: 'bajarildi', yetkazib: 'bino' }
  const yonBolimlar = kengPanel ? {
    kassa: { nomi: 'Kassa', royxat: kassaRoyxat, joriy: kassaBolim, tanla: setKassaBolim },
    ...(rahbar ? { hisobotlar: { nomi: 'Hisobotlar', royxat: HISOBOT_ROYXAT, joriy: hisobotlarBolim, tanla: setHisobotlarBolim } } : {}),
    katalog: { nomi: 'Liboslar', royxat: ichki?.royxat.map(([id, nomi]) => [id, nomi, LIBOS_IKON[id]]), joriy: katalogBolim, tanla: setKatalogBolim },
  }[sahifa] || null : null
  // bitta bo'lim (masalan, kassir rejimidagi sotuvchi) — chap menyu kerak emas, tepada ham tab chiqmaydi
  const yonda = yonBolimlar?.royxat?.length > 1 ? yonBolimlar : null
  // «‹ Asosiy» bosilganda chap panelda asosiy menyu; tepadagi tablar baribir chiqmaydi (eski ko'rinish aralashmasin) —
  // asosiy menyudagi shu bo'lim (masalan, Liboslar) qayta bosilsa, ro'yxat qaytadi (Sozlama bilan bir xil)
  const navTekis = yonda && !menyu && !asosiyMenyu ? yonda : null
  // Telefon «Profil» sahifasi (maket): pastki panelda yo'q bo'limlar shu yerdan ochiladi — ular ochiq turganda ham «Profil» belgilanadi
  const profilBolimlari = bolimlar.filter(([k]) => k !== 'bosh' && k !== 'zakazlar' && !(k === 'kassa' && pulOladi) && !(k === 'mijozlar' && !pulOladi))
  const profilda = sahifa === 'profil' || profilBolimlari.some(([k]) => k === sahifa)
  const tabBar = [['bosh', 'Bosh'], ['zakazlar', 'Zakazlar'], pulOladi ? ['kassa', 'Kassa'] : ['mijozlar', 'Mijozlar']]
  // Qo'ng'iroqcha ro'yxati: har biri bosilganda aynan kerakli bo'limni ochadi
  const t = xabarD?.tasdiq_kutmoqda, og = xabarD?.ogohlantirishlar
  // Rahbarga — dashbord ma'lumotidan; sotuvchi/kassirga — /bildirishnomalar/ (R2)
  const xodimXabarlari = (xodimXabar?.xabarlar || []).filter((x) => !korilgan.includes(x.kalit)).map((x) => ({
    kalit: x.kalit, matn: x.matn, soni: x.soni,
    tur: { chegirma_tasdiq: 'ok', chegirma_rad: 'qarz', otkazma_kelmadi: 'qarz', xarajat_rad: 'qarz', kechikkan: 'qarz', qarzdor: 'qarz' }[x.tur] || 'vaqt',
    bolim: x.zakaz_id ? `zakaz:${x.zakaz_id}` : {
      topshiriq: 'kassa', xarajat_rad: 'kassa:xarajat', olib: 'bosh:olib', qaytar: 'bosh:qaytar', kechikkan: 'zakazlar:kechikkan',
      qarzdor: 'bosh:qarz' }[x.tur] || 'bosh:eslatma',
  }))
  // Rahbarga: avval qarorlar, keyin bugungi ishlar (umumiy manba — /bildirishnomalar/), oxirida ogohlantirishlar
  const xabarlar = !rahbar ? xodimXabarlari : !xabarD ? xodimXabarlari : [
    t.otkazmalar > 0 && { matn: `${t.otkazmalar} ta o'tkazma: hisobingizga kelganini tasdiqlang`, soni: t.otkazmalar, bolim: 'kassa:tolov', tur: 'vaqt' },
    og.kutayotgan_qurilmalar > 0 && { matn: `${og.kutayotgan_qurilmalar} ta yangi qurilma ruxsat kutmoqda`, soni: og.kutayotgan_qurilmalar, bolim: 'sozlamalar:qurilmalar', tur: 'vaqt' },
    ...xodimXabarlari,
    xabarD.bugun.kechikkan > 0 && og.kechikish_jarimasi_yoqilgan === false && { matn: "Kechikkan qaytarishlar bor, lekin kechikish jarimasi o'chirilgan", soni: 1, bolim: 'sozlamalar:kechikish', tur: 'vaqt' },
    og.kassa_farqi !== 0 && { matn: `Kassa farqi (${og.kassa_farqi_sana}): ${som(og.kassa_farqi)}`, soni: 1, bolim: 'kassa:tarix', tur: 'qarz' },
    og.tannarxsiz_liboslar > 0 && { matn: `${og.tannarxsiz_liboslar} ta libosning tannarxi kiritilmagan — foyda haqiqatdagidan yuqori ko'rinadi`, soni: 1, bolim: 'katalog', tur: 'vaqt' },
    og.saqlanayotgan_zaloglar > 0 && { matn: `${og.saqlanayotgan_zaloglar} ta hujjat/tillo garov saqlanmoqda`, soni: 1, bolim: 'kassa:zalog', tur: 'yopildi' },
    og.tugayotgan_promokodlar > 0 && { matn: `${og.tugayotgan_promokodlar} ta promokod muddati 7 kun ichida tugaydi`, soni: 1, bolim: 'sozlamalar:promokod', tur: 'yopildi' },
    og.telegramsiz_xodimlar > 0 && { matn: `${og.telegramsiz_xodimlar} xodim Telegramni ulamagan — xabarlar ularga bormaydi`, soni: 1, bolim: 'sozlamalar:xodimlar', tur: 'yopildi' },
  ].filter(Boolean)
  const hozir = new Date()
  const soat = hozir.getHours()
  const salom = soat < 11 ? 'Xayrli tong' : soat < 18 ? 'Xayrli kun' : 'Xayrli kech'
  // Rahbar bosh sahifasi — maketdagidek ikki qatorli salom (birinchisi och tilla)
  // Bo'lim boshi kanvasdagidek (foydalanuvchi: «har bo'limda har xil, kanvas bilan ishlanmagan»): sarlavha — ochiq tabning nomi,
  // ostida bir qatorli xulosa. `null` xulosa — sahifaning o'zi hisoblab qo'yadi (BoshXulosa: zakaz va libos sonlari).
  // Telefon (maket): Kassa ichki ekranlarining o'z sarlavhasi va izohi
  const KASSA_TELEFON = {
    tolov: ["To'lov qabul qilish", "Ijara to'lovini qabul qilish"], xarajat: ['Xarajat', 'Salon xarajatini kiritish'],
    inkassatsiya: ['Pul topshirish', 'Kassadan pul topshirish'], zalog: ['Garovlar', 'Zakazlar uchun olingan garovlar'],
    hisobot: ['Smena hisoboti', "Joriy smena bo'yicha qisqa hisobot"], tarix: ['Smenalar tarixi', 'Smenalar yakuni va farqlar'],
    yangi: ['Yangi zakaz', 'Yangi ijara zakazini yaratish'],  // pastki panelda «Zakazlar» belgilanadi (maket)
  }
  const BOSH = {
    'zakazlar:royxat': ['Zakazlar', null],
    'zakazlar:bandlik': ['Bandlik kalendari', 'Qaysi libos qachon band — bir qarashda'],
    'katalog:liboslar': ['Liboslar', null],
    'katalog:aksessuarlar': ['Aksessuarlar', "Fata, toj, taqinchoq — har dona o'z yorlig'i bilan hisobda"],
    'katalog:sanoq': ["Libos sanog'i", "Javondagini belgilang — yo'qolgan yoki zakazsiz berilgan buyum shu yerda ko'rinadi"],
    'katalog:yetkazib': ['Yetkazib beruvchilar', 'Libos va aksessuar kimdan olingan, kimga qancha qarz qoldi'],
    'mijozlar:mijozlar': ['Mijozlar', "Kim qachon to'y qiladi, kimda qoldiq yoki qarz bor"],
    'mijozlar:salonchilar': ['Salonchilar', 'Mijoz olib keladigan makiyaj ustalari va salonlar'],
    'hisobotlar:hisobot': ['Umumiy hisobot', "Egasining savollari: qaysi libos o'zini oqladi, xodimlar qanday ishladi, kim qarzdor"],
    'hisobotlar:pnl': ['Oylik foyda', "Kassa usuli: pul kirgan kuni — tushum, qaytarilgan pul — qaytarilgan kuni ayiriladi"],
    'hisobotlar:xarajat': ['Xarajatlar', "Pul qayerga ketdi — moddalar bo'yicha"],
    'hisobotlar:bonus': ['Sotuvchi bonusi', "Sotuvchilarga zakazlardan hisoblangan foizli mukofot"],
    'hisobotlar:bank': ['Bank solishtirish', "Bankka tushgan pul tizimdagi to'lovlar bilan solishtiriladi"],
    // Kassa tablari (kanvas KassaBolimShisha): sarlavha «Kassa», ostida tab nima uchunligi
    'kassa:uy': ['Kassa', 'Salon kassa va smena boshqaruvi'],
    'kassa:xarajat': ['Kassa', 'Xarajat — kassadan chiqqan pul, modda va izoh bilan'],
    'kassa:inkassatsiya': ['Kassa', 'Pul topshirish — kassadagi naqdni rahbarga yoki keyingi kassirga'],
    'kassa:zalog': ['Kassa', 'Saqlanayotgan garovlar — smena yopilishidan oldin seyf bilan solishtiring'],
    'kassa:hisobot': ['Kassa', 'Smena hisoboti — naqd pul qayerdan keldi va qayerga ketdi'],
    'kassa:tarix': ['Kassa', 'Smenalar tarixi — har smenaning yakuni, farqlar va tuzatishlar'],
    sozlamalar: ['Sozlama', 'Salon qoidalari bir marta sozlanadi — kassa, zakaz va hisobotlar shunga amal qiladi'],
  }
  const bosh2 = BOSH[ichki && !(sahifa === 'zakazlar' && zakazId) ? `${sahifa}:${ichki.joriy}` : sahifa]
  const panelNomi = sahifa === 'bosh'
    ? (rahbar ? <><span className="salom-birinchi">{salom},</span>{' '}<br />{xodim.ism}!</> : <><span className="salom-birinchi">{salom},</span> {xodim.ism}</>)
    : bosh2?.[0] || Object.fromEntries(bolimlar)[sahifa]
  const panelXulosa = bosh2?.[1] || null
  // Rahbar Dashboard'ida salomdan keyin izoh ham, «Yangi zakaz» tugmasi ham yo'q (foydalanuvchi: «kerak emas», 2026-11-09) —
  // yangi zakaz «Tezkor amallar» va Kassa orqali ochiladi
  const panelIzoh = sahifa === 'bosh'
    ? null
    : sahifa === 'kassa' && !bosh2 ? kassaRoyxat.find(([id]) => id === kassaBolim)?.[1] || null : null
  // «Salonni sozlash» — qo'ng'iroqcha menyusining tepasida ixcham: progress va qolgan qadamlar (bosh sahifada emas)
  const sozlash = rahbar && bosh?.korsatilsin && bosh.qadamlar ? {
    bajarilgan: bosh.qadamlar.filter((q) => q.bajarildi).length, jami: bosh.qadamlar.length,
    qolgan: bosh.qadamlar.filter((q) => !q.bajarildi), onQadam: setSahifa, onYashir: () => boshlashYop().then(setBosh),
  } : null
  const chiqish = () => { saqlangan.chiqish(); window.location.hash = '#kirish'; setKirish(true); setXodim(null) }
  const rolNomi = rahbar ? 'Rahbar' : xodim.rol === 'kassir' ? 'Kassir' : 'Sotuvchi'
  // Profil rasmi: yangi manzil xodim holatiga va oflayn nusxaga yoziladi (shapka va kirish ekrani shu zahoti yangilanadi)
  const rasmniYangila = (r) => { const x = { ...xodim, rasm: r.rasm }; setXodim(x); saqlangan.xodimSaqla(x) }
  const rasmYukla = (f) => profilRasmYukla(f).then(rasmniYangila).catch((e) => { throw new Error(xatoMatni(e)) })
  const rasmOchir = () => profilRasmOchir().then(rasmniYangila).catch((e) => { throw new Error(xatoMatni(e)) })

  return (
    <div className="ilova" data-nav={navRejim || undefined}>
      <PlatformaFon nurli />
      <Shapka ochiq={menyu} onMenyu={() => setMenyu(!menyu)}>
        {/* Telefon shapkasi; keng ekranda xodim chap panel pastida */}
        {/* Telefon: belgi bosilsa — xodim menyusi (profil rasmi va «Chiqish»), kompyuterdagi bilan bir xil */}
        <XodimMenyu xodim={xodim} rol={rolNomi} onChiqish={chiqish} onRasm={rasmYukla} onRasmOchir={rasmOchir} ixcham
          onKassa={() => setSahifa('kassa:hisobot')} />
      </Shapka>
      {faqatKorish && (
        <p className="ogohlantirish obuna-banner" role="status">Obuna muddati tugagan: yangi zakaz, katalog va sozlamalar yopiq. Boshlangan zakazlarni yakunlash mumkin — to'lov, berish, qaytarish va smena ishlaydi.</p>
      )}
      {xodim.obuna_qolgan_kun != null && rahbar && (
        <p className="ogohlantirish obuna-banner">
          {xodim.obuna_qolgan_kun === 0 ? 'Obuna muddati bugun tugaydi.' : `Obuna muddati ${xodim.obuna_qolgan_kun} kundan keyin tugaydi.`} Salon uzilishsiz ishlashi uchun obunani uzaytiring.
        </p>
      )}
      {xodim.obuna_ogohlantirish_kun != null && rahbar && (
        <p className="ogohlantirish obuna-banner">
          Obuna to'lovi muddati o'tgan. {xodim.obuna_ogohlantirish_kun} kundan keyin salon «faqat ko'rish» rejimiga o'tadi.
        </p>
      )}
      {!onlayn && <p className="ogohlantirish obuna-banner" role="status">Internet yo'q: faqat ko'rish rejimi. Kiritilganlar sahifada qoladi — aloqa tiklangach davom eting.</p>}
      {/* C-14: aloqa uzilsa joriy sahifa olib tashlanmaydi (forma holati yo'qolmasin) — saqlangan ma'lumot ustida chiqadi */}
      <BoshJoyi.Provider value={boshJoyi}>
      <main>
        <UstkiPanel ikon={(sahifa === 'kassa' && kassaRoyxat.find(([id]) => id === kassaBolim)?.[2]) || { bosh: 'hisobotlar', zakazlar: 'kalendar' }[sahifa] || sahifa}
          telefonNomi={sahifa === 'bosh' && rahbar ? ['Rahbar paneli', "Salon faoliyati bo'yicha asosiy ko'rsatkichlar"] : sahifa === 'kassa' ? KASSA_TELEFON[kassaBolim] || null : null}
          sarlavha={panelNomi} izoh={panelIzoh} xulosa={panelXulosa} xulosaRef={setXulosaJoy} xodim={xodim} rahbar={rahbar} xabarlar={xabarlar} sozlash={sozlash}
          qarorSoni={rahbar ? t : null} onQarorOzgardi={() => dashbord('oy', '').then(setXabarD).catch(() => {})}
          onBolim={xabargaOt} onChiqish={chiqish} onRasm={rasmYukla} onRasmOchir={rasmOchir} onKassa={() => setSahifa('kassa:hisobot')}
          onQidir={(q) => { setQidiruv({ q, n: Date.now() }); setZakazlarBolim('royxat'); setSahifa('zakazlar') }}
          onFilialOzgardi={() => setFilialKalit((k) => k + 1)} />
        {!onlayn && <section className="oflayn-qatlam" aria-label="Saqlangan ma'lumot"><Oflayn /></section>}
        {/* Kanvas: tablar chapda, bo'limning asosiy tugmasi o'ngda (sahifa BoshAmal bilan qo'yadi) */}
        <div className="bolim-qator">
          {ichki && ichki.royxat.length > 1 && !(sahifa === 'zakazlar' && zakazId) && (
            <div className={`ichki-segment${yonda ? ' faqat-telefon' : ''}`} role="tablist" ref={segmentRef}>
              {ichki.royxat.map(([id, nomi, ikon]) => (
                <button key={id} type="button" role="tab" aria-selected={ichki.joriy === id} className={ichki.joriy === id ? 'faol' : ''}
                  onClick={() => ichki.tanla(id)}>{ikon && <NavIkona nom={ikon} />}{nomi}</button>
              ))}
            </div>
          )}
          <div className="bolim-amal" ref={setAmalJoy} />
        </div>
        {sahifa === 'zakazlar' && zakazlarBolim === 'bandlik' && !zakazId && (
          <BoshAmal><button type="button" className="bosh-tugma" disabled={faqatKorish} title={faqatKorish ? YOPIQ_SABAB : undefined}
            onClick={() => yangiZakazga()}><NavIkona nom="qosh" className="tugma-ikon" />Yangi zakaz</button></BoshAmal>
        )}
        {/* Filial almashganda sahifa ma'lumoti (kassa, filtrlar) yangi filial bo'yicha qayta yuklanadi */}
        <Fragment key={filialKalit}>
        {sahifa === 'bosh' && (
          <BoshEkran key={boshTab?.n} rahbar={rahbar} pulOladi={pulOladi} onZakaz={zakaz} onKassa={() => setSahifa('kassa')} tab={boshTab}
            yuqori={rahbar ? (orta) => <Dashbord orta={orta} onZakaz={zakaz}
              onBolim={(b) => { if (b === 'libos:qosh') { setSahifa('katalog:liboslar'); setLibosQosh(true) } else setSahifa(b) }} /> : null} tasdiqSoni={t} onBolim={setSahifa} />
        )}
        {sahifa === 'zakazlar' && (zakazlarBolim === 'bandlik' && !zakazId
          ? <Kalendar onZakaz={zakaz} onYangi={faqatKorish ? undefined : yangiZakazga} />
          : <Zakazlar key={`${qidiruv?.n}-${zakazFiltr?.n}`} tanlangan={zakazId} onTanla={setZakazId} onYangi={() => setSahifa('yangi')}
            yangiYopiq={faqatKorish ? YOPIQ_SABAB : null} onBandlik={() => setZakazlarBolim('bandlik')}
            amal={zakazAmal?.id === zakazId ? zakazAmal.amal : null}
            onKassa={() => setSahifa('kassa')} boshQ={zakazFiltr ? undefined : qidiruv?.q} boshHolat={zakazFiltr?.holat} />)}
        {sahifa === 'profil' && (
          <div className="profil-sahifa">
            <section className="blok tb-karta profil-karta" aria-label="Profil">
              <span className="profil-rasm">{xodim.rasm ? <img src={xodim.rasm} alt="" /> : <b aria-hidden="true">{(xodim.ism || '?').trim().charAt(0).toUpperCase()}</b>}</span>
              <span className="profil-matn"><b>{xodim.ism}</b><small>{rolNomi}</small><FilialTanlov rahbar={false} /></span>
            </section>
            {profilBolimlari.map(([k, nom]) => (
              <button key={k} type="button" className="blok tb-karta tb-qator" onClick={() => setSahifa(k)}>
                <NavIkona nom={k} /><span>{nom}</span><NavIkona nom="ong" className="nav-ikon tb-ong" />
              </button>
            ))}
            <div className="profil-chiqish">
              <XodimMenyu xodim={xodim} rol={rolNomi} onChiqish={chiqish} onRasm={rasmYukla} onRasmOchir={rasmOchir} yon onKassa={() => setSahifa('kassa:hisobot')} />
            </div>
          </div>
        )}
        {sahifa === 'mijozlar' && <Mijozlar rahbar={rahbar} onZakaz={zakaz} bolim={mijozlarBolim} onYangiZakaz={faqatKorish ? undefined : (mijoz) => yangiZakazga({ mijoz })} />}
        {sahifa === 'katalog' && <Katalog rahbar={rahbar} bolim={katalogBolim} onZakaz={zakaz} yangiOch={libosQosh} onYangiYopildi={setLibosQosh} />}
        {sahifa === 'kassa' && (
          <Kassa rahbar={rahbar} bolim={kassaBolim} onBolim={setKassaBolim} tolovZakaz={tolovZakaz} onZakaz={zakazOch}
            yangiZakaz={<YangiZakaz onTayyor={zakaz} boshlangich={yangiBosh}
              onTolov={(id) => { setTolovZakaz({ id, n: Date.now() }); setKassaBolim('tolov'); window.scrollTo(0, 0) }} />} />
        )}
        {sahifa === 'hisobotlar' && rahbar && <Hisobotlar bolim={hisobotlarBolim} onZakaz={zakaz} onBolim={setSahifa} />}
        {sahifa === 'sozlamalar' && rahbar && <Sozlamalar menId={xodim.id} bolim={sozlamaBolim} onBolim={(b) => setSahifa(`sozlamalar:${b}`)} />}
        </Fragment>
      </main>
      {/* Telefon: pastki panel — eng ko'p ishlatiladigan bo'limlar, qolgani «Ko'proq» menyusida */}
      {/* Telefon pastki paneli (maket): Bosh, Zakazlar, Kassa, Profil. «Yangi zakaz» — Zakazlar sahifasidagi katta tugma va
          Kassa bo'limi; qolgan bo'limlar (Liboslar, Mijozlar, Hisobotlar, Sozlama) — «Profil» ochadigan menyuda */}
      <nav className="tab-bar" aria-label="Asosiy bo'limlar">
        {tabBar.map(([k, nom]) => k === 'kassa' ? (
          <button key={k} type="button" className={sahifa === 'kassa' && kassaBolim !== 'yangi' ? 'faol' : ''}
            onClick={() => setSahifa('kassa:uy')}><NavIkona nom={k} /><span>{nom}</span></button>
        ) : (
          <button key={k} type="button" className={sahifa === k || (k === 'zakazlar' && sahifa === 'kassa' && kassaBolim === 'yangi') ? 'faol' : ''} onClick={() => setSahifa(k)}>
            <NavIkona nom={k === 'bosh' ? 'uy' : k === 'zakazlar' ? 'kalendar' : k} /><span>{nom}</span></button>
        ))}
        <button type="button" className={profilda ? 'faol' : ''} onClick={() => setSahifa('profil')}><NavIkona nom="profil" /><span>Profil</span></button>
      </nav>
      {uxlayapti && (
        <DavomOynasi muddat={uxlayapti} onDavom={() => faollikRef.current?.()} onChiqish={() => { setUxlayapti(null); chiqish() }} />
      )}
      {menyu && <div className="menyu-parda" onClick={() => setMenyu(false)} />}
      {/* Chap panel (planshet va kompyuter) / telefonda chapdan chiqadigan menyu — doim bir xil asosiy bo'limlar */}
      <nav className={`pastki ${menyu ? 'ochiq' : ''}`} aria-label="Bo'limlar">
        <div className="nav-brend">
          <svg viewBox="-60 -40 640 640" aria-hidden="true"><path d={BELGI_D} fill="currentColor" /></svg>
          <span className="nav-brend-matn"><b>LIBOSA</b></span>{/* salon nomi bu yerda ortiqcha (foydalanuvchi) — xodim menyusida bor */}
        </div>
        {navTekis ? (
          <div className="nav-asosiy nav-sozlama">
            <button type="button" className="nav-orqaga" onClick={() => setAsosiyMenyu(true)}>
              <NavIkona nom="chap" /><span className="nav-nom">Asosiy</span>
            </button>
            <p className="nav-bolim-nom">{navTekis.nomi}</p>
            {/* tepadagi tablar o'rnida — vertikal tablar (sahifa mazmunini almashtiradi) */}
            <div className="nav-tablar" role="tablist" aria-orientation="vertical" aria-label={`${navTekis.nomi} bo'limlari`}>
              {navTekis.royxat.map(([id, nomi, ikon]) => (
                <button key={id} type="button" role="tab" aria-selected={navTekis.joriy === id} className={navTekis.joriy === id ? 'faol' : undefined}
                  disabled={faqatKorish && id === 'yangi'} title={faqatKorish && id === 'yangi' ? YOPIQ_SABAB : undefined}
                  onClick={() => { navTekis.tanla(id); window.scrollTo(0, 0) }}>
                  <NavIkona nom={ikon || 'doira'} /><span className="nav-nom">{nomi}</span>
                </button>
              ))}
            </div>
          </div>
        ) : sahifa === 'sozlamalar' && rahbar && kengPanel && !menyu && !asosiyMenyu ? (
          <div className="nav-asosiy nav-sozlama">
            <button type="button" className="nav-orqaga" onClick={() => setAsosiyMenyu(true)}>
              <NavIkona nom="chap" /><span className="nav-nom">Asosiy</span>
            </button>
            <p className="nav-bolim-nom">Sozlama</p>
            {/* Sozlamalar.jsx shu yerga o'z ro'yxatini chizadi (e'tibor nuqtalari, faol bo'lim, guruh nomlari bilan) */}
            <div className="nav-sozlama-joy" ref={setSozlamaYonJoy} />
          </div>
        ) : (
        <div className="nav-asosiy">
            {bolimlar.map(([k, nom]) => (
              <button key={k} type="button" aria-label={nom}
                className={[sahifa === k && 'faol', tabBar.some(([x]) => x === k) && 'tabda'].filter(Boolean).join(' ') || undefined}
                aria-current={sahifa === k ? 'page' : undefined} onClick={() => setSahifa(k === 'kassa' && pulOladi && sahifa !== 'kassa' ? 'kassa:tolov' : k)}>{/* Kassa ichidan («‹ Asosiy» dan keyin) bosilsa ochiq bo'lim o'zgarmaydi */}
                <NavIkona nom={k} /><span className="nav-nom">{nom}</span>
              </button>
            ))}
          </div>
        )}
        {/* Shisha uslubi: chap panel pastida faqat «Chiqish» — keng ekranda (CSS); xodim belgisi va menyusi yuqori panelda */}
        <div className="yon-past">
          <XodimMenyu xodim={xodim} rol={rolNomi} onChiqish={chiqish} onRasm={rasmYukla} onRasmOchir={rasmOchir} yon
            onKassa={() => setSahifa('kassa:hisobot')} />
        </div>
      </nav>
      </BoshJoyi.Provider>
    </div>
  )
}

// C-23: harakatsizlikdan oldin — «Chiqish» (darhol) yoki «Ha, davom etaman» (fokus shunda), jonli sanoq bilan.
// C-13: qoralama endi xodimga bog'langan (boshqa xodimga ochilmaydi); nima saqlanishi aniq aytiladi.
function DavomOynasi({ muddat, onDavom, onChiqish }) {
  const [hozir, setHozir] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setHozir(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const soniya = Math.max(0, Math.ceil((muddat - hozir) / 1000))
  return (
    <Tasdiq sarlavha="Davom etyapsizmi?" tugma="Ha, davom etaman" xavfli={false} fokus="tasdiq"
      bekorMatn="Chiqish" onBekor={onChiqish} onYop={onDavom} onTasdiq={onDavom}
      matn={<><b>{soniya} soniyadan</b> keyin xavfsizlik uchun tizimdan chiqiladi. Boshlangan yangi zakazning sanasi va mijozi siz uchun saqlanadi — qayta kirganingizda davom etasiz, libosni qayta tanlaysiz.</>} />
  )
}
