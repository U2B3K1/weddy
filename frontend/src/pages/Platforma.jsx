import axios from 'axios'
import { Fragment, useCallback, useEffect, useState } from 'react'
import { sanaMatni, som, xatoMatni } from '../api'
import SummaInput from '../components/SummaInput'
import { ZAKAZ_HOLATLARI } from '../nomlar'
import Shapka from '../components/Shapka'
import Logo from '../components/Logo'
import NavIkona from '../components/NavIkona'
import Oyna from '../components/Oyna'
import { BELGI_D } from './ezazBelgi'

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
// Chap panel, yuqori panel, ko'rsatkichlar va jadval — rahbar ilovasi bilan bir xil sinflar (ichki.css).
const BOLIMLAR = [
  ['salonlar', 'Salonlar', 'bino'],
  ['tariflar', 'Tariflar', 'yorliq'],
  ['so\'rovlar', "So'rovlar", 'mijozlar'],
  ['telegram', 'Telegram bot', 'xabar'],
]

export default function Platforma({ onOrqaga }) {
  const [kirgan, setKirgan] = useState(Boolean(sessionStorage.getItem(TOKEN)))
  const [bolim, setBolim] = useState('salonlar')
  const [menyu, setMenyu] = useState(false)   // telefonda chapdan chiqadigan nav ochiqmi
  const chiqish = useCallback(() => { sessionStorage.removeItem(TOKEN); setKirgan(false) }, [])
  if (!kirgan) return <Kirish onKirdi={() => setKirgan(true)} onOrqaga={onOrqaga} />
  return (
    <div className="ilova">
      <Shapka ochiq={menyu} onMenyu={() => setMenyu(!menyu)}>
        <button className="ikkinchi kichik" onClick={chiqish}>Chiqish</button>
      </Shapka>
      <main>
        <header className="ustki">
          <div className="ustki-nom">
            <h1>{BOLIMLAR.find(([k]) => k === bolim)[1]}</h1>
            <p>Libosa · platforma egasi</p>
          </div>
          <button type="button" className="ikkinchi kichik" onClick={chiqish}><NavIkona nom="almashtir" className="tugma-ikon" />Chiqish</button>
        </header>
        <Panel bolim={bolim} onChiqish={chiqish} />
      </main>
      {menyu && <div className="menyu-parda" onClick={() => setMenyu(false)} />}
      <nav className={`pastki ${menyu ? 'ochiq' : ''}`} aria-label="Bo'limlar">
        <div className="nav-brend">
          <svg viewBox="-60 -40 640 640" aria-hidden="true"><path d={BELGI_D} fill="currentColor" /></svg>
          <span className="nav-brend-matn"><b>LIBOSA</b><small>Platforma</small></span>
        </div>
        <div className="nav-asosiy">
          {BOLIMLAR.map(([k, nom, ikon]) => (
            <button key={k} type="button" className={bolim === k ? 'faol' : undefined} aria-label={nom} aria-current={bolim === k ? 'page' : undefined}
              onClick={() => { setBolim(k); setMenyu(false); window.scrollTo(0, 0) }}>
              <NavIkona nom={ikon} /><span className="nav-nom">{nom}</span>
            </button>
          ))}
        </div>
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
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {bolim === 'telegram' && sozlamalar && <TelegramSozlama s={sozlamalar} bajar={bajar} />}

      {bolim === 'so\'rovlar' && <Arizalar arizalar={arizalar} bajar={bajar} />}

      {bolim === 'tariflar' && <TariflarBolimi tariflar={tariflar} bajar={bajar} />}

      {bolim === 'salonlar' && <SalonlarBolimi salonlar={salonlar} tariflar={tariflar} bajar={bajar} />}
    </div>
  )
}

const HOLAT_SINF = { sinov: 'vaqtinchalik', faol: 'berildi', faqat_korish: 'qarz', bloklangan: 'qarz' }

// Salonlar: ko'rsatkichlar, asboblar paneli, ustunli jadval; qator bosilsa tafsilot shu joyda ochiladi; qo'shish — oynada.
function SalonlarBolimi({ salonlar, tariflar, bajar }) {
  const [oyna, setOyna] = useState(false)
  const [ochiq, setOchiq] = useState(null)
  const [holat, setHolat] = useState('')
  const [q, setQ] = useState('')
  const kutayotgan = salonlar.filter((s) => s.faqat_korishgacha_kun != null || s.holat === 'faqat_korish').length
  const soz = q.trim().toLowerCase()
  const korinadi = salonlar.filter((s) => (!holat || s.holat === holat)
    && (!soz || `${s.nomi} ${s.login} ${s.rahbar_telefon || ''}`.toLowerCase().includes(soz)))
  return (
    <>
      <div className="stat-qator">
        <div className="stat"><span>Jami salonlar</span><b>{salonlar.length}</b></div>
        <div className="stat"><span>Faol</span><b>{salonlar.filter((s) => s.holat === 'faol').length}</b></div>
        <div className="stat"><span>Sinov muddatida</span><b>{salonlar.filter((s) => s.holat === 'sinov').length}</b></div>
        <div className="stat"><span>To'lov kutilmoqda / bloklangan</span><b>{kutayotgan + salonlar.filter((s) => s.holat === 'bloklangan').length}</b></div>
      </div>

      {oyna && (
        <Oyna sarlavha="Salon qo'shish" onYop={() => setOyna(false)}>
          <SalonForma tariflar={tariflar}
            onYuborish={async (b) => {
              const ok = await bajar(() => papi.post('/salonlar/', b), "Salon qo'shildi. Login va boshlang'ich parolni rahbarga bering.")
              if (ok) setOyna(false)
              return ok
            }} />
        </Oyna>
      )}

      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Salonlar</h3>
          <div className="tezkor-tablar" role="tablist" aria-label="Holat">
            {[['', 'Hammasi'], ...Object.entries(HOLAT)].map(([k, nom]) => (
              <button key={k || 'hammasi'} type="button" role="tab" aria-selected={holat === k} className={holat === k ? 'faol' : ''} onClick={() => setHolat(k)}>{nom}</button>
            ))}
          </div>
          <label className="qidiruv-maydon">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Nom, login yoki telefon" aria-label="Salon qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <button type="button" className="kichik" onClick={() => setOyna(true)}><NavIkona nom="qosh" className="tugma-ikon" />Salon qo'shish</button>
        </div>
        {korinadi.length === 0 ? (
          <p className="malumot jadval-bosh">{salonlar.length === 0 ? "Hali salon yo'q — birinchisini qo'shing." : "Bu filtr bo'yicha salon yo'q."}</p>
        ) : (
          <div className="jadval-ora">
            <table className="zakaz-jadval aks-jadval">
              <thead>
                <tr><th>Salon</th><th>Holat</th><th className="tor-yashir">Tarif</th><th className="tor-yashir">Obuna tugaydi</th><th className="ong">Zakazlar</th></tr>
              </thead>
              <tbody>
                {korinadi.map((s) => (
                  <Fragment key={s.id}>
                    <tr className={ochiq === s.id ? 'ochiq' : ''} onClick={() => setOchiq(ochiq === s.id ? null : s.id)}>
                      <td>
                        <button type="button" className="zakaz-katak" aria-expanded={ochiq === s.id}>
                          <span className="kod-belgi">{(s.nomi || '?').trim().charAt(0).toUpperCase()}</span>
                          <span className="zakaz-nom"><b>{s.nomi}</b><small>{s.login}</small></span>
                        </button>
                      </td>
                      <td>
                        <span className={`holat ${HOLAT_SINF[s.holat] || ''}`}>{HOLAT[s.holat]}</span>
                        {s.faqat_korishgacha_kun != null && <small className="qizil"> {s.faqat_korishgacha_kun} kun</small>}
                      </td>
                      <td className="tor-yashir">{s.tarif || '—'}</td>
                      <td className="tor-yashir">{s.obuna_tugaydi || s.sinov_tugaydi || '—'}</td>
                      <td className="ong"><b>{s.zakazlar_soni}</b></td>
                    </tr>
                    {ochiq === s.id && (
                      <tr className="tafsilot-qator"><td colSpan={5}><SalonTafsilot s={s} tariflar={tariflar} bajar={bajar} /></td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}

function SalonTafsilot({ s, tariflar, bajar }) {
  return (
    <div className="aks-tafsilot">
      <div className="stack">
        <h4>Ma'lumot</h4>
        <table className="jadval"><tbody>
          <tr><td>Login</td><td>{s.login}</td></tr>
          <tr><td>Rahbar telefoni</td><td>{s.rahbar_telefon || '—'}</td></tr>
          <tr><td>Sinov / obuna tugaydi</td><td>{s.sinov_tugaydi || '—'} / {s.obuna_tugaydi || '—'}</td></tr>
          <tr><td>Faol xodimlar</td><td>{s.faol_xodimlar}</td></tr>
          <tr><td>Oxirgi kirish</td><td>{s.oxirgi_kirish ? s.oxirgi_kirish.slice(0, 16).replace('T', ' ') : '—'}</td></tr>
        </tbody></table>
        {s.yordam_ruxsati && <Yordam salonId={s.id} />}
        <Chiqish s={s} bajar={bajar} />
      </div>
      <div className="stack">
        <h4>Obuna va tarif</h4>
        <div className="qator">
          {[1, 3, 12].map((oy) => (
            <button key={oy} className="ikkinchi kichik"
              onClick={() => bajar(() => papi.post(`/salonlar/${s.id}/tolov/`, { oylar: oy }), `To'lov belgilandi: ${oy} oy.`)}>
              To'lov: {oy} oy
            </button>
          ))}
        </div>
        <ObunaSana key={`${s.id}-${s.sinov_tugaydi}-${s.obuna_tugaydi}`} s={s} bajar={bajar} />
        <select value={s.tarif_id || ''} aria-label="Tarif"
          onChange={(e) => bajar(() => papi.patch(`/salonlar/${s.id}/`, { tarif: e.target.value ? Number(e.target.value) : null }), "Tarif o'zgartirildi.")}>
          <option value="">Tarifsiz (limit yo'q)</option>
          {tariflar.map((t) => <option key={t.id} value={t.id}>{t.nomi} · {som(t.oylik_narx)} · {t.xodim_limit} xodim</option>)}
        </select>
        <button className="ikkinchi kichik"
          onClick={() => bajar(() => papi.patch(`/salonlar/${s.id}/`, { qurilmalarni_tozala: true }),
            "Qurilmalar tozalandi: keyingi kirgan qurilma yana ishonchli bo'ladi.")}>
          Ishonchli qurilmalarni tozalash (rahbar qurilmasini yo'qotganda)
        </button>
        {!s.chiqish_sanasi && (
          <button className={s.holat === 'bloklangan' ? 'ikkinchi' : 'xavfli'}
            onClick={() => bajar(() => papi.patch(`/salonlar/${s.id}/`, { bloklangan: s.holat !== 'bloklangan' }),
              s.holat === 'bloklangan' ? 'Salon blokdan chiqarildi.' : 'Salon bloklandi.')}>
            {s.holat === 'bloklangan' ? 'Blokdan chiqarish' : 'Bloklash'}
          </button>
        )}
      </div>
    </div>
  )
}

// Tariflar: ko'rsatkichlar + jadval; tarifni tuzatish qator ostida, qo'shish — oynada.
function TariflarBolimi({ tariflar, bajar }) {
  const [oyna, setOyna] = useState(false)
  const [ochiq, setOchiq] = useState(null)
  return (
    <>
      <div className="stat-qator">
        <div className="stat"><span>Faol tariflar</span><b>{tariflar.length}</b></div>
        <div className="stat"><span>Eng arzon oylik narx</span><b>{tariflar.length ? som(Math.min(...tariflar.map((t) => Number(t.oylik_narx)))) : '—'}</b></div>
        <div className="stat"><span>Eng qimmat oylik narx</span><b>{tariflar.length ? som(Math.max(...tariflar.map((t) => Number(t.oylik_narx)))) : '—'}</b></div>
        <div className="stat"><span>Eng katta xodim limiti</span><b>{tariflar.length ? Math.max(...tariflar.map((t) => t.xodim_limit)) : '—'}</b></div>
      </div>
      {oyna && (
        <Oyna sarlavha="Tarif qo'shish" onYop={() => setOyna(false)}>
          <TarifForma onYuborish={async (b) => {
            const ok = await bajar(() => papi.post('/tariflar/', b), "Tarif qo'shildi.")
            if (ok) setOyna(false)
            return ok
          }} />
        </Oyna>
      )}
      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Tariflar</h3>
          <span className="tezkor-tablar" />
          <button type="button" className="kichik" onClick={() => setOyna(true)}><NavIkona nom="qosh" className="tugma-ikon" />Tarif qo'shish</button>
        </div>
        {tariflar.length === 0 ? (
          <p className="malumot jadval-bosh">Hali tarif yo'q — birinchisini qo'shing.</p>
        ) : (
          <div className="jadval-ora">
            <table className="zakaz-jadval aks-jadval">
              <thead>
                <tr><th>Tarif</th><th className="ong">Oylik narx</th><th className="tor-yashir ong">Xodimlar</th><th className="tor-yashir ong">Filiallar</th></tr>
              </thead>
              <tbody>
                {tariflar.map((t) => (
                  <Fragment key={t.id}>
                    <tr className={ochiq === t.id ? 'ochiq' : ''} onClick={() => setOchiq(ochiq === t.id ? null : t.id)}>
                      <td>
                        <button type="button" className="zakaz-katak" aria-expanded={ochiq === t.id}>
                          <span className="kod-belgi">{(t.nomi || '?').trim().charAt(0).toUpperCase()}</span>
                          <span className="zakaz-nom"><b>{t.nomi}</b></span>
                        </button>
                      </td>
                      <td className="ong"><b>{som(t.oylik_narx)}</b></td>
                      <td className="tor-yashir ong">{t.xodim_limit}</td>
                      <td className="tor-yashir ong">{t.filial_limit}</td>
                    </tr>
                    {ochiq === t.id && (
                      <tr className="tafsilot-qator"><td colSpan={4}>
                        <TarifTahrir key={`${t.id}-${t.nomi}-${t.oylik_narx}-${t.xodim_limit}-${t.filial_limit}`} t={t}
                          onSaqla={(b, ok) => bajar(() => papi.patch(`/tariflar/${t.id}/`, b), ok)} />
                      </td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
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
    <section className="blok">
      <h3 className="panel-nom">
        Telegram bot · {MANBA[s.telegram_manba]}
        {s.telegram_bot_nomi && ` (@${s.telegram_bot_nomi})`}
        {!s.telegram_ulangan && <span className="qizil"> · ishlamayapti</span>}
      </h3>
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
    </section>
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
    <>
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
    </>
  )
}

function TarifForma({ onYuborish }) {
  const [f, setF] = useState({})
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <>
      <div className="stack">
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Oylik narx<SummaInput value={f.oylik_narx || ''} onChange={set('oylik_narx')} /></label>
        <label>Xodimlar limiti<input type="number" min="1" max="50" value={f.xodim_limit || ''} onChange={set('xodim_limit')} /></label>
        <button disabled={!f.nomi || !f.xodim_limit}
          onClick={() => onYuborish({ nomi: f.nomi, oylik_narx: Number(f.oylik_narx || 0), xodim_limit: Number(f.xodim_limit) }).then((ok) => ok && setF({}))}>
          Qo'shish
        </button>
      </div>
    </>
  )
}

// Bosh sahifadagi «A'zo bo'lish» va «Bog'lanish» formalaridan kelgan so'rovlar.
function Arizalar({ arizalar, bajar }) {
  const yangi = arizalar.filter((a) => !a.korilgan).length
  return (
    <section className="blok">
      <h3 className="panel-nom">So'rovlar ({arizalar.length}){yangi > 0 && <span className="qizil"> · {yangi} ta yangi</span>}</h3>
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
    </section>
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
