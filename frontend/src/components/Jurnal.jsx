import { useEffect, useState } from 'react'
import { amallarJurnali, som, telegramXabarlari, xatoMatni } from '../api'

// Server vaqti UTC da keladi — mahalliy vaqtda «25.10.2026 14:30»
const vaqtMatni = (s) => {
  const t = new Date(s), n = (x) => String(x).padStart(2, '0')
  return `${n(t.getDate())}.${n(t.getMonth() + 1)}.${t.getFullYear()} ${n(t.getHours())}:${n(t.getMinutes())}`
}
// Amal nomlari odam tilida (B-39); lug'atda yo'q kod — «xarajat_tuzatildi» → «Xarajat tuzatildi», apostrof bilan
const HARAKAT = {
  libos_qoshildi: "Libos qo'shildi", libos_tasdiqlandi: 'Libos tasdiqlandi', libos_holati: "Libos holati o'zgardi",
  libos_filiali: "Libos filiali o'zgardi", libos_kategoriyasi: "Libos kategoriyasi o'zgardi",
  libos_yetkazib_beruvchisi: "Libos yetkazib beruvchisi o'zgardi", ijara_narxi_ozgardi: "Ijara narxi o'zgardi",
  tannarx_ozgardi: "Tannarx o'zgardi", zalog_ozgardi: "Zalog summasi o'zgardi", aksessuar_qoshildi: "Aksessuar qo'shildi",
  dona_holati: "Dona holati o'zgardi", sozlama_ozgardi: "Sozlama o'zgardi", oy_yopildi: 'Oy yopildi', oy_qayta_ochildi: 'Oy qayta ochildi',
  sanoq_bekor_qilindi: 'Sanoq bekor qilindi', yetkazib_beruvchiga_tolov: "Yetkazib beruvchiga to'lov",
  yetkazib_beruvchi_tolovi_ochirildi: "Yetkazib beruvchiga to'lov o'chirildi", qurilma_pin_xato: "Qurilmada PIN xato terildi",
  platforma_yordam_kirishi: 'Texnik yordam kirdi',
}
const SOZ = [[/\bqoshildi\b/g, "qo'shildi"], [/\bozgardi\b/g, "o'zgardi"], [/\bochirildi\b/g, "o'chirildi"], [/\btolov/g, "to'lov"],
  [/\bozgartirildi\b/g, "o'zgartirildi"], [/\bruyxat/g, "ro'yxat"], [/\broyxat/g, "ro'yxat"]]
const harakatNomi = (h) => {
  if (HARAKAT[h]) return HARAKAT[h]
  let m = h.replaceAll('_', ' ')
  for (const [re, v] of SOZ) m = m.replace(re, v)
  return m.charAt(0).toUpperCase() + m.slice(1)
}
// Holat kodlari odam tilida (libos, aksessuar, dona, promokod)
const HOLAT_NOMI = {
  faol: 'faol', nofaol: 'nofaol', bosh: "bo'sh", tasdiq_kutilmoqda: 'tasdiq kutilmoqda', tamirda: "ta'mirda", tozalashda: 'tozalashda',
  sotildi: 'sotildi', hisobdan_chiqarildi: 'hisobdan chiqarildi', arxiv: 'arxiv', yoqolgan: "yo'qolgan", toxtatilgan: "to'xtatilgan",
}
const holatNomi = (k) => HOLAT_NOMI[k] || k.replaceAll('_', ' ')
// Qiymat odam tilida (QA-09): butun son — summa («100000» → «100 000 so'm»); faqat holat kodi — nomi;
// matn ichida «narx 300000, holat faol» → «narx 300 000 so'm, holat: faol»
const qiymat = (v) => {
  if (v === null || v === undefined || v === '') return '—'
  const t = String(v)
  if (/^-?\d{4,}$/.test(t)) return som(t)
  if (HOLAT_NOMI[t]) return holatNomi(t)
  return t.replace(/\b(narx|tannarx|zalog|summa|bonus|komissiya|chegirma)\s+(-?\d+)\b/g, (_, soz, n) => `${soz} ${som(n)}`)
    .replace(/\bholat\s+([a-z_]+)/g, (_, k) => `holat: ${holatNomi(k)}`)
}
const KORINADI = 30

// Ilova B: rahbar kim nimani o'zgartirganini ko'radi (oxirgi 200 ta). Telegram xabarlari — bot ishlayaptimi,
// kimga yetib bormagan (oxirgi 100 ta). Ikkalasi ham faqat o'qish uchun.
export default function Jurnal() {
  const [amallar, setAmallar] = useState(null)
  const [xabarlar, setXabarlar] = useState(null)
  const [q, setQ] = useState('')
  const [xato, setXato] = useState('')
  const [hammasi, setHammasi] = useState(false)
  useEffect(() => {
    amallarJurnali().then(setAmallar).catch((e) => setXato(xatoMatni(e)))
    telegramXabarlari().then(setXabarlar).catch(() => setXabarlar([]))
  }, [])

  const s = q.trim().toLowerCase()
  const korinadi = (amallar || []).filter((j) => !s || [harakatNomi(j.harakat), j.harakat, j.obyekt, j.eski, j.yangi, j.xodim]
    .some((v) => String(v ?? '').toLowerCase().includes(s)))
  const yetmagan = (xabarlar || []).filter((x) => x.holat !== 'yuborildi')
  // Yetib bormaganlar sabab bo'yicha guruhlanadi: bir xil «Xodim Telegram ulamagan» qatori 100 marta takrorlanmasin (B-39)
  const sabablar = Object.values(yetmagan.reduce((g, x) => {
    const k = x.xato || x.holat_nomi
    g[k] = g[k] || { sabab: k, soni: 0, xodimlar: new Set() }
    g[k].soni += 1; g[k].xodimlar.add(x.xodim)
    return g
  }, {})).sort((a, b) => b.soni - a.soni)
  const tgKorinadi = hammasi ? xabarlar || [] : (xabarlar || []).slice(0, KORINADI)

  return (
    <>
      <section className="blok stack">
        <h3>Amallar jurnali</h3>
        {xato && <p className="xato">{xato}</p>}
        <input type="search" placeholder="Qidirish: xodim, amal yoki obyekt (masalan: Malika, narx, L001)" aria-label="Jurnaldan qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
        {amallar === null && !xato && <p className="malumot">Yuklanmoqda…</p>}
        {amallar && korinadi.length === 0 && <p className="malumot">Yozuv topilmadi.</p>}
        {korinadi.length > 0 && (
          <table className="jadval r2-jurnal"><tbody>
            {korinadi.map((j, i) => (
              <tr key={i} className="kichik-qator">
                <td>{vaqtMatni(j.vaqt)}<br />{j.xodim || '—'}</td>
                <td><b>{harakatNomi(j.harakat)}</b> · {j.obyekt}
                  {(j.eski || j.yangi) && <><br />{qiymat(j.eski)} → {qiymat(j.yangi)}</>}
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </section>
      <section className="blok stack">
        <h3>Telegram xabarlari{yetmagan.length > 0 ? ` · yetib bormagan: ${yetmagan.length}` : ''}</h3>
        {xabarlar === null && <p className="malumot">Yuklanmoqda…</p>}
        {xabarlar && xabarlar.length === 0 && <p className="malumot">Hali xabar yuborilmagan.</p>}
        {sabablar.length > 0 && (
          <ul className="r2-sabablar">
            {sabablar.map((g) => (
              <li key={g.sabab}>
                <b className="qizil">{g.sabab}</b> — {g.soni} ta xabar
                <span className="malumot"> · {[...g.xodimlar].join(', ')}</span>
              </li>
            ))}
            <li className="malumot">Telegram ulanmagan xodimni ulash: Sozlama → «Xodimlar» → xodim menyusi → «Telegram».</li>
          </ul>
        )}
        {xabarlar && xabarlar.length > 0 && (
          <table className="jadval r2-jurnal"><tbody>
            {tgKorinadi.map((x, i) => (
              <tr key={i} className="kichik-qator">
                <td>{vaqtMatni(x.vaqt)}<br />{x.xodim}</td>
                <td>{x.matn.length > 120 ? `${x.matn.slice(0, 120)}…` : x.matn}</td>
                <td className={x.holat === 'yuborildi' ? '' : 'qizil'}>{x.holat_nomi}{x.xato ? `: ${x.xato}` : ''}</td>
              </tr>
            ))}
          </tbody></table>
        )}
        {xabarlar && xabarlar.length > KORINADI && (
          <button type="button" className="ikkinchi kichik r2-yana-tugma" onClick={() => setHammasi(!hammasi)}>
            {hammasi ? `Oxirgi ${KORINADI} tasini ko'rsatish` : `Hammasini ko'rsatish (${xabarlar.length})`}
          </button>
        )}
      </section>
    </>
  )
}
