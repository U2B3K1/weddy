import { oflaynKesh, som } from '../api'

const HOLAT = {
  vaqtinchalik: 'vaqtinchalik bron', chegirma_kutilmoqda: 'chegirma kutilmoqda', bron: 'bron', berildi: 'mijozda',
}

// «07.11.2026 10:24» — brauzer tilidan qat'i nazar (C-22)
const ikki = (n) => String(n).padStart(2, '0')
const vaqtMatni = (s) => { const d = new Date(s); return `${ikki(d.getDate())}.${ikki(d.getMonth() + 1)}.${d.getFullYear()} ${ikki(d.getHours())}:${ikki(d.getMinutes())}` }

// 7-bo'lim, S28: internet uzilganda faqat ko'rish rejimi. Yangi zakaz yaratilmaydi (ikki marta bron xavfi) —
// buning uchun qog'oz blanka va mobil internet zaxirasi ishlatiladi.
export default function Oflayn() {
  const d = oflaynKesh.oqi()
  if (!d) {
    return <p className="ogohlantirish">Internet yo'q va qurilmada saqlangan ma'lumot topilmadi. Aloqa tiklangach sahifa o'zi yangilanadi.</p>
  }
  // `qoldiq` — olib ketishda olinadigan pul (qog'oz kvitansiya uchun); eski keshda bo'lmasa ko'rsatilmaydi
  const guruh = (sarlavha, royxat, qoldiqBilan = false) => (
    <section className="blok">
      <h3>{sarlavha} ({royxat.length})</h3>
      {royxat.length === 0 && <p className="malumot">Yo'q</p>}
      {royxat.map((b) => (
        <p key={`${sarlavha}-${b.raqam}`} className="qator-matn">
          <b>#{b.raqam}</b> {b.mijoz || '—'} · <a href={`tel:${b.telefon}`}>{b.telefon}</a><br />
          {b.liboslar.join(', ')}{b.aksessuarlar.length > 0 ? ` + ${b.aksessuarlar.join(', ')}` : ''} · {HOLAT[b.holat] || b.holat}
          {qoldiqBilan && b.qoldiq != null && <> · <b>{b.qoldiq > 0 ? `qoldiq ${som(b.qoldiq)}` : "to'langan"}</b></>}
        </p>
      ))}
    </section>
  )
  const b = d.bronlar
  return (
    <div className="stack">
      <p className="malumot">Ma'lumot {vaqtMatni(d.olingan)} holatiga ko'ra. Yangi zakaz uchun qog'oz blankadan foydalaning.</p>
      {guruh('Kechikkan qaytarishlar', b.filter((x) => x.holat === 'berildi' && x.qaytarish < d.bugun))}
      {guruh('Bugun olib ketiladi', b.filter((x) => x.olib_ketish === d.bugun && x.holat !== 'berildi'), true)}
      {guruh('Bugun qaytariladi', b.filter((x) => x.qaytarish === d.bugun && x.holat === 'berildi'))}
      {guruh('Ertaga olib ketiladi', b.filter((x) => x.olib_ketish === d.ertaga && x.holat !== 'berildi'), true)}
      {guruh('Ertaga qaytariladi', b.filter((x) => x.qaytarish === d.ertaga && x.holat === 'berildi'))}
      <section className="blok">
        <h3>Saqlanayotgan zaloglar ({d.zaloglar.length})</h3>
        {d.zaloglar.length === 0 && <p className="malumot">Yo'q</p>}
        {d.zaloglar.map((g) => (
          <p key={g.yorliq} className="qator-matn">
            <b>{g.yorliq}</b> {g.turi} · zakaz #{g.zakaz} · {g.mijoz || '—'} · <a href={`tel:${g.telefon}`}>{g.telefon}</a>
          </p>
        ))}
      </section>
    </div>
  )
}
