import { useCallback, useEffect, useState } from 'react'
import LibosSiluet from '../components/LibosSiluet'
import TelegramBlok from '../components/TelegramBlok'
import { boglandim, boshEkran, chegirmaQaror, chegirmaSorovlari, qarzdorlar, sanaMatni, som, xatoMatni } from '../api'
import { ZAKAZ_HOLATLARI } from '../nomlar'

const holatSinfi = (h) => ({ vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopildi: 'qaytarildi', bekor: 'qarz' }[h] || 'bron')

// FT-1.2: bosh sahifa (Point uslubi). Rahbarga tepada ko'rsatkichlar va grafiklar (`yuqori` — Dashbord),
// ostida bitta jadval paneli: bugungi ishlar, eslatmalar, qaror kutayotganlar va qarzdorlar — tablar bilan,
// ustma-ust bloklar o'rniga. «Yangi zakaz» tugmasi navigatsiyada doim ko'rinib turadi.
export default function BoshEkran({ onZakaz, onKassa, rahbar, boshlash, yuqori, tasdiqSoni, onBolim }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  const [sorovlar, setSorovlar] = useState([])
  const [qarz, setQarz] = useState(null)
  const [tab, setTab] = useState(null)

  const yukla = useCallback(() => {
    boshEkran().then(setD).catch((e) => setXato(xatoMatni(e)))
    if (rahbar) {
      chegirmaSorovlari().then(setSorovlar).catch(() => {})
      qarzdorlar().then(setQarz).catch(() => {})
    }
  }, [rahbar])
  useEffect(() => { yukla() }, [yukla])

  const tablar = d ? [
    ...(rahbar ? [['tasdiq', 'Tasdiq kutmoqda', sorovlar.length + (tasdiqSoni?.liboslar || 0) + (tasdiqSoni?.xarajatlar || 0)]] : []),
    ['olib', 'Bugun olib ketish', d.olib_ketiladi.length],
    ['qaytar', 'Bugun qaytarish', d.qaytariladi.length],
    ['kech', 'Kechikkan', d.kechikkan.length],
    ['eslatma', 'Eslatmalar', d.eslatmalar.filter((e) => !e.boglangan).length],
    ...(rahbar ? [['qoldiq', 'Qoldiq kutilmoqda', qarz?.qoldiq_kutilmoqda.length || 0], ['qarz', 'Qarzdorlar', qarz?.qarzdorlar.length || 0]] : []),
  ] : []
  // Tanlanmagan bo'lsa — birinchi bo'sh bo'lmagan tab (rahbarga odatda qaror kutayotganlar)
  const joriy = tab || tablar.find(([, , n]) => n > 0)?.[0] || 'olib'

  return (
    <div className="bosh-sahifa">
      {boshlash}
      {yuqori}
      {d && !d.smena.ochiq && (
        <div className="ogohlantirish qator-ogoh">
          <span>Smena ochiq emas — to'lov qabul qilib bo'lmaydi.</span>
          <button className="ikkinchi kichik" onClick={onKassa}>Kassaga o'tish</button>
        </div>
      )}
      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Ishlar</h3>
          <div className="tezkor-tablar" role="tablist" aria-label="Ishlar">
            {tablar.map(([k, nom, n]) => (
              <button key={k} type="button" role="tab" aria-selected={joriy === k} className={joriy === k ? 'faol' : ''} onClick={() => setTab(k)}>
                {nom}{n > 0 && <span className="tab-son">{n}</span>}
              </button>
            ))}
          </div>
        </div>
        {xato && <p className="xato jadval-bosh">{xato}</p>}
        {!d && !xato && <p className="malumot jadval-bosh">Yuklanmoqda…</p>}
        {d && joriy === 'olib' && <ZakazJadval royxat={d.olib_ketiladi} onZakaz={onZakaz} bosh="Bugun olib ketiladigan libos yo'q." />}
        {d && joriy === 'qaytar' && <ZakazJadval royxat={d.qaytariladi} onZakaz={onZakaz} bosh="Bugun qaytariladigan libos yo'q." />}
        {d && joriy === 'kech' && <ZakazJadval royxat={d.kechikkan} onZakaz={onZakaz} bosh="Kechikkan qaytarish yo'q." />}
        {d && joriy === 'eslatma' && (d.eslatmalar.length === 0 ? <p className="malumot jadval-bosh">Bugun eslatma yo'q.</p> : (
          <div className="eslatmalar">
            {d.eslatmalar.map((e) => <Eslatma key={`${e.tur}-${e.zakaz_id}`} e={e} onZakaz={onZakaz} onBajarildi={yukla} />)}
          </div>
        ))}
        {joriy === 'tasdiq' && <Tasdiqlar sorovlar={sorovlar} soni={tasdiqSoni} onZakaz={onZakaz} onBolim={onBolim} onOzgardi={yukla} />}
        {joriy === 'qoldiq' && (
          <ZakazJadval royxat={qarz?.qoldiq_kutilmoqda || []} onZakaz={onZakaz} bosh="Qoldiq kutayotgan zakaz yo'q."
            summa={(z) => som(z.qoldiq)} summaNomi="Qoldiq" />
        )}
        {joriy === 'qarz' && (
          <ZakazJadval royxat={qarz?.qarzdorlar || []} onZakaz={onZakaz} bosh="Qarzdor yo'q."
            summa={(z) => <span className="qizil">{som(z.qarz)}</span>} summaNomi="Qarz" />
        )}
      </section>
      <TelegramBlok rahbar={rahbar} />
    </div>
  )
}

// Zakazlar ro'yxati — Zakazlar sahifasidagi jadval bilan bir xil ko'rinish
function ZakazJadval({ royxat, onZakaz, bosh, summa = (z) => som(z.jami), summaNomi = 'Jami' }) {
  if (royxat.length === 0) return <p className="malumot jadval-bosh">{bosh}</p>
  return (
    <div className="jadval-ora">
      <table className="zakaz-jadval">
        <thead><tr><th>Zakaz</th><th className="tor-yashir">Ijara</th><th>Holat</th><th className="ong">{summaNomi}</th></tr></thead>
        <tbody>
          {royxat.map((z) => (
            <tr key={z.id} onClick={() => onZakaz(z.id)}>
              <td>
                <button type="button" className="zakaz-katak">
                  <span className="zakaz-eskiz">{z.rasm ? <img src={z.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
                  <span className="zakaz-nom"><b>#{z.raqam} {z.mijoz}</b><small>{z.liboslar.join(', ')}</small></span>
                </button>
              </td>
              <td className="tor-yashir">{sanaMatni(z.olib_ketish)} – {sanaMatni(z.qaytarish)}</td>
              <td><span className={`holat ${holatSinfi(z.holat)}`}>{ZAKAZ_HOLATLARI[z.holat]}</span></td>
              <td className="ong"><b>{summa(z)}</b></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Rahbar qarorini kutayotganlar. Chegirma so'rovi shu yerning o'zida tasdiqlanadi (avval faqat Telegram orqali edi).
function Tasdiqlar({ sorovlar, soni, onZakaz, onBolim, onOzgardi }) {
  const [xato, setXato] = useState('')
  const qaror = async (id, q) => {
    setXato('')
    try { await chegirmaQaror(id, { qaror: q }); onOzgardi() } catch (e) { setXato(xatoMatni(e)) }
  }
  const boshqa = [
    soni?.liboslar > 0 && [`${soni.liboslar} ta yangi libos katalogga chiqishini kutmoqda`, 'katalog:liboslar'],
    soni?.xarajatlar > 0 && [`${soni.xarajatlar} ta xarajat tasdiqni kutmoqda`, 'hisobotlar:xarajat'],
  ].filter(Boolean)
  if (sorovlar.length === 0 && boshqa.length === 0) return <p className="malumot jadval-bosh">Qaror kutayotgan narsa yo'q.</p>
  return (
    <div className="tasdiq-royxat">
      {xato && <p className="xato">{xato}</p>}
      {sorovlar.map((c) => (
        <div key={c.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b><button type="button" className="havola" onClick={() => onZakaz(c.zakaz)}>#{c.zakaz_raqami}</button> {c.mijoz} — chegirma {c.foiz ? `${Number(c.foiz)}%` : som(c.summa)}</b>
            <small>{som(c.zakaz_jami)} dan · {c.sabab_nomi}{c.sotuvchi ? ` · so'radi: ${c.sotuvchi}` : ''}{c.izoh ? ` · «${c.izoh}»` : ''}</small>
          </div>
          <div className="tasdiq-tugmalar">
            <button type="button" className="ikkinchi kichik" onClick={() => qaror(c.id, 'rad')}>Rad etish</button>
            <button type="button" className="kichik" onClick={() => qaror(c.id, 'tasdiq')}>Tasdiqlash</button>
          </div>
        </div>
      ))}
      {boshqa.map(([t, b]) => (
        <button key={t} type="button" className="tasdiq-qator havola-qator" onClick={() => onBolim(b)}>{t}</button>
      ))}
    </div>
  )
}

// 4.14: eslatma sotuvchiga chiqadi; u mijoz bilan o'zi bog'lanadi va natijani yozadi (FT-14.2).
function Eslatma({ e, onZakaz, onBajarildi }) {
  const [izoh, setIzoh] = useState('')
  const [ochiq, setOchiq] = useState(false)
  return (
    <div className={`tasdiq-qator ${e.boglangan ? 'bajarilgan' : ''}`}>
      <div className="tasdiq-matn">
        <b><button className="havola" onClick={() => onZakaz(e.zakaz_id)}>#{e.raqam}</button> {e.mijoz || 'Mijoz'} · <a href={`tel:${e.telefon}`}>{e.telefon}</a></b>
        <small>{e.matn}</small>
      </div>
      <div className="tasdiq-tugmalar">
        {e.boglangan ? <span className="malumot">Bog'lanildi</span> : ochiq ? (
          <>
            <input placeholder="Natija (ixtiyoriy)" aria-label="Natija" value={izoh} onChange={(ev) => setIzoh(ev.target.value)} />
            <button className="kichik" onClick={() => boglandim(e.zakaz_id, e.tur, izoh).then(onBajarildi)}>Saqlash</button>
          </>
        ) : <button className="ikkinchi kichik" onClick={() => setOchiq(true)}>Bog'landim</button>}
      </div>
    </div>
  )
}
