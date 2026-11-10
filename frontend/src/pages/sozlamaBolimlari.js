// Sozlama bo'limlari: chap paneldagi Sozlama menyusi (App) va telefondagi ochiladigan menyu (Sozlamalar) uchun yagona ro'yxat.
// Guruhlar mazmun bo'yicha (B-36): zakaz qoidalari, narx, liboslar, salon va xodimlar (kassa, filial, rekvizit), ko'rinish
// va xabarlar, xavfsizlik. Avval «Ko'rinish va xabarlar» ichida libos ruxsatlari va artikul, «Narx» ichida bonus turardi.
// «Bron va garov» — avvalgi «Bron va bandlik» va «Garov turlari» (1–3 maydonli ikki bo'lim) birlashgan.
// `izoh` — «Barcha sozlamalar» umumiy ko'rinishidagi qisqa tavsif.
// `sozlar` — sahifa tepasidagi qidiruv uchun kalit so'zlar (bo'lim nomida yo'q, lekin ichida bor narsalar).
export const SOZLAMA_BOLIMLAR = [
  { id: 'bandlik', izoh: "Bron muddati, tozalash kunlari, garov turlari", ikon: 'kalendar', nomi: 'Bron va garov', guruh: 'Zakaz qoidalari', sozlar: 'bufer tozalash avanssiz bron soat qulf daqiqa garov zalog pul hujjat tillo' },
  { id: 'kechikish', izoh: "Libosni kechiktirgan mijozga kunlik jarima", ikon: 'soat', nomi: 'Kechikish jarimasi', guruh: 'Zakaz qoidalari', sozlar: 'jarima kunlik qaytmagan eslatma vaqt' },
  { id: 'qaytarish', izoh: "Bekor qilinganda avansning qancha qismi qaytadi", ikon: 'qaytar', nomi: 'Avans qaytarish', guruh: 'Zakaz qoidalari', sozlar: 'bekor qilish foiz qoida' },
  { id: 'shartnoma', izoh: "Shartnomaga qo'shiladigan bandlar", ikon: 'hujjat', nomi: 'Shartnoma bandlari', guruh: 'Zakaz qoidalari', sozlar: 'band shart hujjat' },
  { id: 'mavsumiy', izoh: "To'y mavsumida narxga ustama", ikon: 'quyosh', nomi: 'Mavsumiy narx', guruh: 'Narx va chegirma', sozlar: 'ustama mavsum hafta kunlari' },
  { id: 'chegirmalar', izoh: "Sotuvchi bir bosishda beradigan chegirmalar", ikon: 'foiz', nomi: 'Tayyor chegirmalar', guruh: 'Narx va chegirma', sozlar: 'chegirma foiz' },
  { id: 'promokod', izoh: "Salonchi va aksiya kodlari", ikon: 'yorliq', nomi: 'Promokodlar', guruh: 'Narx va chegirma', sozlar: 'kod salonchi kodi' },
  { id: 'katalog', izoh: "Sotuvchi libos qo'sha oladimi, manekin", ikon: 'katalog', nomi: "Libos qo'shish va manekin", guruh: 'Liboslar', sozlar: "tasdiq sotuvchi qo'shadi manekin aksessuar ruxsat" },
  { id: 'artikul', izoh: "Libos artikulining prefiksi va raqami", ikon: 'raqam', nomi: 'Libos artikuli', guruh: 'Liboslar', sozlar: 'prefiks avtomatik raqam' },
  { id: 'xodimlar', izoh: "PIN, rol va Telegram", ikon: 'mijozlar', nomi: 'Xodimlar', guruh: 'Salon va xodimlar', sozlar: 'pin rol telegram sotuvchi kassir rahbar' },
  { id: 'bonus', izoh: "Sotuvchiga foizli mukofot", ikon: 'sovga', nomi: 'Sotuvchi bonusi', guruh: 'Salon va xodimlar', sozlar: 'foiz mukofot' },
  { id: 'kassa', izoh: "Kim pul qabul qiladi, terminal va o'tkazma", ikon: 'kassa', nomi: 'Kassa', guruh: 'Salon va xodimlar', sozlar: "kassir o'tkazma terminal sverka naqdsiz" },
  { id: 'filiallar', izoh: "Filial va alohida kassa", ikon: 'joy', nomi: 'Filiallar', guruh: 'Salon va xodimlar', sozlar: 'filial manzil alohida kassa' },
  { id: 'rekvizitlar', izoh: "Yuridik nom, manzil, telefon", ikon: 'bino', nomi: 'Rekvizitlar', guruh: 'Salon va xodimlar', sozlar: 'stir yuridik nom manzil telefon' },
  { id: 'dashbord', izoh: "Dashboard ko'rsatkichlari va kunlik hisobot", ikon: 'bosh', nomi: 'Dashboard va hisobot', guruh: "Ko'rinish va xabarlar", sozlar: "kunlik hisobot telegram qoplamagan bo'sh liboslar" },
  { id: 'sms', izoh: "Mijozga SMS eslatma va kvitansiya", ikon: 'xabar', nomi: 'SMS eslatma', guruh: "Ko'rinish va xabarlar", sozlar: 'sms kvitansiya eskiz' },
  { id: 'integratsiyalar', izoh: "Telegram bot, Eskiz, Click va Payme", ikon: 'vilka', nomi: 'Integratsiyalar', guruh: "Ko'rinish va xabarlar", sozlar: 'telegram bot token eskiz click payme fiskal' },
  { id: 'qurilmalar', izoh: "Ruxsat berilgan qurilmalar va salon paroli", ikon: 'qurilma', nomi: 'Qurilmalar va parol', guruh: 'Xavfsizlik', sozlar: 'planshet ruxsat salon paroli login' },
  { id: 'yordam', izoh: "Platforma egasiga muddatli ruxsat", ikon: 'yordam', nomi: 'Texnik yordam', guruh: 'Xavfsizlik', sozlar: 'platforma ruxsat' },
  { id: 'jurnal', izoh: "Kim nimani qachon o'zgartirgan", ikon: 'tarix', nomi: 'Jurnal', guruh: 'Xavfsizlik', sozlar: "amallar kim o'zgartirdi telegram xabarlari" },
]
// Eski bo'lim nomlari (havolalar, «boshlash» ro'yxati) — birlashtirilgan bo'limga olib boradi
export const ESKI_BOLIM = { zalog: 'bandlik' }
// Guruh: nomi va chap paneldagi belgisi (tartib — ro'yxatdagi birinchi uchrashi bo'yicha)
const GURUH_IKON = { 'Zakaz qoidalari': 'zakazlar', 'Narx va chegirma': 'foiz', Liboslar: 'katalog', 'Salon va xodimlar': 'bino', "Ko'rinish va xabarlar": 'xabar', Xavfsizlik: 'qalqon' }
export const GURUHLAR = [...new Set(SOZLAMA_BOLIMLAR.map((b) => b.guruh))].map((nomi) => ({ nomi, ikon: GURUH_IKON[nomi] }))

// Qidiruv: apostrof shakllari (o' o‘ oʻ) farq qilmaydi, katta-kichik harf ham
const toza = (s) => String(s || '').toLowerCase().replace(/[‘’ʻʼ`´]/g, "'")
export const sozlamaQidir = (q) => {
  const t = toza(q).trim()
  if (!t) return []
  return SOZLAMA_BOLIMLAR.filter((b) => toza(`${b.nomi} ${b.guruh} ${b.sozlar}`).includes(t))
}
