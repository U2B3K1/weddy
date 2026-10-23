// Kalendar uchun sana yordamchilari. Hammasi mahalliy vaqtda: toISOString UTC ga o'tkazib, kunni siljitadi.
export const OYLAR = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr']
// Hafta dushanbadan boshlanadi
export const HAFTA = [['Du', 'Dushanba'], ['Se', 'Seshanba'], ['Ch', 'Chorshanba'], ['Pa', 'Payshanba'], ['Ju', 'Juma'], ['Sh', 'Shanba'], ['Ya', 'Yakshanba']]
// Date.getDay(): 0 = yakshanba → dushanbadan boshlangan ustun raqami
export const ustun = (y, m, d) => (new Date(y, m, d).getDay() + 6) % 7

export const iso = (y, m, d) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
export const isoOch = (s) => { const [y, m, d] = s.split('-').map(Number); return { y, m: m - 1, d } }
const sanadan = (t) => iso(t.getFullYear(), t.getMonth(), t.getDate())
export const bugunIso = () => sanadan(new Date())

// new Date(y, m + 1, 0) — oyning oxirgi kuni; kabisa yilini Date o'zi hisobga oladi
export const oyKunlari = (y, m) => new Date(y, m + 1, 0).getDate()
export const kunQosh = (s, n) => { const { y, m, d } = isoOch(s); return sanadan(new Date(y, m, d + n)) }
export const oyQosh = ({ y, m }, n) => { const t = new Date(y, m + n, 1); return { y: t.getFullYear(), m: t.getMonth() } }
export const oylarFarqi = (a, b) => (b.y - a.y) * 12 + (b.m - a.m)
export const kunlarSoni = (a, b) => {
  const x = isoOch(a), y = isoOch(b)
  return Math.round((Date.UTC(y.y, y.m, y.d) - Date.UTC(x.y, x.m, x.d)) / 86400000)
}

// Oyning haftalari: har qator 7 katak, oy tashqarisidagi kataklar — null (4–6 qator chiqadi)
export const haftalar = (y, m) => {
  const katak = [...Array(ustun(y, m, 1)).fill(null), ...Array.from({ length: oyKunlari(y, m) }, (_, i) => iso(y, m, i + 1))]
  while (katak.length % 7) katak.push(null)
  return Array.from({ length: katak.length / 7 }, (_, i) => katak.slice(i * 7, i * 7 + 7))
}
