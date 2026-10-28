import axios from 'axios'
import { useCallback, useEffect, useState } from 'react'
import { sanaMatni, som, xatoMatni } from '../api'
import SummaInput from '../components/SummaInput'
import { ZAKAZ_HOLATLARI } from '../nomlar'
import Shapka from '../components/Shapka'
import Logo from '../components/Logo'

// Platforma egasi alohida token bilan ishlaydi: salon xodimi tokeni bu API ga, bu token esa salon ma'lumotiga yaramaydi.
const TOKEN = 'weddy.platforma_token'
const papi = axios.create({ baseURL: `${import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`}/platforma` })
papi.interceptors.request.use((cfg) => {
  const t = sessionStorage.getItem(TOKEN)
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

const HOLAT = { sinov: 'Sinov', faol: 'Faol', faqat_korish: "Faqat ko'rish", bloklangan: 'Bloklangan' }

// 4.19: salonlarni ulash, bloklash, tarif va obuna. Egasi faqat umumiy faollikni ko'radi (FT-22.5).
// Chap tarafdagi panel (desktopda yon panel, telefonda pastki nav) — rahbar tomonidagi «.pastki» uslubi bilan bir xil.
const BOLIMLAR = [
  ['salonlar', 'Salonlar'],
  ['tariflar', 'Tariflar'],
  ['so\'rovlar', "So'rovlar"],
  ['telegram', 'Telegram bot'],
]

export default function Platforma({ onOrqaga }) {
  const [kirgan, setKirgan] = useState(Boolean(sessionStorage.getItem(TOKEN)))
  const [bolim, setBolim] = useState('salonlar')
  const [menyu, setMenyu] = useState(false)   // telefonda chapdan chiqadigan nav ochiqmi
  const chiqish = () => { sessionStorage.removeItem(TOKEN); setKirgan(false) }
  if (!kirgan) return <Kirish onKirdi={() => setKirgan(true)} onOrqaga={onOrqaga} />
  return (
    <div className="ilova">
      <Shapka ochiq={menyu} onMenyu={() => setMenyu(!menyu)} />
      <main>
        <h1>Libosa · platforma</h1>
        <Panel bolim={bolim} onChiqish={chiqish} />
      </main>
      {menyu && <div className="menyu-parda" onClick={() => setMenyu(false)} />}
      <nav className={`pastki ${menyu ? 'ochiq' : ''}`}>
        {BOLIMLAR.map(([k, nom]) => (
          <button key={k} type="button" className={bolim === k ? 'faol' : ''} onClick={() => { setBolim(k); setMenyu(false) }}>{nom}</button>
        ))}
      </nav>
    </div>
  )
}

function Kirish({ onKirdi, onOrqaga }) {
  const [login, setLogin] = useState('')
  const [parol, setParol] = useState('')
  const [xato, setXato] = useState('')
  const yubor = async (e) => {
    e.preventDefault()
    setXato('')
    try {
      const r = await papi.post('/login/', { login, parol })
      sessionStorage.setItem(TOKEN, r.data.token)
      onKirdi()
    } catch (err) { setXato(xatoMatni(err, "Login yoki parol noto'g'ri.")) }
  }
  return (
    <>
      <button type="button" className="kirish-orqaga ikkinchi kichik" onClick={onOrqaga}>← Bosh sahifa</button>
      <main className="kirish">
        <div className="kirish-panel">
          <Logo className="kirish-logo" />
          {xato && <p className="xato" role="alert">{xato}</p>}
          <form onSubmit={yubor}>
            <p className="kirish-sarlavha">Platformaga <em>kirish</em></p>
            <label>Login<input value={login} onChange={(e) => setLogin(e.target.value)} autoFocus /></label>
            <label>Parol<input type="password" value={parol} onChange={(e) => setParol(e.target.value)} /></label>
            <button type="submit">Kirish</button>
          </form>
        </div>
      </main>
    </>
  )
}

function Panel({ bolim, onChiqish }) {
  const [salonlar, setSalonlar] = useState([])
  const [tariflar, setTariflar] = useState([])
  const [arizalar, setArizalar] = useState([])
  const [sozlamalar, setSozlamalar] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(async () => {
    try {
      const [s, t, a, z] = await Promise.all([papi.get('/salonlar/'), papi.get('/tariflar/'), papi.get('/arizalar/'), papi.get('/sozlamalar/')])
      setSalonlar(s.data); setTariflar(t.data); setArizalar(a.data); setSozlamalar(z.data)
    } catch (e) {
      if (e.response?.status === 401) onChiqish()
      else setXabar({ turi: 'xato', matn: xatoMatni(e) })
    }
  }, [onChiqish])
  useEffect(() => { yukla() }, [yukla])

  const bajar = useCallback(async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }, [yukla])

  return (
    <div className="stack">
      <button className="ikkinchi kichik" onClick={onChiqish}>Chiqish</button>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {bolim === 'telegram' && sozlamalar && <TelegramSozlama s={sozlamalar} bajar={bajar} />}

      {bolim === 'so\'rovlar' && <Arizalar arizalar={arizalar} bajar={bajar} />}

      {bolim === 'tariflar' && (
        <>
          <TarifForma onYuborish={(b) => bajar(() => papi.post('/tariflar/', b), "Tarif qo'shildi.")} />
          {tariflar.length > 0 && (
            <details className="blok amal">
              <summary>Tariflar ({tariflar.length})</summary>
              <div className="stack">
                {tariflar.map((t) => (
                  <TarifTahrir key={`${t.id}-${t.nomi}-${t.oylik_narx}-${t.xodim_limit}-${t.filial_limit}`} t={t}
                    onSaqla={(b, ok) => bajar(() => papi.patch(`/tariflar/${t.id}/`, b), ok)} />
                ))}
              </div>
            </details>
          )}
        </>
      )}

      {bolim === 'salonlar' && (
        <>
          <SalonForma tariflar={tariflar}
            onYuborish={(b) => bajar(() => papi.post('/salonlar/', b), "Salon qo'shildi. Login va boshlang'ich parolni rahbarga bering.")} />
          {salonlar.length === 0 && <p className="malumot">Hali salon yo'q.</p>}
          {salonlar.map((s) => (
            <details key={s.id} className="blok amal">
              <summary>
                {s.nomi} · <span className={s.holat === 'faol' || s.holat === 'sinov' ? '' : 'qizil'}>{HOLAT[s.holat]}</span>
                {s.faqat_korishgacha_kun != null && <span className="qizil"> · to'lov kutilmoqda ({s.faqat_korishgacha_kun} kun)</span>}
              </summary>
              <div className="stack">
                <table className="jadval"><tbody>
                  <tr><td>Login</td><td>{s.login}</td></tr>
                  <tr><td>Rahbar telefoni</td><td>{s.rahbar_telefon || '—'}</td></tr>
                  <tr><td>Tarif</td><td>{s.tarif || '—'}</td></tr>
                  <tr><td>Sinov / obuna tugaydi</td><td>{s.sinov_tugaydi || '—'} / {s.obuna_tugaydi || '—'}</td></tr>
                  <tr><td>Zakazlar soni</td><td>{s.zakazlar_soni}</td></tr>
                  <tr><td>Faol xodimlar</td><td>{s.faol_xodimlar}</td></tr>
                  <tr><td>Oxirgi kirish</td><td>{s.oxirgi_kirish ? s.oxirgi_kirish.slice(0, 16).replace('T', ' ') : '—'}</td></tr>
                </tbody></table>
                <div className="qator">
                  {[1, 3, 12].map((oy) => (
                    <button key={oy} className="ikkinchi kichik"
                      onClick={() => bajar(() => papi.post(`/salonlar/${s.id}/tolov/`, { oylar: oy }), `To'lov belgilandi: ${oy} oy.`)}>
                      To'lov: {oy} oy
                    </button>
                  ))}
                </div>
                <ObunaSana key={`${s.id}-${s.sinov_tugaydi}-${s.obuna_tugaydi}`} s={s} bajar={bajar} />
                <select value={s.tarif_id || ''}
                  onChange={(e) => bajar(() => papi.patch(`/salonlar/${s.id}/`, { tarif: e.target.value ? Number(e.target.value) : null }), "Tarif o'zgartirildi.")}>
                  <option value="">Tarifsiz (limit yo'q)</option>
                  {tariflar.map((t) => <option key={t.id} value={t.id}>{t.nomi} · {som(t.oylik_narx)} · {t.xodim_limit} xodim</option>)}
                </select>
                <button className="ikkinchi kichik"
                  onClick={() => bajar(() => papi.patch(`/salonlar/${s.id}/`, { qurilmalarni_tozala: true }),
                    "Qurilmalar tozalandi: keyingi kirgan qurilma yana ishonchli bo'ladi.")}>
                  Ishonchli qurilmalarni tozalash (rahbar qurilmasini yo'qotganda)
                </button>
                {s.yordam_ruxsati && <Yordam salonId={s.id} />}
                {!s.chiqish_sanasi && (
                  <button className={s.holat === 'bloklangan' ? 'ikkinchi' : 'xavfli'}
                    onClick={() => bajar(() => papi.patch(`/salonlar/${s.id}/`, { bloklangan: s.holat !== 'bloklangan' }),
                      s.holat === 'bloklangan' ? 'Salon blokdan chiqarildi.' : 'Salon bloklandi.')}>
                    {s.holat === 'bloklangan' ? 'Blokdan chiqarish' : 'Bloklash'}
                  </button>
                )}
                <Chiqish s={s} bajar={bajar} />
              </div>
            </details>
          ))}
        </>
      )}
    </div>
  )
}

// FT-22.9: obuna muddatini to'lov tugmalaridan tashqari aniq sana bilan ham belgilash mumkin.
function ObunaSana({ s, bajar }) {
  const [sinov, setSinov] = useState(s.sinov_tugaydi || '')
  const [obuna, setObuna] = useState(s.obuna_tugaydi || '')
  const ozgargan = sinov !== (s.sinov_tugaydi || '') || obuna !== (s.obuna_tugaydi || '')
  const yubor = () => bajar(() => papi.patch(`/salonlar/${s.id}/`, {
    sinov_tugaydi: sinov || null,
    obuna_tugaydi: obuna || null,
  }), "Obuna muddati o'zgartirildi.")
  return (
    <div className="qator">
      <label>Sinov tugaydi (sana)<input type="date" value={sinov} onChange={(e) => setSinov(e.target.value)} /></label>
      <label>Obuna tugaydi (sana)<input type="date" value={obuna} onChange={(e) => setObuna(e.target.value)} /></label>
      <button className="ikkinchi kichik" disabled={!ozgargan} onClick={yubor}>Sanalarni saqlash</button>
    </div>
  )
}

// FT-22.10: salon platformadan chiqsa — rahbarning yozma so'rovi bilan arxiv beriladi, 90 kundan keyin ma'lumotlar o'chiriladi.
function Chiqish({ s, bajar }) {
  const [izoh, setIzoh] = useState('')
  const [xato, setXato] = useState('')
  const yuklab = async () => {
    setXato('')
    try {
      const r = await papi.get(`/salonlar/${s.id}/arxiv/`, { responseType: 'blob' })
      const havola = document.createElement('a')
      havola.href = URL.createObjectURL(r.data)
      havola.download = `libosa-${s.login}-arxiv.json`
      havola.click()
      URL.revokeObjectURL(havola.href)
    } catch (e) { setXato(xatoMatni(e)) }
  }
  if (s.chiqish_sanasi) {
    return (
      <div className="tasdiq">
        <span className="qizil">
          Platformadan chiqqan: {s.chiqish_sanasi}. Ma'lumotlar {s.ochiriladi} dan keyin o'chiriladi.
        </span>
        <span className="malumot">Asos: {s.chiqish_izohi}</span>
        {xato && <p className="xato">{xato}</p>}
        <div className="qator">
          <button className="ikkinchi kichik" onClick={yuklab}>Arxivni yuklab olish (JSON)</button>
          <button className="ikkinchi kichik" onClick={() => bajar(() => papi.delete(`/salonlar/${s.id}/chiqish/`), 'Chiqish bekor qilindi.')}>
            Chiqishni bekor qilish
          </button>
        </div>
      </div>
    )
  }
  return (
    <details className="amal">
      <summary>Salon platformadan chiqdi</summary>
      <div className="stack">
        <p className="malumot">
          Salon bloklanadi, ma'lumotlari arxiv sifatida beriladi va 90 kundan keyin butunlay o'chiriladi. Shu muddat ichida bekor qilish mumkin.
        </p>
        <label>Asos (rahbarning yozma so'rovi: sana, kimdan)
          <input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} />
        </label>
        <button className="xavfli" disabled={!izoh.trim()}
          onClick={() => bajar(() => papi.post(`/salonlar/${s.id}/chiqish/`, { izoh }), 'Salon platformadan chiqqan deb belgilandi.').then((ok) => ok && setIzoh(''))}>
          Chiqqan deb belgilash
        </button>
      </div>
    </details>
  )
}

const MANBA = { panel: 'panelda kiritilgan', env: 'server sozlamasidan (.env)', yoq: 'kiritilmagan' }

// FT-4.14: butun platformaga bitta Libosa boti xizmat qiladi. Har bir salonga alohida bot qilinsa, 100 salon
// 100 ta jarayon bo'lib bitta bot akkauntining limitidan navbat bilan foydalanardi — ulanish ham, xabar ham
// sekinlashardi. Shuning uchun tokenni faqat platforma egasi shu yerdan kiritadi.
function TelegramSozlama({ s, bajar }) {
  const [token, setToken] = useState('')
  const [nomi, setNomi] = useState('')
  const [ulash, setUlash] = useState(null)

  // Kod ko'rsatilgandan keyin egasi botga ulanganini tekshirib turadi
  useEffect(() => {
    if (!ulash) return undefined
    const t = setInterval(async () => {
      try {
        const r = await papi.get('/sozlamalar/')
        if (r.data.telegram_ega_ulangan) { setUlash(null); bajar(async () => {}, '') }
      } catch { /* keyingi urinishda tekshiramiz */ }
    }, 3000)
    return () => clearInterval(t)
  }, [ulash, bajar])

  const yubor = async () => {
    const tana = {}
    if (token.trim()) tana.telegram_token = token.trim()
    if (nomi.trim()) tana.telegram_bot_nomi = nomi.trim()
    if (await bajar(() => papi.patch('/sozlamalar/', tana), 'Telegram boti saqlandi.')) { setToken(''); setNomi('') }
  }

  const ulashBoshlash = () => bajar(async () => {
    const r = await papi.post('/sozlamalar/telegram-ulash/')
    setUlash(r.data)
  }, "Kod tayyor. Telegram'da botga yuboring.")

  return (
    <details className="blok amal">
      <summary>
        Telegram bot · {MANBA[s.telegram_manba]}
        {s.telegram_bot_nomi && ` (@${s.telegram_bot_nomi})`}
        {!s.telegram_ulangan && <span className="qizil"> · ishlamayapti</span>}
      </summary>
      <div className="stack">
        <p className="malumot">
          Butun platformaga <b>bitta</b> Libosa boti xizmat qiladi: har bir salon xodimi shu bot orqali ulanadi.
          Boshqa salonlar ham shu tokenni ishlatadi — almashtirsangiz, hammasi yangi botga o'tadi.
        </p>
        <label>Bot tokeni (BotFather beradi: 123456:ABC…)
          <input type="password" autoComplete="new-password" value={token} onChange={(e) => setToken(e.target.value)}
            placeholder={s.telegram_kiritilgan ? 'kiritilgan — almashtirish uchun yangisini yozing' : ''} />
        </label>
        <label>Bot nomi (@ belgisisiz, ixtiyoriy)
          <input value={nomi} maxLength={32} onChange={(e) => setNomi(e.target.value)}
            placeholder={s.telegram_bot_nomi || "token tekshirilgach o'zi to'ladi"} />
        </label>
        <div className="qator">
          <button type="button" className="ikkinchi" disabled={!token.trim() && !nomi.trim()} onClick={yubor}>Saqlash</button>
          {s.telegram_kiritilgan && (
            <button type="button" className="ikkinchi" onClick={() => bajar(() => papi.patch('/sozlamalar/', { telegram_token: '' }), 'Bot uzildi.')}>
              Botni uzish
            </button>
          )}
        </div>
        <p className="malumot">
          Token saqlanmasdan oldin Telegram'da tekshiriladi — xato token butun platformani botsiz qoldirmasin.
          Saqlangach qayta ko'rsatilmaydi.
        </p>

        {s.telegram_ulangan && (
          s.telegram_ega_ulangan ? (
            <div className="qator">
              <span className="malumot">Siz botga ulangansiz — «a'zo bo'lish» so'rovlari Telegram'ingizga keladi.</span>
              <button type="button" className="ikkinchi" onClick={() => bajar(() => papi.delete('/sozlamalar/telegram-ulash/'), 'Telegram uzildi.')}>
                Ulanishni uzish
              </button>
            </div>
          ) : ulash ? (
            <>
              <p>Telegramda botni oching{s.telegram_bot_nomi ? <> (<b>@{s.telegram_bot_nomi}</b>)</> : ''} va shu xabarni yuboring:</p>
              <p className="kod">/start {ulash.kod}</p>
              {ulash.havola && <a className="tugma-havola" href={ulash.havola} target="_blank" rel="noreferrer">Botni ochish</a>}
              <p className="malumot">Kod 15 daqiqa amal qiladi. Ulangach bu oyna o'zi yangilanadi.</p>
            </>
          ) : (
            <button type="button" className="ikkinchi" onClick={ulashBoshlash}>Telegramni ulash (men — egasi)</button>
          )
        )}
      </div>
    </details>
  )
}

function SalonForma({ tariflar, onYuborish }) {
  const [f, setF] = useState({})
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tayyor = f.nomi && f.login && (f.parol || '').length >= 8 && f.rahbar_ismi && /^\d{4,6}$/.test(f.rahbar_pin || '')
  const yubor = async () => {
    const body = { ...f, ...(f.tarif ? { tarif: Number(f.tarif) } : {}) }
    if (!f.tarif) delete body.tarif
    if (await onYuborish(body)) setF({})
  }
  return (
    <details className="blok amal">
      <summary>Salon qo'shish</summary>
      <div className="stack">
        <label>Salon nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Manzil<input value={f.manzil || ''} onChange={set('manzil')} /></label>
        <label>Salon logini (kichik lotin harflari)<input value={f.login || ''} onChange={set('login')} /></label>
        <label>Boshlang'ich parol (kamida 8 belgi)<input type="password" value={f.parol || ''} onChange={set('parol')} /></label>
        <label>Rahbar ismi<input value={f.rahbar_ismi || ''} onChange={set('rahbar_ismi')} /></label>
        <label>Rahbar telefoni<input inputMode="tel" value={f.rahbar_telefon || ''} onChange={set('rahbar_telefon')} /></label>
        <label>Rahbar PIN kodi (4–6 raqam)<input type="password" inputMode="numeric" maxLength={6} value={f.rahbar_pin || ''} onChange={set('rahbar_pin')} /></label>
        <select value={f.tarif || ''} onChange={set('tarif')}>
          <option value="">Tarifsiz</option>
          {tariflar.map((t) => <option key={t.id} value={t.id}>{t.nomi}</option>)}
        </select>
        <p className="malumot">Salon 14 kunlik sinov muddati va standart kategoriyalar bilan yaratiladi.</p>
        <button disabled={!tayyor} onClick={yubor}>Qo'shish</button>
      </div>
    </details>
  )
}

function TarifForma({ onYuborish }) {
  const [f, setF] = useState({})
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <details className="blok amal">
      <summary>Tarif qo'shish</summary>
      <div className="stack">
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Oylik narx<SummaInput value={f.oylik_narx || ''} onChange={set('oylik_narx')} /></label>
        <label>Xodimlar limiti<input type="number" min="1" max="50" value={f.xodim_limit || ''} onChange={set('xodim_limit')} /></label>
        <button disabled={!f.nomi || !f.xodim_limit}
          onClick={() => onYuborish({ nomi: f.nomi, oylik_narx: Number(f.oylik_narx || 0), xodim_limit: Number(f.xodim_limit) }).then((ok) => ok && setF({}))}>
          Qo'shish
        </button>
      </div>
    </details>
  )
}

// Bosh sahifadagi «A'zo bo'lish» va «Bog'lanish» formalaridan kelgan so'rovlar.
function Arizalar({ arizalar, bajar }) {
  const yangi = arizalar.filter((a) => !a.korilgan).length
  return (
    <details className="blok amal" open={yangi > 0}>
      <summary>So'rovlar ({arizalar.length}){yangi > 0 && <span className="qizil"> · {yangi} ta yangi</span>}</summary>
      <div className="stack">
        {arizalar.length === 0 && <p className="malumot">Hali so'rov yo'q.</p>}
        {arizalar.map((a) => (
          <div key={a.id} className={`tasdiq ${a.korilgan ? 'bajarilgan' : ''}`}>
            <span>
              <b>{a.tur === 'azo' ? "A'zo bo'lish" : "Bog'lanish"}</b> · {a.ism} · <a href={`tel:${a.telefon.replace(/[^+\d]/g, '')}`}>{a.telefon}</a>
              {a.salon_nomi ? ` · ${a.salon_nomi}` : ''} · {a.yaratilgan.slice(0, 16).replace('T', ' ')}
            </span>
            {a.xabar && <p className="qator-matn">{a.xabar}</p>}
            <div className="qator">
              <button className="ikkinchi kichik"
                onClick={() => bajar(() => papi.patch(`/arizalar/${a.id}/`, { korilgan: !a.korilgan }), a.korilgan ? 'Yangi deb belgilandi.' : "Ko'rilgan deb belgilandi.")}>
                {a.korilgan ? 'Yangi deb belgilash' : "Ko'rildi"}
              </button>
              <button className="ikkinchi kichik" onClick={() => bajar(() => papi.delete(`/arizalar/${a.id}/`), "So'rov o'chirildi.")}>O'chirish</button>
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}

// Tarifni tuzatish yoki yopish. Salon ulangan tarifni server yopishga qo'ymaydi.
function TarifTahrir({ t, onSaqla }) {
  const [f, setF] = useState({ nomi: t.nomi, oylik_narx: t.oylik_narx, xodim_limit: t.xodim_limit, filial_limit: t.filial_limit })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="tasdiq">
      <label>Nomi<input value={f.nomi} maxLength={100} onChange={set('nomi')} /></label>
      <label>Oylik narx<SummaInput value={f.oylik_narx} onChange={set('oylik_narx')} /></label>
      <div className="qator">
        <label>Xodimlar limiti<input type="number" min="1" max="50" value={f.xodim_limit} onChange={set('xodim_limit')} /></label>
        <label>Filiallar limiti<input type="number" min="1" max="10" value={f.filial_limit} onChange={set('filial_limit')} /></label>
      </div>
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!f.nomi.trim() || !(Number(f.xodim_limit) > 0) || !(Number(f.filial_limit) > 0)}
          onClick={() => onSaqla({ nomi: f.nomi.trim(), oylik_narx: Number(f.oylik_narx || 0), xodim_limit: Number(f.xodim_limit),
            filial_limit: Number(f.filial_limit) }, 'Tarif saqlandi.')}>Saqlash</button>
        <button className="xavfli kichik" onClick={() => onSaqla({ faol: false }, 'Tarif yopildi.')}>Tarifni yopish</button>
      </div>
    </div>
  )
}

// FT-22.5: faqat rahbar bergan muddatli ruxsat bilan, faqat o'qish; har bir ochish salon jurnaliga yoziladi.
function Yordam({ salonId }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  if (!d) {
    return (
      <>
        <button className="ikkinchi" onClick={() => papi.get(`/salonlar/${salonId}/yordam/`).then((r) => setD(r.data)).catch((e) => setXato(xatoMatni(e)))}>
          Yordam ko'rinishini ochish (jurnalga yoziladi)
        </button>
        {xato && <p className="xato">{xato}</p>}
      </>
    )
  }
  return (
    <div className="stack">
      <p className="malumot">Shu oy: tushum {som(d.shu_oy.tushum)}, sof foyda {som(d.shu_oy.sof_foyda)}. Oxirgi zakazlar:</p>
      {d.zakazlar.map((z) => (
        <p key={z.raqam} className="qator-matn">#{z.raqam} · {z.mijoz} · {sanaMatni(z.olib_ketish)} · {ZAKAZ_HOLATLARI[z.holat] || z.holat} · {som(z.jami)}</p>
      ))}
    </div>
  )
}
