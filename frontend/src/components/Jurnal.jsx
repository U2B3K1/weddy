import { useEffect, useState } from 'react'
import { amallarJurnali, som, telegramXabarlari, xatoMatni } from '../api'
import Sahifali from './Sahifalash'
import NavIkona from './NavIkona'
import { SPanel, Yorliq } from './SozlamaUI'

// Kanvas jurnali (server vaqti UTC — mahalliy vaqtda): «bugun 11:20», «kecha 20:05», «7 noy, 17:40»
const OY = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek']
const qisqaVaqt = (s) => {
  const t = new Date(s), n = (x) => String(x).padStart(2, '0'), soat = `${n(t.getHours())}:${n(t.getMinutes())}`
  const kun = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const farq = Math.round((kun(new Date()) - kun(t)) / 86_400_000)
  if (farq === 0) return `bugun ${soat}`
  if (farq === 1) return `kecha ${soat}`
  return `${t.getDate()} ${OY[t.getMonth()]}, ${soat}`
}
// Amal turi bo'yicha belgi (libos, sozlama, pul, qurilma, sanoq)
const jurnalBelgi = (h) => (/libos|aksessuar|dona|tannarx|ijara|zalog_oz/.test(h) ? 'katalog'
  : /sozlama/.test(h) ? 'sozlamalar' : /tolov|oy_|smena|kassa/.test(h) ? 'kassa' : /qurilma|platforma/.test(h) ? 'qurilma'
    : /sanoq/.test(h) ? 'raqam' : 'tarix')
// Amal nomlari odam tilida (B-39); lug'atda yo'q kod — «xarajat_tuzatildi» → «Xarajat tuzatildi», apostrof bilan
const HARAKAT = {
  libos_qoshildi: "Libos qo'shildi", libos_tasdiqlandi: 'Libos tasdiqlandi', libos_holati: "Libos holati o'zgardi",
  libos_filiali: "Libos filiali o'zgardi", libos_kategoriyasi: "Libos kategoriyasi o'zgardi",
  libos_yetkazib_beruvchisi: "Libos yetkazib beruvchisi o'zgardi", ijara_narxi_ozgardi: "Ijara narxi o'zgardi",
  tannarx_ozgardi: "Tannarx o'zgardi", zalog_ozgardi: "Zalog summasi o'zgardi", aksessuar_qoshildi: "Aksessuar qo'shildi",
  dona_holati: "Dona holati o'zgardi", sozlama_ozgardi: "Sozlama o'zgardi", oy_yopildi: 'Oy yopildi', oy_qayta_ochildi: 'Oy qayta ochildi',
  sanoq_bekor_qilindi: 'Sanoq bekor qilindi', yetkazib_beruvchiga_tolov: "Yetkazib beruvchiga to'lov",
  yetkazib_beruvchi_tolovi_ochirildi: "Yetkazib beruvchiga to'lov o'chirildi", qurilma_pin_xato: "Qurilmada PIN xato terildi",
  platforma_yordam_kirishi: 'Texnik yordam kirdi', qurilma_filiali: "Qurilma filiali o'zgardi",
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
// Ilova B: rahbar kim nimani o'zgartirganini ko'radi (oxirgi 200 ta). Telegram xabarlari — bot ishlayaptimi,
// kimga yetib bormagan (oxirgi 100 ta). Ikkalasi ham faqat o'qish uchun.
export default function Jurnal() {
  const [amallar, setAmallar] = useState(null)
  const [xabarlar, setXabarlar] = useState(null)
  const [q, setQ] = useState('')
  const [xato, setXato] = useState('')
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

  return (
    <>
      <SPanel id="jurnal" ikon="tarix" nomi="Jurnal" izoh="Kim nimani qachon o'zgartirgan (oxirgi 200 ta)"
        ong={<input type="search" className="soz-tanlov soz-jurnal-qidiruv" placeholder="Qidirish: Malika, narx, L001" aria-label="Jurnaldan qidirish"
          value={q} onChange={(e) => setQ(e.target.value)} />}>
        {xato && <p className="xato">{xato}</p>}
        {amallar === null && !xato && <p className="soz-izoh">Yuklanmoqda…</p>}
        {amallar && korinadi.length === 0 && <p className="soz-izoh">Yozuv topilmadi.</p>}
        {korinadi.length > 0 && (
          <Sahifali royxat={korinadi} hajm={12} kalit={s} nomi="yozuv">{(qism) => qism.map((j, i) => (
            <div key={`${i}-${j.vaqt}`} className="soz-jurnal-q">
              <span className="soz-mute">{qisqaVaqt(j.vaqt)}</span>
              <span className="soz-j-belgi" aria-hidden="true"><NavIkona nom={jurnalBelgi(j.harakat)} className="tugma-ikon" /></span>
              <span className="soz-matn">
                <b>{j.xodim || '—'} · {harakatNomi(j.harakat).toLowerCase()}</b>
                <small>{j.obyekt}{(j.eski || j.yangi) && `: ${qiymat(j.eski)} → ${qiymat(j.yangi)}`}</small>
              </span>
            </div>
          ))}</Sahifali>
        )}
      </SPanel>
      <SPanel ikon="xabar" nomi="Telegram xabarlari" izoh={yetmagan.length > 0 ? `Yetib bormagan: ${yetmagan.length} ta — sababi pastda` : 'Bot xodimlarga yuborgan oxirgi xabarlar'}>
        {xabarlar === null && <p className="soz-izoh">Yuklanmoqda…</p>}
        {xabarlar && xabarlar.length === 0 && <p className="soz-izoh">Hali xabar yuborilmagan.</p>}
        {sabablar.length > 0 && (
          <ul className="soz-sabablar">
            {sabablar.map((g) => (
              <li key={g.sabab}>
                <b>{g.sabab}</b> — {g.soni} ta xabar · {[...g.xodimlar].join(', ')}
              </li>
            ))}
            <li className="soz-mute">Ulash: Salon va xodimlar → «Xodimlar» → xodim menyusi → «Telegram».</li>
          </ul>
        )}
        {xabarlar && xabarlar.length > 0 && (
          <Sahifali royxat={xabarlar} hajm={10} nomi="xabar">{(qism) => (
            <table className="soz-jadval soz-tg-jadval">
              <thead><tr><th>Vaqt</th><th>Xabar</th><th className="ong">Holat</th></tr></thead>
              <tbody>
                {qism.map((x, i) => (
                  <tr key={`${x.vaqt}-${i}`}>
                    <td className="soz-mute">{qisqaVaqt(x.vaqt)}<br />{x.xodim}</td>
                    <td>{x.matn.length > 110 ? `${x.matn.slice(0, 110)}…` : x.matn}</td>
                    <td className="ong">
                      <Yorliq tur={x.holat === 'yuborildi' ? 'yashil' : 'qizil'} title={x.xato || undefined}>{x.holat === 'yuborildi' ? 'yetkazildi' : 'yetmadi'}</Yorliq>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}</Sahifali>
        )}
      </SPanel>
    </>
  )
}
