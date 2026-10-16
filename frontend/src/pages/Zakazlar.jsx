import { useCallback, useEffect, useState } from 'react'
import Hujjat from '../components/Hujjat'
import Tasdiq from '../components/Tasdiq'
import {
  bekorQilish, berish, chegirmaSora, mijozOzgartir, tolovHavola, primerkaBelgila, primerkaOzgartir, promokodOlibTashla, promokodQolla, qarzTolash, qaytarish, sanaKochirish, som, sozlamalar, tayyorChegirmalar,
  tolovQabul, xatoMatni, zakazAksessuarOchir, zakazAksessuarQosh, zakazTafsilot, zakazTarixi, zakazlarRoyxat,
  boshAksessuarlar, boshLiboslar, libosAlmashtirish, salonchilar, zakazSalonchi,
} from '../api'

const HOLATLAR = {
  vaqtinchalik: 'Vaqtinchalik bron', chegirma_kutilmoqda: "Chegirma tasdig'i kutilmoqda", bron: 'Bron',
  berildi: 'Berildi', qaytarildi: 'Qaytarildi (qarz bor)', yopildi: 'Yopildi', bekor: 'Bekor qilingan',
}

// Zakaz yo'li: 4 qadam; «yopildi» — hammasi o'tilgan, «bekor» — hech biri.
const QADAMLAR = ['Bron', 'Avans', 'Berildi', 'Qaytarildi']
function qadamIndeksi(z) {
  const h = z.holat
  if (h === 'yopildi') return 4
  if (h === 'qaytarildi') return 3
  if (h === 'berildi') return 2
  if (h === 'bron') return z.qoldiq === 0 ? 2 : 1
  if (h === 'vaqtinchalik') return z.tolangan > 0 ? 1 : 0
  return 0
}
// Holatga qarab bitta katta asosiy tugma matni (yo'riqnoma 8.1)
function asosiyTugma(z) {
  const h = z.holat
  if (h === 'vaqtinchalik' && z.qoldiq > 0) return 'Avans qabul qilish'
  if (h === 'bron' && z.qoldiq > 0) return 'Qoldiqni qabul qilish'
  if (h === 'bron') return 'Libosni berish'
  if (h === 'berildi') return 'Qaytarib olish'
  if (h === 'qaytarildi' && z.qarz > 0) return 'Qarzni yopish'
  return null
}
const holatSinfi = (h) => ({ vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopildi: 'qaytarildi', bekor: 'qarz' }[h] || 'bron')

export default function Zakazlar({ tanlangan, onTanla }) {
  const [q, setQ] = useState('')
  const [holat, setHolat] = useState('')
  const [royxat, setRoyxat] = useState([])
  const [xato, setXato] = useState('')

  useEffect(() => {
    zakazlarRoyxat({ q: q || undefined, holat: holat || undefined })
      .then(setRoyxat).catch((e) => setXato(xatoMatni(e)))
  }, [q, holat, tanlangan])

  if (tanlangan) return <Karta id={tanlangan} onOrqaga={() => onTanla(null)} />

  return (
    <div className="stack">
      <input placeholder="Raqam, telefon yoki ism" value={q} onChange={(e) => setQ(e.target.value)} />
      <select value={holat} onChange={(e) => setHolat(e.target.value)}>
        <option value="">Barcha holatlar</option>
        {Object.entries(HOLATLAR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      {xato && <p className="xato">{xato}</p>}
      {royxat.length === 0 && <p className="malumot">Zakaz topilmadi.</p>}
      {royxat.map((z) => (
        <button key={z.id} className="qator-btn" onClick={() => onTanla(z.id)}>
          <b>#{z.raqam}</b> {z.mijoz} · {z.olib_ketish}
          <span>{HOLATLAR[z.holat]} · {som(z.jami)}</span>
        </button>
      ))}
    </div>
  )
}

function Karta({ id, onOrqaga }) {
  const [z, setZ] = useState(null)
  const [tarix, setTarix] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [soz, setSoz] = useState(null)
  const [chop, setChop] = useState(null)
  useEffect(() => { sozlamalar().then(setSoz).catch(() => {}) }, [])

  const yukla = useCallback(() => zakazTafsilot(id).then(setZ), [id])
  useEffect(() => { yukla() }, [yukla])

  // Har bir amal: muvaffaqiyatda kartani yangilaydi, xatoni ko'rsatadi.
  const bajar = async (fn, ok = 'Bajarildi.') => {
    setXabar({ turi: '', matn: '' })
    try {
      await fn()
      setXabar({ turi: 'ok', matn: ok })
      setTarix(null)
      await yukla()
      return true
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
      return false
    }
  }

  if (chop) return <Hujjat zakazId={id} tur={chop} onYop={() => setChop(null)} />
  if (!z) return <p className="malumot">Yuklanmoqda…</p>
  const h = z.holat

  return (
    <div className="stack karta">
      <div className="karta-bosh">
        <button className="ikkinchi karta-orqaga" aria-label="Zakazlar ro'yxatiga qaytish" onClick={onOrqaga}>‹</button>
        <h2>Zakaz #{z.raqam}</h2>
        <span className={`holat ${holatSinfi(h)}`}>{HOLATLAR[h]}</span>
      </div>
      {h !== 'bekor' && (
        <ol className="holat-chizigi" aria-label="Zakaz bosqichlari">
          {QADAMLAR.map((n, i) => <li key={n} className={i < qadamIndeksi(z) ? 'otdi' : i === qadamIndeksi(z) ? 'joriy' : ''}><i />{n}</li>)}
        </ol>
      )}
      {asosiyTugma(z) && (
        <button className="asosiy-tugma" onClick={() => {
          const d = document.getElementById('asosiy-amal')
          if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }) }
        }}>{asosiyTugma(z)}</button>
      )}
      <section className="blok karta-asosiy">
        <p>{z.mijoz === z.telefon ? z.telefon : `${z.mijoz} · ${z.telefon}`}</p>
        <p>{z.liboslar.join(', ')}</p>
        {z.aksessuarlar.length > 0 && <p className="malumot">Aksessuarlar: {z.aksessuarlar.join(', ')}</p>}
        <p>{z.olib_ketish} – {z.qaytarish}</p>
        {z.salonchi && (
          <p className="malumot">Salonchi: {z.salonchi.ism}
            {z.salonchi.instagram && <> · <a href={z.salonchi.instagram} target="_blank" rel="noreferrer">Instagram</a></>}
          </p>
        )}
        <table className="jadval"><tbody>
          <tr><td>Asosiy narx</td><td>{som(z.asosiy_narx - z.xizmatlar)}</td></tr>
          {z.xizmatlar > 0 && <tr><td>Moslash xizmati</td><td>{som(z.xizmatlar)}</td></tr>}
          {z.ustama > 0 && <tr><td>Mavsumiy ustama ({Number(z.ustama_foiz)}%)</td><td>{som(z.ustama)}</td></tr>}
          {z.chegirma - z.promokod_chegirma > 0 && <tr><td>Chegirma</td><td>−{som(z.chegirma - z.promokod_chegirma)}</td></tr>}
          {z.promokod && <tr><td>Promokod {z.promokod}</td><td>−{som(z.promokod_chegirma)}</td></tr>}
          <tr><td><b>Jami</b></td><td><b>{som(z.jami)}</b></td></tr>
          <tr><td>To'langan</td><td>{som(z.tolangan)}</td></tr>
          <tr><td>Qoldiq</td><td>{som(z.qoldiq)}</td></tr>
          {z.qarz > 0 && <tr className="qizil"><td>Jarima qarzi</td><td>{som(z.qarz)}</td></tr>}
        </tbody></table>
        {z.bekor_sabab && <p className="malumot">Bekor sababi: {z.bekor_sabab}</p>}
        <div className="qator hujjat-havolalar">
          {!['chegirma_kutilmoqda', 'bekor'].includes(h) && (
            <button className="ikkinchi kichik" onClick={() => setChop('shartnoma')}>Shartnoma</button>
          )}
          {z.tolovlar.length > 0 && h !== 'chegirma_kutilmoqda' && (
            <button className="ikkinchi kichik" onClick={() => setChop('kvitansiya')}>Kvitansiya</button>
          )}
          {z.zaloglar.length > 0 && (
            <button className="ikkinchi kichik" onClick={() => setChop('dalolatnoma')}>Zalog dalolatnomasi</button>
          )}
        </div>
        {h === 'chegirma_kutilmoqda' && <p className="malumot">Chegirma tasdiqlanmaguncha shartnoma chop etilmaydi.</p>}
      </section>
      <div className="karta-ong">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {(h === 'vaqtinchalik' || h === 'bron') && z.qoldiq > 0 && (
        <TolovForma sarlavha={h === 'bron' ? "Qoldiq to'lov" : 'Avans qabul qilish'} maks={z.qoldiq}
          zakazId={soz?.tolov_havolasi ? z.id : null}
          onYuborish={(summa, usul) => bajar(
            () => tolovQabul({ zakaz: z.id, tur: h === 'bron' ? 'qoldiq' : 'avans', summa, usul }),
            `To'lov qabul qilindi.${soz?.fiskal_eslatma ? ` ${soz.fiskal_izoh || 'Fiskal chekni urishni unutmang.'}` : ''}`)} />
      )}
      {h === 'bron' && z.qoldiq === 0 && <BerishForma soz={soz} onYuborish={(zaloglar) => bajar(() => berish(z.id, zaloglar), 'Libos berildi.')} />}
      {h === 'berildi' && <QaytarishForma baholash={soz ? soz.mijoz_bahosi : true} onYuborish={(b) => bajar(() => qaytarish(z.id, b), 'Qaytarish rasmiylashtirildi.')} />}
      {h === 'qaytarildi' && z.qarz > 0 && (
        <TolovForma sarlavha="Jarima qarzini to'lash" maks={z.qarz} usulsiz
          onYuborish={(summa) => bajar(() => qarzTolash(z.id, summa), "Qarz to'landi.")} />
      )}
      <details className="boshqa-amallar">
        <summary className="havola-tugma">Boshqa amallar</summary>
      {h === 'vaqtinchalik' && z.tolangan === 0 && (soz?.promokodlar_bolimi !== false || z.promokod) && <PromokodForma z={z} bajar={bajar} />}
      {h === 'vaqtinchalik' && <ChegirmaForma zakazId={z.id} z={z} bajar={bajar} />}
      {['vaqtinchalik', 'bron'].includes(h) && <AksessuarForma z={z} bajar={bajar} />}
      {['vaqtinchalik', 'chegirma_kutilmoqda', 'bron'].includes(h) && <LibosAlmashtirishForma z={z} bajar={bajar} />}
      {h !== 'bekor' && <SalonchiTanlash z={z} bajar={bajar} />}
      {(soz?.primerka || z.primerkalar.length > 0) && (
        <PrimerkaForma z={z} bajar={bajar} ochiq={['vaqtinchalik', 'chegirma_kutilmoqda', 'bron'].includes(h) && !!soz?.primerka} />
      )}
      {['vaqtinchalik', 'chegirma_kutilmoqda', 'bron'].includes(h) && (
        <>
          <KochirishForma onYuborish={(b) => bajar(() => sanaKochirish(z.id, b), 'Sana ko\'chirildi.')} />
          <BekorForma soz={soz} onYuborish={(b) => bajar(() => bekorQilish(z.id, b), 'Zakaz bekor qilindi.')} />
        </>
      )}
      </details>
      </div>
      <section className="blok karta-tolovlar">
        <h3>To'lovlar</h3>
        {z.tolovlar.length === 0 && <p className="malumot">Hali yo'q</p>}
        {z.tolovlar.map((t, i) => (
          <p key={i} className="qator-matn">{t.tur} · {som(t.summa)} · {t.usul} · {t.xodim}</p>
        ))}
        {z.zaloglar.map((g) => (
          <p key={g.id} className="qator-matn">Zalog {g.yorliq}: {g.turi} · {g.holat}</p>
        ))}
        <button className="ikkinchi kichik" onClick={() => zakazTarixi(id).then(setTarix)}>O'zgarishlar tarixi</button>
        {tarix && tarix.map((t, i) => (
          <p key={i} className="qator-matn">{t.harakat}: {t.eski} → {t.yangi} ({t.xodim}) {t.sabab}</p>
        ))}
      </section>
    </div>
  )
}

// Saqlangan zakazga aksessuar qo'shish yoki olib tashlash; narx va bandlik serverda qayta hisoblanadi.
function AksessuarForma({ z, bajar }) {
  const [bosh, setBosh] = useState([])
  const [tanlov, setTanlov] = useState('')
  const qatorlar = z.aksessuar_qatorlari
  useEffect(() => {
    boshAksessuarlar(z.olib_ketish, z.qaytarish).then(setBosh).catch(() => {})
  }, [z.olib_ketish, z.qaytarish, qatorlar.length])
  const id = tanlov || bosh[0]?.id
  return (
    <Amal sarlavha={`Aksessuarlar (${qatorlar.length})`}>
      {qatorlar.map((q) => (
        <div key={q.id} className="qator aks-qator">
          <span className="matn-ustun">{q.nomi} ({q.yorliq}) · {som(q.narx)}</span>
          <button className="ikkinchi kichik"
            onClick={() => bajar(() => zakazAksessuarOchir(z.id, q.id), 'Aksessuar olib tashlandi.')}>Olib tashlash</button>
        </div>
      ))}
      {bosh.length > 0 ? (
        <div className="qator">
          <select value={id} onChange={(e) => setTanlov(e.target.value)}>
            {bosh.map((a) => <option key={a.id} value={a.id}>{a.nomi} · {som(a.ijara_narxi)} · bo'sh {a.bosh_soni}</option>)}
          </select>
          <button className="ikkinchi" onClick={() => bajar(() => zakazAksessuarQosh(z.id, Number(id)), "Aksessuar qo'shildi.")}>Qo'shish</button>
        </div>
      ) : <p className="malumot">Bu sanalarga bo'sh aksessuar yo'q.</p>}
    </Amal>
  )
}

// FT-17.2: zakazdagi libosni shu sanalarga bo'sh boshqa libosga almashtirish; narx farqi serverda hisoblanadi.
function LibosAlmashtirishForma({ z, bajar }) {
  const [bosh, setBosh] = useState(null)
  const [eski, setEski] = useState('')
  const [yangi, setYangi] = useState('')
  const [sabab, setSabab] = useState('')
  const [xato, setXato] = useState('')
  const qatorlar = z.libos_qatorlari || []
  const och = (e) => {
    if (!e.target.open || bosh) return
    boshLiboslar(z.olib_ketish, z.qaytarish).then(setBosh).catch((x) => setXato(xatoMatni(x)))
  }
  const mavjud = (bosh || []).filter((l) => !l.band && !l.qulflangan && !qatorlar.some((q) => q.id === l.id))
  const eskiId = eski || qatorlar[0]?.id
  return (
    <details className="blok amal" onToggle={och}>
      <summary>Libosni almashtirish</summary>
      <div className="stack">
        {xato && <p className="xato">{xato}</p>}
        <label>Qaysi libos
          <select value={eskiId} onChange={(e) => setEski(e.target.value)}>
            {qatorlar.map((q) => <option key={q.id} value={q.id}>{q.artikul} {q.nomi} · {som(q.narx)}</option>)}
          </select>
        </label>
        {bosh && mavjud.length === 0 && <p className="malumot">Bu sanalarga bo'sh boshqa libos yo'q.</p>}
        {mavjud.length > 0 && (
          <label>Yangi libos
            <select value={yangi} onChange={(e) => setYangi(e.target.value)}>
              <option value="">Tanlang</option>
              {mavjud.map((l) => <option key={l.id} value={l.id}>{l.artikul} {l.nomi} · {som(l.ijara_narxi)}</option>)}
            </select>
          </label>
        )}
        <label>Sabab<input value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
        <button className="ikkinchi" disabled={!eskiId || !yangi}
          onClick={() => bajar(() => libosAlmashtirish(z.id, { eski: Number(eskiId), yangi: Number(yangi), sabab }), 'Libos almashtirildi.')
            .then((ok) => { if (ok) { setYangi(''); setEski(''); setSabab(''); setBosh(null) } })}>Almashtirish</button>
      </div>
    </details>
  )
}

// Saqlangan zakazga salonchini belgilash yoki olib tashlash (FT-6.3).
function SalonchiTanlash({ z, bajar }) {
  const [royxat, setRoyxat] = useState(null)
  const [tanlov, setTanlov] = useState(z.salonchi?.id || '')
  const och = (e) => e.target.open && !royxat && salonchilar().then(setRoyxat).catch(() => setRoyxat([]))
  return (
    <details className="blok amal" onToggle={och}>
      <summary>Salonchi{z.salonchi ? `: ${z.salonchi.ism}` : ''}</summary>
      <div className="stack">
        {royxat && royxat.length === 0 && !z.salonchi && <p className="malumot">Salonchi yo'q — «Mijozlar» → «Salonchilar» bo'limida qo'shing.</p>}
        <select value={tanlov} onChange={(e) => setTanlov(e.target.value)} aria-label="Salonchi">
          <option value="">Salonchisiz</option>
          {z.salonchi && !(royxat || []).some((s) => s.id === z.salonchi.id) && <option value={z.salonchi.id}>{z.salonchi.ism}</option>}
          {(royxat || []).map((s) => <option key={s.id} value={s.id}>{s.ism}{s.salon_nomi ? ` · ${s.salon_nomi}` : ''}</option>)}
        </select>
        <button className="ikkinchi" disabled={String(tanlov) === String(z.salonchi?.id || '')}
          onClick={() => bajar(() => zakazSalonchi(z.id, tanlov ? Number(tanlov) : null), tanlov ? 'Salonchi belgilandi.' : 'Salonchi olib tashlandi.')}>Saqlash</button>
      </div>
    </details>
  )
}

function Amal({ sarlavha, children, id }) {
  return (
    <details className="blok amal" id={id}>
      <summary>{sarlavha}</summary>
      <div className="stack">{children}</div>
    </details>
  )
}

function TolovForma({ sarlavha, maks, onYuborish, usulsiz, zakazId }) {
  const [summa, setSumma] = useState('')
  const [usul, setUsul] = useState('naqd')
  // Click/Payme merchant ma'lumotlari kiritilgan bo'lsa — mijozga beriladigan to'lov havolasi
  const [havola, setHavola] = useState(null)
  const havolaOl = () => tolovHavola(zakazId, Number(summa) || undefined).then(setHavola).catch(() => setHavola({ havolalar: {} }))
  return (
    <Amal sarlavha={sarlavha} id="asosiy-amal">
      <label>Summa (maks. {som(maks)})
        <input type="number" min="1" max={maks} value={summa} onChange={(e) => setSumma(e.target.value)} />
      </label>
      {!usulsiz && (
        <select value={usul} onChange={(e) => setUsul(e.target.value)}>
          <option value="naqd">Naqd</option><option value="karta">Karta</option>
          <option value="click">Click</option><option value="payme">Payme</option>
        </select>
      )}
      {zakazId && ['click', 'payme'].includes(usul) && (
        <>
          <button type="button" className="ikkinchi" onClick={havolaOl}>To'lov havolasini ko'rsatish</button>
          {havola && Object.entries(havola.havolalar).filter(([k]) => k === usul).map(([k, url]) => (
            <p key={k} className="malumot havola-matn">
              {k === 'click' ? 'Click' : 'Payme'} · {som(havola.summa)}: <a href={url} target="_blank" rel="noreferrer">{url}</a>
            </p>
          ))}
          {havola && !havola.havolalar[usul] && <p className="malumot">Bu to'lov tizimi «Integratsiyalar»da ulanmagan.</p>}
          <p className="malumot">Havolani mijozga yuboring; to'lov tushganini merchant kabinetida ko'rgach «Qabul qilish» ni bosing.</p>
        </>
      )}
      <button disabled={!summa} onClick={() => onYuborish(Number(summa), usul).then((ok) => { if (ok) { setSumma(''); setHavola(null) } })}>
        Qabul qilish
      </button>
    </Amal>
  )
}

// FT-21.5: sotuvchi kodni kiritadi — tizim darhol qo'llaydi yoki sababini ko'rsatadi.
function PromokodForma({ z, bajar }) {
  const [kod, setKod] = useState('')
  if (z.promokod) {
    return (
      <Amal sarlavha={`Promokod: ${z.promokod}`}>
        <p className="malumot">Chegirma: {som(z.promokod_chegirma)}</p>
        <button className="ikkinchi" onClick={() => bajar(() => promokodOlibTashla(z.id), 'Promokod olib tashlandi.')}>Olib tashlash</button>
      </Amal>
    )
  }
  return (
    <Amal sarlavha="Promokod">
      <label>Kod
        <input value={kod} maxLength={30} autoCapitalize="characters" onChange={(e) => setKod(e.target.value.toUpperCase())} />
      </label>
      <button disabled={!kod.trim()}
        onClick={() => bajar(() => promokodQolla(z.id, kod), "Promokod qabul qilindi.").then((ok) => ok && setKod(''))}>
        Qo'llash
      </button>
    </Amal>
  )
}

function ChegirmaForma({ zakazId, z, bajar }) {
  const [tayyor, setTayyor] = useState([])
  const [foiz, setFoiz] = useState('')
  const [tur, setTur] = useState('foiz')
  // chegirma ustama qo'shilgan summadan hisoblanadi (FT-4.3); promokod chegirmasi saqlanadi
  const asos = z.asosiy_narx + z.ustama
  const miqdor = Math.min(tur === 'foiz' ? Math.round((asos * Number(foiz || 0)) / 100) : Number(foiz || 0), asos - (z.promokod_chegirma || 0))
  const [sabab, setSabab] = useState('doimiy_mijoz')
  useEffect(() => { tayyorChegirmalar().then(setTayyor).catch(() => {}) }, [])
  return (
    <Amal sarlavha="Chegirma">
      {tayyor.map((t) => (
        <button key={t.id} className="ikkinchi"
          onClick={() => bajar(() => chegirmaSora(zakazId, { tayyor: t.id }), 'Chegirma qo\'llandi.')}>
          {t.nomi}
        </button>
      ))}
      <div className="segment">
        <button type="button" className={tur === 'foiz' ? '' : 'ikkinchi'} onClick={() => { setTur('foiz'); setFoiz('') }}>Foizda</button>
        <button type="button" className={tur === 'summa' ? '' : 'ikkinchi'} onClick={() => { setTur('summa'); setFoiz('') }}>Summada</button>
      </div>
      <label>{tur === 'foiz' ? 'Boshqa chegirma, %' : "Boshqa chegirma, so'm"}
        <input type="number" min="1" max={tur === 'foiz' ? 100 : asos} value={foiz} onChange={(e) => setFoiz(e.target.value)} />
      </label>
      {Number(foiz) > 0 && (
        <p className="malumot">Chegirma: {som(miqdor)} · yangi jami: <b>{som(asos - (z.promokod_chegirma || 0) - miqdor)}</b> (rahbar tasdiqlasa)</p>
      )}
      <select value={sabab} onChange={(e) => setSabab(e.target.value)}>
        <option value="doimiy_mijoz">Doimiy mijoz</option>
        <option value="nuqson">Libosda kichik nuqson</option>
        <option value="boshqa">Boshqa</option>
      </select>
      <button disabled={!(Number(foiz) > 0)}
        onClick={() => bajar(() => chegirmaSora(zakazId, tur === 'foiz' ? { foiz, sabab } : { summa: Number(foiz), sabab }), "Rahbar tasdig'iga yuborildi.")}>
        Rahbardan so'rash
      </button>
    </Amal>
  )
}

function BerishForma({ onYuborish, soz }) {
  const TURLAR = [['pul', 'Pul', 'zalog_pul'], ['hujjat', 'Hujjat', 'zalog_hujjat'], ['tillo', 'Tillo buyum', 'zalog_tillo']]
    .filter(([, , k]) => !soz || soz[k])  // admin panelda yoqilgan turlar (FT-7.1)
  const [tanlov, setTuri] = useState('')
  const turi = TURLAR.some(([t]) => t === tanlov) ? tanlov : TURLAR[0]?.[0]
  const [f, setF] = useState({})
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const zalog = turi === 'pul'
    ? { turi, summa: Number(f.summa || 0) }
    : turi === 'hujjat'
      ? { turi, hujjat_turi: f.hujjat_turi, hujjat_raqami: f.hujjat_raqami }
      : { turi, tavsif: f.tavsif, ogirlik_gr: f.ogirlik_gr, summa: Number(f.summa || 0) }
  return (
    <Amal sarlavha="Libosni berish (zalog)" id="asosiy-amal">
      <select value={turi} onChange={(e) => { setTuri(e.target.value); setF({}) }}>
        {TURLAR.map(([t, nom]) => <option key={t} value={t}>{nom}</option>)}
      </select>
      {turi === 'pul' && <label>Zalog summasi<input type="number" onChange={set('summa')} /></label>}
      {turi === 'hujjat' && (<>
        <label>Hujjat turi<input placeholder="pasport" onChange={set('hujjat_turi')} /></label>
        <label>Raqami<input onChange={set('hujjat_raqami')} /></label>
      </>)}
      {turi === 'tillo' && (<>
        <label>Tavsif<input placeholder="uzuk" onChange={set('tavsif')} /></label>
        <label>Og'irligi, g<input type="number" step="0.01" onChange={set('ogirlik_gr')} /></label>
        <label>Taxminiy qiymat<input type="number" onChange={set('summa')} /></label>
      </>)}
      <button onClick={() => onYuborish([zalog])}>Zalogni qabul qilib berish</button>
    </Amal>
  )
}

function QaytarishForma({ onYuborish, baholash }) {
  const [f, setF] = useState({ tekshiruv: 'butun' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const body = {
    tekshiruv: f.tekshiruv, jarima: Number(f.jarima || 0), jarima_tolandi: Number(f.jarima_tolandi || 0),
    ...(f.tortilgan_gr ? { tortilgan_gr: f.tortilgan_gr } : {}),
    ...(f.baho ? { baho: Number(f.baho) } : {}), izoh: f.izoh || '',
  }
  return (
    <Amal sarlavha="Qaytarish" id="asosiy-amal">
      <label>Holat tekshiruvi
        <select value={f.tekshiruv} onChange={set('tekshiruv')}>
          <option value="butun">Butun</option><option value="dog">Dog'</option>
          <option value="yirtiq">Yirtiq</option><option value="aksessuar_yoq">Aksessuar yo'q</option>
        </select>
      </label>
      <label>Jarima<input type="number" min="0" onChange={set('jarima')} /></label>
      <label>Shu zahoti to'langan jarima (zalogdan ortig'i)<input type="number" min="0" onChange={set('jarima_tolandi')} /></label>
      <label>Tillo qayta tortildi, g (agar tillo zalog bo'lsa)<input type="number" step="0.01" onChange={set('tortilgan_gr')} /></label>
      {baholash && <label>Mijoz bahosi (1–5)<input type="number" min="1" max="5" onChange={set('baho')} /></label>}
      <button onClick={() => onYuborish(body)}>Qaytarishni rasmiylashtirish</button>
    </Amal>
  )
}

const PRIMERKA_HOLAT = { rejalashtirilgan: 'rejalashtirilgan', otkazildi: "o'tkazildi", bekor: 'bekor qilingan' }
const vaqtMatni = (v) => new Date(v).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })

const OLCHAMLAR = [['kokrak', "Ko'krak"], ['bel', 'Bel'], ['son', 'Son'], ['boy', "Bo'y"], ['oyoq_olchami', 'Oyoq kiyim']]

// FT-8.4: mijoz o'lchamlari primerkada yangilanadi (keyingi safar libos tanlashda o'lcham filtriga qo'yiladi)
function OlchamForma({ z, bajar }) {
  const [f, setF] = useState({})
  const q = (k) => f[k] ?? z.olchamlar?.[k] ?? ''
  const tana = () => {
    const b = { kiyim_olchami: String(q('kiyim_olchami')) }
    for (const [k] of OLCHAMLAR) b[k] = q(k) === '' ? null : Number(q(k))
    return b
  }
  return (
    <details className="amal">
      <summary>Mijoz o'lchamlari</summary>
      <div className="stack">
        <div className="qator keng olcham-qator">
          {OLCHAMLAR.map(([k, nom]) => (
            <label key={k}>{nom}<input type="number" min="0" value={q(k)} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>
          ))}
        </div>
        <label>Kiyim o'lchami (masalan, 44 yoki M)
          <input value={q('kiyim_olchami')} maxLength={20} onChange={(e) => setF({ ...f, kiyim_olchami: e.target.value })} />
        </label>
        <button type="button" className="ikkinchi" disabled={Object.keys(f).length === 0}
          onClick={() => bajar(() => mijozOzgartir(z.mijoz_id, tana()), "O'lchamlar saqlandi.").then((ok) => ok && setF({}))}>
          O'lchamlarni saqlash
        </button>
      </div>
    </details>
  )
}

// FT-2.8: primerka sanasi va vaqti; moslash kerak bo'lsa narxi zakazga qo'shiladi.
function PrimerkaForma({ z, bajar, ochiq }) {
  const [vaqt, setVaqt] = useState('')
  const [f, setF] = useState({})
  const qiymat = (p, k) => f[`${p.id}_${k}`] ?? p[k] ?? ''
  const set = (p, k) => (e) => setF({ ...f, [`${p.id}_${k}`]: e.target.value })
  return (
    <Amal sarlavha={`Primerka (${z.primerkalar.filter((p) => p.holat !== 'bekor').length})`}>
      {z.primerkalar.map((p) => (
        <div key={p.id} className={`tasdiq ${p.holat === 'bekor' ? 'bajarilgan' : ''}`}>
          <span>
            <b>{vaqtMatni(p.vaqt)}</b> · {PRIMERKA_HOLAT[p.holat]}
            {p.moslash_narxi > 0 && ` · moslash ${som(p.moslash_narxi)}`}
            {p.natija && ` · ${p.natija}`}
          </span>
          {ochiq && p.holat !== 'bekor' && (
            <>
              <label>Natija<input value={qiymat(p, 'natija')} maxLength={300} onChange={set(p, 'natija')} /></label>
              <label>Moslash narxi, so'm (kerak bo'lmasa 0)
                <input type="number" min="0" value={qiymat(p, 'moslash_narxi')} onChange={set(p, 'moslash_narxi')} />
              </label>
              <div className="qator">
                <button className="ikkinchi kichik" onClick={() => bajar(() => primerkaOzgartir(p.id, {
                  natija: String(qiymat(p, 'natija')), moslash_narxi: Number(qiymat(p, 'moslash_narxi')) || 0, holat: 'otkazildi',
                }), 'Primerka natijasi saqlandi.').then((ok) => ok && setF({}))}>O'tkazildi — saqlash</button>
                <button className="ikkinchi kichik" onClick={() => bajar(() => primerkaOzgartir(p.id, { holat: 'bekor' }), 'Primerka bekor qilindi.')}>Bekor qilish</button>
              </div>
            </>
          )}
        </div>
      ))}
      {ochiq && <OlchamForma z={z} bajar={bajar} />}
      {ochiq && (
        <>
          <label>Sana va vaqt
            <input type="datetime-local" value={vaqt} max={`${z.olib_ketish}T23:59`} onChange={(e) => setVaqt(e.target.value)} />
          </label>
          <button disabled={!vaqt}
            onClick={() => bajar(() => primerkaBelgila(z.id, new Date(vaqt).toISOString()), 'Primerka belgilandi.').then((ok) => ok && setVaqt(''))}>
            Primerka belgilash
          </button>
        </>
      )}
    </Amal>
  )
}

function KochirishForma({ onYuborish }) {
  const [dan, setDan] = useState('')
  const [gacha, setGacha] = useState('')
  return (
    <Amal sarlavha="Sanani ko'chirish">
      <label>Olib ketish<input type="date" value={dan} onChange={(e) => setDan(e.target.value)} /></label>
      <label>Qaytarish<input type="date" min={dan} value={gacha} onChange={(e) => setGacha(e.target.value)} /></label>
      <button disabled={!dan || !gacha} onClick={() => onYuborish({ dan, gacha })}>Ko'chirish</button>
    </Amal>
  )
}

function BekorForma({ onYuborish, soz }) {
  const qoida = (soz?.qaytarish_qoidasi || [[30, 100], [7, 50], [0, 0]])
    .map(([kun, foiz]) => (kun > 0 ? `${kun}+ kun — ${foiz}%` : `undan kam — ${foiz}%`)).join(', ')
  const [sabab, setSabab] = useState('')
  const [surov, setSurov] = useState(false)
  return (
    <Amal sarlavha="Zakazni bekor qilish">
      <p className="malumot">Avans qaytarish qoidasi: {qoida}.</p>
      <label>Sabab<input value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
      <button className="xavfli" disabled={!sabab.trim()} onClick={() => setSurov(true)}>Bekor qilish</button>
      {surov && (
        <Tasdiq sarlavha="Zakazni bekor qilasizmi?" tugma="Ha, bekor qilish"
          matn={`Zakaz bekor qilinadi (sabab: ${sabab.trim()}). Avans qaytarish qoidasi: ${qoida}. Bu amalni qaytarib bo'lmaydi.`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish({ sabab }) }} />
      )}
    </Amal>
  )
}
