import { oflaynKesh } from '../api'

const HOLAT = {
  vaqtinchalik: 'vaqtinchalik bron', chegirma_kutilmoqda: 'chegirma kutilmoqda', bron: 'bron', berildi: 'mijozda',
}

// 7-bo'lim, S28: internet uzilganda faqat ko'rish rejimi. Yangi zakaz yaratilmaydi (ikki marta bron xavfi) —
// buning uchun qog'oz blanka va mobil internet zaxirasi ishlatiladi.
export default function Oflayn() {
  const d = oflaynKesh.oqi()
  if (!d) {
    return <p className="ogohlantirish">Internet yo'q va qurilmada saqlangan ma'lumot topilmadi. Aloqa tiklangach sahifa o'zi yangilanadi.</p>
  }
  const guruh = (sarlavha, royxat) => (
    <section className="blok">
      <h3>{sarlavha} ({royxat.length})</h3>
      {royxat.length === 0 && <p className="malumot">Yo'q</p>}
      {royxat.map((b) => (
        <p key={`${sarlavha}-${b.raqam}`} className="qator-matn">
          <b>#{b.raqam}</b> {b.mijoz || '—'} · <a href={`tel:${b.telefon}`}>{b.telefon}</a><br />
          {b.liboslar.join(', ')}{b.aksessuarlar.length > 0 ? ` + ${b.aksessuarlar.join(', ')}` : ''} · {HOLAT[b.holat] || b.holat}
        </p>
      ))}
    </section>
  )
  const b = d.bronlar
  return (
    <div className="stack">
      <p className="malumot">Ma'lumot {new Date(d.olingan).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })} holatiga ko'ra. Yangi zakaz uchun qog'oz blankadan foydalaning.</p>
      {guruh('Kechikkan qaytarishlar', b.filter((x) => x.holat === 'berildi' && x.qaytarish < d.bugun))}
      {guruh('Bugun olib ketiladi', b.filter((x) => x.olib_ketish === d.bugun && x.holat !== 'berildi'))}
      {guruh('Bugun qaytariladi', b.filter((x) => x.qaytarish === d.bugun && x.holat === 'berildi'))}
      {guruh('Ertaga olib ketiladi', b.filter((x) => x.olib_ketish === d.ertaga && x.holat !== 'berildi'))}
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
