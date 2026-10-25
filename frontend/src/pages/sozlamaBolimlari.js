// Sozlama bo'limlari: chap paneldagi Sozlama menyusi (App) va telefondagi ochiladigan menyu (Sozlamalar) uchun yagona ro'yxat.
// Bo'limlar mavzu bo'yicha guruhlangan — 19 ta bo'limni bitta uzun ro'yxatdan qidirish shart emas.
export const SOZLAMA_BOLIMLAR = [
  { id: 'bandlik', ikon: 'kalendar', nomi: 'Bron va bandlik', guruh: 'Zakaz va bron' },
  { id: 'zalog', ikon: 'qalqon', nomi: 'Zalog turlari', guruh: 'Zakaz va bron' },
  { id: 'kechikish', ikon: 'soat', nomi: 'Kechikish jarimasi', guruh: 'Zakaz va bron' },
  { id: 'qaytarish', ikon: 'qaytar', nomi: 'Avans qaytarish', guruh: 'Zakaz va bron' },
  { id: 'primerka', ikon: 'chizgich', nomi: 'Primerka va baho', guruh: 'Zakaz va bron' },
  { id: 'shartnoma', ikon: 'hujjat', nomi: 'Shartnoma bandlari', guruh: 'Zakaz va bron' },
  { id: 'mavsumiy', ikon: 'quyosh', nomi: 'Mavsumiy narx', guruh: 'Narx va chegirma' },
  { id: 'promokod', ikon: 'yorliq', nomi: 'Promokodlar', guruh: 'Narx va chegirma' },
  { id: 'chegirmalar', ikon: 'foiz', nomi: 'Tayyor chegirmalar', guruh: 'Narx va chegirma' },
  { id: 'bonus', ikon: 'sovga', nomi: 'Sotuvchi bonusi', guruh: 'Narx va chegirma' },
  { id: 'katalog', ikon: 'katalog', nomi: 'Katalog', guruh: "Ko'rinish va xabarlar" },
  { id: 'dashbord', ikon: 'bosh', nomi: 'Dashboard va hisobot', guruh: "Ko'rinish va xabarlar" },
  { id: 'sms', ikon: 'xabar', nomi: 'SMS eslatma', guruh: "Ko'rinish va xabarlar" },
  { id: 'integratsiyalar', ikon: 'vilka', nomi: 'Integratsiyalar', guruh: "Ko'rinish va xabarlar" },
  { id: 'xodimlar', ikon: 'mijozlar', nomi: 'Xodimlar', guruh: 'Salon' },
  { id: 'filiallar', ikon: 'joy', nomi: 'Filiallar', guruh: 'Salon' },
  { id: 'rekvizitlar', ikon: 'bino', nomi: 'Rekvizitlar', guruh: 'Salon' },
  { id: 'qurilmalar', ikon: 'qurilma', nomi: 'Qurilmalar', guruh: 'Salon' },
  { id: 'yordam', ikon: 'yordam', nomi: 'Texnik yordam', guruh: 'Salon' },
  { id: 'jurnal', ikon: 'tarix', nomi: 'Jurnal', guruh: 'Salon' },
]
// Guruh: nomi va chap paneldagi belgisi (tartib — ro'yxatdagi birinchi uchrashi bo'yicha)
const GURUH_IKON = { 'Zakaz va bron': 'zakazlar', 'Narx va chegirma': 'foiz', "Ko'rinish va xabarlar": 'xabar', Salon: 'bino' }
export const GURUHLAR = [...new Set(SOZLAMA_BOLIMLAR.map((b) => b.guruh))].map((nomi) => ({ nomi, ikon: GURUH_IKON[nomi] }))
