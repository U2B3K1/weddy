import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`,
})

const QURILMA = 'weddy.qurilma_token'
const TOKEN = 'weddy.token'
const XODIM = 'weddy.xodim'
const OFLAYN = 'weddy.oflayn'

export const saqlangan = {
  qurilma: () => localStorage.getItem(QURILMA),
  token: () => sessionStorage.getItem(TOKEN),
  qurilmaSaqla: (t) => localStorage.setItem(QURILMA, t),
  tokenSaqla: (t) => sessionStorage.setItem(TOKEN, t),
  chiqish: () => { sessionStorage.removeItem(TOKEN); sessionStorage.removeItem(XODIM) },
  // oflaynda sahifa yangilansa sessiyani tiklash uchun (faqat shu tab ichida)
  xodimSaqla: (x) => sessionStorage.setItem(XODIM, JSON.stringify(x)),
  xodim: () => { try { return JSON.parse(sessionStorage.getItem(XODIM)) } catch { return null } },
  qurilmaOchir: () => {
    localStorage.removeItem(QURILMA)
    localStorage.removeItem(OFLAYN)
    sessionStorage.removeItem(TOKEN)
    sessionStorage.removeItem(XODIM)
  },
}

api.interceptors.request.use((cfg) => {
  const q = saqlangan.qurilma()
  const t = saqlangan.token()
  if (q) cfg.headers['X-Device-Token'] = q
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

// Tarmoq holati: javob kelmasa (server yoki internet yo'q) ilova oflayn rejimga o'tadi (7-bo'lim).
export const tarmoqXatosi = (e) => !e.response
api.interceptors.response.use(
  (r) => { window.dispatchEvent(new Event('weddy-onlayn')); return r },
  (e) => { if (tarmoqXatosi(e)) window.dispatchEvent(new Event('weddy-oflayn')); return Promise.reject(e) },
)

// Oflayn kesh: bugungi/ertangi bronlar, telefonlar va saqlanayotgan zaloglar. Qurilma salondan chiqarilsa o'chadi.
export const oflaynKesh = {
  saqla: (d) => { try { localStorage.setItem(OFLAYN, JSON.stringify(d)) } catch { /* joy yo'q bo'lsa keshsiz ishlaydi */ } },
  oqi: () => { try { return JSON.parse(localStorage.getItem(OFLAYN)) } catch { return null } },
}
export const oflaynToplam = () => api.get('/oflayn-toplam/').then((r) => r.data)

// Rahbar qurilmalar ro'yxatida ajrata olishi uchun: «Chrome · Windows · 09.10 12:50» kabi nom (FT-22.2)
const qurilmaNomi = () => {
  const ua = navigator.userAgent
  const brauzer = BRAUZERLAR.find(([re]) => re.test(ua))?.[1] || 'Brauzer'  // model qatoridagi brauzer bilan bir xil
  const tizim = /iPad/.test(ua) ? 'iPad' : /iPhone/.test(ua) ? 'iPhone' : /Android/.test(ua) ? 'Android'
    : /Windows/.test(ua) ? 'Windows' : /Mac/.test(ua) ? 'Mac' : 'qurilma'
  const d = new Date()
  const ikki = (n) => String(n).padStart(2, '0')
  return `${brauzer} · ${tizim} · ${ikki(d.getDate())}.${ikki(d.getMonth() + 1)} ${ikki(d.getHours())}:${ikki(d.getMinutes())}`
}

// Qurilma modeli: «Samsung SM-T505 · Android 13 · Chrome 130». Chromium brauzerlari aniq modelni
// userAgentData orqali beradi (oddiy userAgent da Android modeli endi «K» deb yashiriladi); qolganlari userAgent dan.
// Tartib muhim: Edge/Opera/Yandex userAgent ida «Chrome/…» ham bor (va undan oldin turadi), shuning uchun
// bitta umumiy regex hammasini Chrome deb olardi. iOS dagi Chrome/Firefox/Edge nomini boshqacha yozadi.
// Samsung plansheti standart brauzeri (SamsungBrowser) ham «Chrome/…» deb yozadi.
const BRAUZERLAR = [[/(?:EdgA?|EdgiOS)\/(\d+)/, 'Edge'], [/(?:OPR|OPT)\/(\d+)/, 'Opera'], [/YaBrowser\/(\d+)/, 'Yandex'],
  [/SamsungBrowser\/(\d+)/, 'Samsung Internet'], [/(?:Firefox|FxiOS)\/(\d+)/, 'Firefox'], [/(?:Chrome|CriOS)\/(\d+)/, 'Chrome'], [/Version\/(\d+(?:\.\d+)?).*Safari\//, 'Safari']]
const brauzerVersiyasi = (ua) => {
  for (const [re, nomi] of BRAUZERLAR) {
    const m = ua.match(re)
    if (m) return `${nomi} ${m[1]}`
  }
  return ''
}
const BRENDLAR = [[/^SM-/, 'Samsung'], [/^Pixel/, ''], [/^(Redmi|POCO|Mi )/i, 'Xiaomi'], [/^(CPH|RMX)\d/, 'Oppo/Realme']]
let modelKesh
export const qurilmaModeli = async () => {
  if (modelKesh !== undefined) return modelKesh
  const ua = navigator.userAgent
  let model = ''
  let tizim = ''
  try {
    const h = await navigator.userAgentData?.getHighEntropyValues(['model', 'platformVersion'])
    if (h) {
      model = h.model || ''
      const v = h.platformVersion || ''
      tizim = h.platform === 'Windows' ? (parseInt(v, 10) >= 13 ? 'Windows 11' : 'Windows 10')
        : h.platform === 'Android' ? `Android ${parseInt(v, 10) || ''}`.trim()
          : h.platform === 'macOS' ? `macOS ${v.split('.').slice(0, 2).join('.')}`.trim() : h.platform || ''
    }
  } catch { /* brauzer bermasa — userAgent dan */ }
  const ios = ua.match(/OS (\d+)_(\d+)/)
  const ipad = /iPad/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)  // iPadOS o'zini Mac deb ko'rsatadi
  if (ipad) { model = 'iPad'; tizim = ios ? `iPadOS ${ios[1]}.${ios[2]}` : 'iPadOS' }
  else if (/iPhone/.test(ua)) { model = 'iPhone'; tizim = ios ? `iOS ${ios[1]}.${ios[2]}` : 'iOS' }
  if (!tizim) {
    const a = ua.match(/Android ([\d.]+);\s*([^;)]+)/)
    // «K» — Chrome yashirgan model; «Mobile/Tablet» — Firefox modelni umuman bermaydi
    if (a) { tizim = `Android ${parseInt(a[1], 10)}`; if (!model && !/^(K|Mobile|Tablet)$/.test(a[2].trim())) model = a[2].replace(/ Build\/.*/, '').trim() }
    else tizim = /Windows/.test(ua) ? 'Windows' : /Mac/.test(ua) ? 'Mac' : /Linux/.test(ua) ? 'Linux' : ''
  }
  const brend = BRENDLAR.find(([re]) => re.test(model))
  if (brend?.[1]) model = `${brend[1]} ${model}`
  const brauzer = brauzerVersiyasi(ua)
  modelKesh = [model, tizim, brauzer].filter(Boolean).join(' · ').slice(0, 200)
  return modelKesh
}

export const salonLogin = async (login, parol) =>
  api.post('/auth/salon-login/', { login, parol, qurilma_nomi: qurilmaNomi(), qurilma_modeli: await qurilmaModeli() })
    .then((r) => r.data)
export const xodimlar = () => api.get('/auth/xodimlar/').then((r) => r.data)
// Ruxsat kutayotgan qurilma: Telegram tasdiq havolasi va Telegram ulamagan rahbarlar (FT-22.2)
export const qurilmaTasdiqHolati = () => api.get('/auth/qurilma-tasdiq/').then((r) => r.data)
export const qurilmaPinTasdiq = (xodim_id, pin) => api.post('/auth/qurilma-tasdiq/', { xodim_id, pin }).then((r) => r.data)
// Rahbar Telegram ulagan bo'lsa server 202 {telegram_kod_kerak} qaytaradi; kod bilan qayta yuboriladi (FT-22.3)
export const pinLogin = async (xodim_id, pin, telegram_kod) =>
  api.post('/auth/pin-login/', { xodim_id, pin, telegram_kod, qurilma_modeli: await qurilmaModeli() }).then((r) => r.data)
export const pinTekshir = (pin) => api.post('/auth/pin-tekshir/', { pin }).then((r) => r.data)
export const arizaYubor = (body) => api.post('/auth/ariza/', body).then((r) => r.data)
export const me = () => api.get('/auth/me/').then((r) => r.data)
export const boshLiboslar = (dan, gacha, bandlarniKorsat = false, q = '') =>
  api
    .get('/bronlar/bosh/', {
      params: { dan, gacha, bandlarni_korsat: bandlarniKorsat ? 1 : undefined, q: q || undefined },
    })
    .then((r) => r.data)

export const qulf = (libos, dan, gacha) =>
  api.post('/bronlar/qulf/', { libos, dan, gacha }).then((r) => r.data)
export const mijozQidir = (telefon) =>
  api.get('/mijozlar/qidirish/', { params: { telefon } }).then((r) => r.data)
export const zakazYarat = (body) => api.post('/zakazlar/', body).then((r) => r.data)

const get = (url, params) => api.get(url, { params }).then((r) => r.data)
const post = (url, body) => api.post(url, body || {}).then((r) => r.data)

export const boshEkran = () => get('/bosh-ekran/')
export const zakazlarRoyxat = (params) => get('/zakazlar/royxat/', params)
export const zakazTafsilot = (id) => get(`/zakazlar/${id}/`)
export const zakazTarixi = (id) => get(`/zakazlar/${id}/tarix/`)
export const tolovQabul = (body) => post('/kassa/tolovlar/', body)
export const berish = (id, zaloglar) => post(`/zakazlar/${id}/berish/`, { zaloglar })
export const qaytarish = (id, body) => post(`/zakazlar/${id}/qaytarish/`, body)
export const qarzTolash = (id, summa) => post(`/zakazlar/${id}/qarz-tolash/`, { summa })
export const bekorQilish = (id, body) => post(`/zakazlar/${id}/bekor/`, body)
export const sanaKochirish = (id, body) => post(`/zakazlar/${id}/sana-kochirish/`, body)
export const chegirmaSora = (id, body) => post(`/zakazlar/${id}/chegirma/`, body)
export const zakazAksessuarQosh = (id, aksessuar, soni = 1) => post(`/zakazlar/${id}/aksessuar/`, { aksessuar, soni })
export const zakazAksessuarOchir = (id, qatorId) => api.delete(`/zakazlar/${id}/aksessuar/${qatorId}/`).then((r) => r.data)
export const tayyorChegirmalar =() => get('/tayyor-chegirmalar/')
export const tozalandi = (libosId) => post(`/liboslar/${libosId}/tozalandi/`)

export const smenaHolati = () => get('/kassa/smena/')
export const smenaOchish = (boshlangich_qoldiq) => post('/kassa/smena/ochish/', { boshlangich_qoldiq })
export const smenaQoshilish = () => post('/kassa/smena/qoshilish/')
export const smenaChiqish = (summa) => post('/kassa/smena/chiqish/', { summa })
export const smenaYopish = (summa, izoh) => post('/kassa/smena/yopish/', { summa, izoh })

export const dashbord = (davr = 'oy', filial) => get('/dashbord/', { davr, filial: filial || undefined })
export const chegirmaSorovlari = () => get('/chegirma-sorovlari/')
export const chegirmaQaror = (id, body) => post(`/chegirma-sorovlari/${id}/qaror/`, body)
export const xarajatlar = (params) => get('/xarajatlar/', params)
export const xarajatYarat = (body) => post('/xarajatlar/', body)
export const xarajatQaror = (id, qaror, summa) => post(`/xarajatlar/${id}/qaror/`, { qaror, ...(summa ? { summa } : {}) })
export const xarajatModdalari = (hammasi) => get('/xarajat-moddalari/', hammasi ? { hammasi: 1 } : undefined)
export const moddaQosh = (body) => post('/xarajat-moddalari/', body)
export const moddaOzgartir = (id, body) => patch(`/xarajat-moddalari/${id}/`, body)
export const doimiyXarajatlar = () => get('/doimiy-xarajatlar/')
export const doimiyXarajatQosh = (body) => post('/doimiy-xarajatlar/', body)
export const doimiyXarajatOzgartir = (id, body) => patch(`/doimiy-xarajatlar/${id}/`, body)
export const kassaZaloglar = () => get('/kassa/zaloglar/')
export const zalogBelgila = (body) => post('/kassa/zaloglar/', body)
export const smenalar = () => get('/kassa/smenalar/')
export const smenaTuzat = (id, body) => patch(`/kassa/smenalar/${id}/`, body)
export const pnl = (oy, filial) => get('/hisobotlar/pnl/', { oy, filial: filial || undefined })
export const oyniYop = (oy) => post('/hisobotlar/oyni-yopish/', { oy })
export const oyniOch = (oy) => api.delete('/hisobotlar/oyni-yopish/', { params: { oy } }).then((r) => r.data)

const patch = (url, body) => api.patch(url, body).then((r) => r.data)
export const liboslar = (params) => get('/liboslar/', params)
export const libosYarat = (body) => post('/liboslar/', body)
export const libosTasdiq = (id, body) => post(`/liboslar/${id}/tasdiq/`, body)
export const libosOzgartir = (id, body) => patch(`/liboslar/${id}/`, body)
export const libosTafsilot = (id) => get(`/liboslar/${id}/`)
export const rasmYukla = (libosId, fayl) => {
  const fd = new FormData()
  fd.append('rasm', fayl)
  return api.post(`/liboslar/${libosId}/rasmlar/`, fd).then((r) => r.data)
}
export const rasmOchir = (id) => api.delete(`/rasmlar/${id}/`)
export const boshAksessuarlar = (dan, gacha) => get('/bronlar/bosh-aksessuarlar/', { dan, gacha })
export const aksessuarlar = () => get('/aksessuarlar/')
export const aksessuarTafsilot = (id) => get(`/aksessuarlar/${id}/`)
export const aksessuarYarat = (body) => post('/aksessuarlar/', body)
export const aksessuarTasdiq = (id, body) => post(`/aksessuarlar/${id}/tasdiq/`, body)
export const aksessuarOzgartir = (id, body) => patch(`/aksessuarlar/${id}/`, body)
export const donalarQosh = (id, soni) => post(`/aksessuarlar/${id}/donalar/`, { soni })
export const donaHolati = (id, holat) => patch(`/donalar/${id}/`, { holat })
export const tamirlar = (libosId) => get(`/liboslar/${libosId}/tamir/`)
export const tamirBer = (libosId, body) => post(`/liboslar/${libosId}/tamir/`, body)
export const tamirTugat = (id, body) => post(`/tamir/${id}/tugatish/`, body)
export const sozlamalar = () => get('/sozlamalar/')
export const sozlamaSaqla = (body) => patch('/sozlamalar/', body)
export const xodimlarBoshqaruv = () => get('/xodimlar-boshqaruv/')
export const xodimQosh = (body) => post('/xodimlar-boshqaruv/', body)
export const xodimOzgartir = (id, body) => patch(`/xodimlar-boshqaruv/${id}/`, body)
export const xodimTelegramUlash = (id) => post(`/xodimlar-boshqaruv/${id}/telegram-ulash/`)
export const hujjat = (zakazId, tur) => get(`/zakazlar/${zakazId}/hujjat/`, { tur })
export const salonRekvizit = () => get('/salon/')
export const salonRekvizitSaqla = (body) => patch('/salon/', body)
export const kalendar = (dan, gacha) => get('/bronlar/kalendar/', { dan, gacha })
export const smsJurnali = () => get('/sms/')
export const integratsiyalar = () => get('/integratsiyalar/')
export const integratsiyaSaqla = (body) => patch('/integratsiyalar/', body)
export const tolovHavola = (zakazId, summa) => get(`/zakazlar/${zakazId}/tolov-havola/`, { summa: summa || undefined })
export const filiallar = (hammasi) => get('/filiallar/', hammasi ? { hammasi: 1 } : undefined)
export const filialQosh = (body) => post('/filiallar/', body)
export const filialOzgartir = (id, body) => patch(`/filiallar/${id}/`, body)
export const qurilmaFilial = (id, filial) => patch(`/qurilmalar/${id}/`, { filial })
export const qurilmalar = () => get('/qurilmalar/')
export const qurilmaTasdiq = (id) => patch(`/qurilmalar/${id}/`, { tasdiq: true })
export const qurilmaOchirish = (id) => api.delete(`/qurilmalar/${id}/`)
export const salonParol = (parol) => post('/salon/parol/', { parol })
export const yordamRuxsati = () => get('/yordam-ruxsati/')
export const yordamBer = (soat) => post('/yordam-ruxsati/', { soat })
export const yordamBekor = () => api.delete('/yordam-ruxsati/').then((r) => r.data)
export const boshlash = () => get('/boshlash/')
export const boshlashYop = () => post('/boshlash/')
export const mijozlar = (params) => get('/mijozlar/', params)
export const mijozKarta = (id) => get(`/mijozlar/${id}/`)
export const mijozOzgartir = (id, body) => patch(`/mijozlar/${id}/`, body)
export const mijozQoraRoyxat = (id, qora_royxat, sabab = '') => post(`/mijozlar/${id}/qora-royxat/`, { qora_royxat, sabab })
export const boglandim = (zakazId, tur, izoh = '') => post(`/zakazlar/${zakazId}/boglandim/`, { tur, izoh })
export const qarzdorlar = () => get('/hisobotlar/qarzdorlar/')
export const telegramHolat = () => get('/telegram/')
export const telegramUlash = () => post('/telegram/')
export const telegramUzish = () => api.delete('/telegram/').then((r) => r.data)
export const hisobotlarRoyxati = () => get('/hisobotlar/royxat/')
export const hisobot = (kalit, dan, gacha, filtr = {}) => get(`/hisobotlar/h/${kalit}/`, { dan, gacha, ...filtr })
export const oylikQator = (filial) => get('/hisobotlar/oylik/', { filial: filial || undefined })
export const bankHolati = (oy) => get('/hisobotlar/bank/', { oy })
export const bankKirit = (body) => post('/hisobotlar/bank/', body)
export const salonchilar = (params) => get('/salonchilar/', params)
export const salonchiQosh = (body) => post('/salonchilar/', body)
export const salonchiOzgartir = (id, body) => patch(`/salonchilar/${id}/`, body)
export const zakazSalonchi = (zakazId, salonchi) => post(`/zakazlar/${zakazId}/salonchi/`, { salonchi })
export const kategoriyalar = () => get('/kategoriyalar/')
export const mavsumiyNarxlar = () => get('/mavsumiy-narxlar/')
export const mavsumiyQosh = (body) => post('/mavsumiy-narxlar/', body)
export const mavsumiyOzgartir = (id, body) => patch(`/mavsumiy-narxlar/${id}/`, body)
export const mavsumiyOchir = (id) => api.delete(`/mavsumiy-narxlar/${id}/`).then((r) => r.data)
export const ustamaFoiz = (sana) => get('/narx/ustama/', { sana })
export const hisobotTafsilot = (nom, kalit, dan, gacha, filtrlar = {}) =>
  get(`/hisobotlar/h/${nom}/tafsilot/`, { kalit, dan, gacha, ...filtrlar })
export const pnlTafsilot = (oy, qator, filial) => get('/hisobotlar/pnl/tafsilot/', { oy, qator, filial: filial || undefined })
export const bonusHisobot = (oy) => get('/hisobotlar/bonus/', { oy })
export const primerkaBelgila = (zakazId, vaqt) => post(`/zakazlar/${zakazId}/primerka/`, { vaqt })
export const primerkaOzgartir = (id, body) => patch(`/primerkalar/${id}/`, body)
export const rasmFonsiz = (rasmId) => post(`/rasmlar/${rasmId}/fonsiz/`)
export const donaFilial = (donaId, filial) => patch(`/donalar/${donaId}/`, { filial })
export const donaTamirga = (donaId, body) => post(`/donalar/${donaId}/tamir/`, body)
export const donaTamirTugat = (tamirId, body) => post(`/dona-tamir/${tamirId}/tugatish/`, body)
export const aksessuarManekinYukla = (id, fayl) => {
  const fd = new FormData()
  fd.append('rasm', fayl)
  return api.post(`/aksessuarlar/${id}/manekin/`, fd).then((r) => r.data)
}
export const aksessuarManekinSaqla = (id, body) => patch(`/aksessuarlar/${id}/manekin/`, body)
export const aksessuarManekinOchir = (id) => api.delete(`/aksessuarlar/${id}/manekin/`).then((r) => r.data)
export const manekinSaqla = (libosId, body) => patch(`/liboslar/${libosId}/manekin/`, body)
export const promokodlar = () => get('/promokodlar/')
export const promokodYarat = (body) => post('/promokodlar/', body)
export const promokodOzgartir = (id, body) => patch(`/promokodlar/${id}/`, body)
export const promokodQolla = (zakazId, kod) => post(`/zakazlar/${zakazId}/promokod/`, { kod })
export const promokodOlibTashla = (zakazId) => api.delete(`/zakazlar/${zakazId}/promokod/`).then((r) => r.data)
export const kategoriyaYarat = (body) => post('/kategoriyalar/', body)
export const kategoriyaOzgartir = (id, body) => patch(`/kategoriyalar/${id}/`, body)
export const kategoriyaOchir = (id) => api.delete(`/kategoriyalar/${id}/`).then((r) => r.data)
export const tayyorChegirmalarHammasi = () => get('/tayyor-chegirmalar/', { hammasi: 1 })
export const tayyorChegirmaQosh = (body) => post('/tayyor-chegirmalar/', body)
export const tayyorChegirmaOzgartir = (id, body) => patch(`/tayyor-chegirmalar/${id}/`, body)
export const xarajatTuzat = (id, body) => patch(`/xarajatlar/${id}/`, body)
export const xarajatBekor = (id) => api.delete(`/xarajatlar/${id}/`).then((r) => r.data)
export const libosAlmashtirish = (zakazId, body) => post(`/zakazlar/${zakazId}/libos-almashtirish/`, body)

export const xatoMatni = (e, standart = 'Xatolik yuz berdi.') => {
  const d = e.response?.data
  if (!d || typeof d !== 'object') return standart // masalan, server 500 da HTML qaytarsa
  if (typeof d.detail === 'string') return d.detail
  return Object.values(d).flat().join(' ') || standart
}

// Brauzerdan qat'i nazar bir xil ko'rinish: 2 400 000 so'm (hujjatlardagi matn bilan mos)
export const som = (n) => `${String(Math.round(Number(n || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} so'm`

export default api
