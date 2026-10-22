import { useCallback, useEffect, useState } from 'react'
import Tasdiq from '../components/Tasdiq'
import {
  kassaZaloglar, smenaChiqish, smenaHolati, smenaOchish, smenaQoshilish, smenaTuzat, smenaYopish, smenalar, som, tolovQabul,
  xarajatModdalari, xarajatYarat, xatoMatni, zalogBelgila,
  sanaMatni,
} from '../api'

// Sotuvchi kassadan to'laydigan kundalik xarajatlar; salonning o'z moddalari ham chiqadi (FT-13.1)
const KASSA_MODDALARI = ['tozalash', 'tamir', 'transport', 'kommunal', 'reklama', 'boshqa']

// 4.12: bitta umumiy smena, sotuvchilar o'z akkauntidan qo'shiladi, kun oxirida naqd sanaladi.
export default function Kassa({ rahbar, bolim, onHolatOzgardi }) {
  const [s, setS] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  // Smena holati App'dagi nav tugmalariga ham kerak: yuklangach yoki o'zgargach onHolatOzgardi chaqiriladi.
  const yukla = useCallback(() => smenaHolati().then((r) => { setS(r); onHolatOzgardi?.() }), [onHolatOzgardi])
  useEffect(() => { yukla() }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      const r = await fn()
      setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(r) : ok })
      await yukla()
      return true
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
      return false
    }
  }

  if (!s) return <p className="malumot">Yuklanmoqda…</p>

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {s.filial && <p className="malumot">Kassa: <b>{s.filial}</b> filiali</p>}
      {!s.ochiq ? (
        bolim === 'tarix' && rahbar ? (
          <YopilganSmenalar />
        ) : (
          <SmenaOchish onOchish={(q) => bajar(() => smenaOchish(q), 'Smena ochildi.')} />
        )
      ) : (
        <>
          {bolim === 'hisobot' && (
            <>
              <section className="blok">
                <h2>Smena ochiq</h2>
                <p>Ishlayotganlar: {s.ishtirokchilar.join(', ')}</p>
                {!s.men_ishtirokchi && (
                  <button className="ikkinchi" onClick={() => bajar(smenaQoshilish, "Smenaga qo'shildingiz.")}>
                    Smenaga qo'shilish
                  </button>
                )}
              </section>
              <Hisobot h={s.hisobot} />
            </>
          )}
          {bolim === 'xarajat' && (
            <XarajatForma onYuborish={(b) => bajar(() => xarajatYarat({ ...b, kassadan: true }), rahbar ? 'Xarajat kassadan yozildi.' : "Xarajat kassadan yozildi (rahbar tasdig'ini kutadi).")} />
          )}
          {bolim === 'inkassatsiya' && (
            <Inkassatsiya onYuborish={(summa, izoh) => bajar(() => tolovQabul({ tur: 'inkassatsiya', summa, izoh }), 'Inkassatsiya yozildi.')} />
          )}
          {bolim === 'zalog' && <ZalogTekshiruvi soni={s.zalog_tekshirilmagan} onOzgardi={yukla} />}
          {bolim === 'chiqish' && (
            <Sanash sarlavha="Smenadan chiqish (boshqa sotuvchi qoladi)"
              tugma="Naqdni sanab chiqish" izohsiz
              onYuborish={(summa) => bajar(() => smenaChiqish(summa), (r) => `Chiqdingiz. Farq: ${som(r.farq)}`)} />
          )}
          {bolim === 'yopish' && (
            <Sanash sarlavha="Smenani yopish (oxirgi sotuvchi)" tugma="Smenani yopish" tasdiqMatn="Smena yopiladi, keyin to'lov qabul qilib bo'lmaydi."
              onYuborish={(summa, izoh) => bajar(() => smenaYopish(summa, izoh), (r) => `Smena yopildi. Farq: ${som(r.farq)}`)} />
          )}
          {bolim === 'tarix' && rahbar && <YopilganSmenalar />}
        </>
      )}
    </div>
  )
}

function SmenaOchish({ onOchish }) {
  const [q, setQ] = useState('')
  return (
    <section className="blok stack">
      <h2>Smena yopiq</h2>
      <label>Boshlang'ich qoldiq (kassadagi naqd pul)
        <input type="number" min="0" value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      <button disabled={q === ''} onClick={() => onOchish(Number(q))}>Smenani ochish</button>
    </section>
  )
}

function Hisobot({ h }) {
  const qatorlar = [
    ['Kun boshidagi qoldiq', h.kun_boshidagi_qoldiq], ['Tushum (avans + qoldiq + jarima)', h.tushum],
    ['Olingan pul zaloglar', h.olingan_zaloglar], ['Qaytarilgan zaloglar', -h.qaytarilgan_zaloglar],
    ['Xarajatlar', -h.xarajatlar], ['Pulni qaytarish va inkassatsiya', -h.vozvrat_va_inkassatsiya],
  ]
  return (
    <section className="blok">
      <h3>Naqd pul hisobi</h3>
      <table className="jadval"><tbody>
        {qatorlar.map(([n, v]) => <tr key={n}><td>{n}</td><td>{som(v)}</td></tr>)}
        <tr><td><b>Hisobdagi qoldiq</b></td><td><b>{som(h.hisobdagi_qoldiq)}</b></td></tr>
      </tbody></table>
      {Object.keys(h.sotuvchilar).length > 0 && (
        <p className="malumot">Kirimlar: {Object.entries(h.sotuvchilar).map(([k, v]) => `${k} — ${som(v)}`).join('; ')}</p>
      )}
    </section>
  )
}

function XarajatForma({ onYuborish }) {
  const [modda, setModda] = useState('transport')
  const [moddalar, setModdalar] = useState([])
  useEffect(() => {
    xarajatModdalari().then((m) => setModdalar(m.filter((x) => !x.standart || KASSA_MODDALARI.includes(x.kod)))).catch(() => {})
  }, [])
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  return (
    <details className="blok amal">
      <summary>Xarajat kiritish (kassadan chiqim)</summary>
      <div className="stack">
        <select value={modda} onChange={(e) => setModda(e.target.value)}>
          {moddalar.map((m) => <option key={m.kod} value={m.kod}>{m.nomi}</option>)}
        </select>
        <label>Summa<input type="number" min="1" value={summa} onChange={(e) => setSumma(e.target.value)} /></label>
        <label>Izoh<input value={izoh} onChange={(e) => setIzoh(e.target.value)} /></label>
        <button disabled={!summa}
          onClick={() => onYuborish({ modda, summa: Number(summa), izoh }).then((ok) => ok && (setSumma(''), setIzoh('')))}>
          Kiritish
        </button>
      </div>
    </details>
  )
}

function Sanash({ sarlavha, tugma, onYuborish, izohsiz, tasdiqMatn }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const [surov, setSurov] = useState(false)
  return (
    <details className="blok amal">
      <summary>{sarlavha}</summary>
      <div className="stack">
        <label>Sanalgan naqd pul<input type="number" min="0" value={summa} onChange={(e) => setSumma(e.target.value)} /></label>
        {!izohsiz && <label>Izoh (farq bo'lsa majburiy)<input value={izoh} onChange={(e) => setIzoh(e.target.value)} /></label>}
        <button disabled={summa === ''} onClick={() => (tasdiqMatn ? setSurov(true) : onYuborish(Number(summa), izoh))}>{tugma}</button>
        {surov && (
          <Tasdiq sarlavha={`${tugma}?`} tugma={tugma} matn={`${tasdiqMatn} Sanalgan naqd: ${Number(summa).toLocaleString('ru-RU')} so'm.`}
            onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish(Number(summa), izoh) }} />
        )}
      </div>
    </details>
  )
}

// FT-12.6: rahbarga topshirilgan naqd pul — alohida chiqim, tushum va xarajatga kirmaydi.
function Inkassatsiya({ onYuborish }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  return (
    <details className="blok amal">
      <summary>Inkassatsiya (naqd pulni rahbarga topshirish)</summary>
      <div className="stack">
        <label>Summa<input type="number" min="1" value={summa} onChange={(e) => setSumma(e.target.value)} /></label>
        <label>Izoh (kimga topshirildi)<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>
        <button disabled={!(Number(summa) > 0)} onClick={() => onYuborish(Number(summa), izoh).then((ok) => ok && (setSumma(''), setIzoh('')))}>Yozish</button>
      </div>
    </details>
  )
}

// FT-12.5: kun oxirida salonda saqlanayotgan hujjat va tillo zaloglar «joyida» deb belgilanadi.
function ZalogTekshiruvi({ soni, onOzgardi }) {
  const [royxat, setRoyxat] = useState(null)
  const [izoh, setIzoh] = useState({})
  const [xato, setXato] = useState('')
  const yukla = () => kassaZaloglar().then((r) => setRoyxat(r.zaloglar)).catch((e) => setXato(xatoMatni(e)))
  const belgila = async (z, joyida) => {
    setXato('')
    try { setRoyxat((await zalogBelgila({ zalog: z.id, joyida, izoh: izoh[z.id] || '' })).zaloglar); onOzgardi?.() } catch (e) { setXato(xatoMatni(e)) }
  }
  return (
    <details className="blok amal" onToggle={(e) => e.target.open && yukla()}>
      <summary>Zaloglarni tekshirish{soni > 0 ? ` (${soni} ta tekshirilmagan)` : ''}</summary>
      <div className="stack">
        {xato && <p className="xato">{xato}</p>}
        {royxat && royxat.length === 0 && <p className="malumot">Salonda saqlanayotgan hujjat yoki tillo zalog yo'q.</p>}
        {royxat && royxat.map((z) => (
          <div key={z.id} className="tasdiq">
            <span>
              <b>{z.yorliq}</b> · {z.tavsif} · zakaz #{z.zakaz_raqami} ({z.mijoz})
              {z.joyida === true && ' · joyida ✓'}{z.joyida === false && <b className="qizil"> · JOYIDA EMAS</b>}
            </span>
            <div className="qator">
              <button className={z.joyida === true ? 'kichik' : 'ikkinchi kichik'} onClick={() => belgila(z, true)}>Joyida</button>
              <input placeholder="Yo'q bo'lsa izoh" value={izoh[z.id] || ''} maxLength={300} onChange={(e) => setIzoh({ ...izoh, [z.id]: e.target.value })} />
              <button className="ikkinchi kichik" disabled={!(izoh[z.id] || '').trim()} onClick={() => belgila(z, false)}>Yo'q</button>
            </div>
          </div>
        ))}
        <p className="malumot">Smenani yopishdan oldin har bir zalogni seyfdan tekshirib belgilang. Tekshirilmagan yoki yo'q zalog haqida rahbarga xabar boradi.</p>
      </div>
    </details>
  )
}

// FT-12.11: yopilgan smenani faqat rahbar o'zgartiradi (qayta sanash natijasi); o'zgarish jurnalga yoziladi.
function YopilganSmenalar() {
  const [royxat, setRoyxat] = useState(null)
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const yukla = () => smenalar().then(setRoyxat).catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) }))
  const saqla = async (s) => {
    setXabar({ turi: '', matn: '' })
    try {
      await smenaTuzat(s.id, { fakt_qoldiq: Number(f[`${s.id}_q`] ?? s.fakt_qoldiq), izoh: f[`${s.id}_i`] ?? s.izoh })
      setF({}); setXabar({ turi: 'ok', matn: 'Smena tuzatildi.' }); await yukla()
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }
  return (
    <details className="blok amal" onToggle={(e) => e.target.open && yukla()}>
      <summary>Smenalar tarixi</summary>
      <div className="stack">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        {royxat && royxat.length === 0 && <p className="malumot">Smena yo'q.</p>}
        {royxat && royxat.map((s) => (
          <div key={s.id} className="tasdiq">
            <span>
              <b>{sanaMatni(s.sana)}</b>{s.filial ? ` · ${s.filial}` : ''} · {s.ochgan} · {s.yopilgan
                ? <>hisobda {som(s.hisobdagi_qoldiq)}, sanaldi {som(s.fakt_qoldiq)}, farq <b className={s.farq ? 'qizil' : ''}>{som(s.farq)}</b></>
                : 'ochiq'}
              {s.zalog_tekshirilmagan > 0 && <span className="qizil"> · {s.zalog_tekshirilmagan} ta zalog tekshirilmagan</span>}
              {s.zalog_yoq > 0 && <b className="qizil"> · {s.zalog_yoq} ta zalog joyida emas</b>}
              {s.izoh && ` · ${s.izoh}`}
            </span>
            {s.yopilgan && (
              <div className="qator">
                <input type="number" min="0" aria-label="Fakt qoldiq" value={f[`${s.id}_q`] ?? s.fakt_qoldiq} onChange={(e) => setF({ ...f, [`${s.id}_q`]: e.target.value })} />
                <input placeholder="Izoh" aria-label="Izoh" value={f[`${s.id}_i`] ?? s.izoh} onChange={(e) => setF({ ...f, [`${s.id}_i`]: e.target.value })} />
                <button className="ikkinchi kichik" onClick={() => saqla(s)}>Tuzatish</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </details>
  )
}
