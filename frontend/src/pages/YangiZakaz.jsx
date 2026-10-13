import { useEffect, useState } from 'react'
import Vitrina from '../components/Vitrina'
import { SalonchiForma } from './Salonchilar'
import Manekin from '../components/Manekin'
import { aksessuarManekinSaqla, boshAksessuarlar, filiallar, boshLiboslar, mijozQidir, qulf, manekinSaqla, salonchiQosh, salonchilar, som, ustamaFoiz, xatoMatni, zakazYarat } from '../api'

// Yangi zakaz: 1) sana va mijoz telefoni, 2) libos tanlash, 3) tasdiqlash (4-bo'lim).
export default function YangiZakaz({ onTayyor }) {
  const [dan, setDan] = useState('')
  const [gacha, setGacha] = useState('')
  const [telefon, setTelefon] = useState('')
  const [mijoz, setMijoz] = useState(null)
  const [fio, setFio] = useState('')
  const [manba, setManba] = useState('boshqa')
  const [salonchiRoyxat, setSalonchiRoyxat] = useState([])
  const [salonchi, setSalonchi] = useState('')
  useEffect(() => { salonchilar().then(setSalonchiRoyxat).catch(() => {}) }, [])
  const tanlanganSalonchi = salonchiRoyxat.find((s) => String(s.id) === String(salonchi))
  const [bandlar, setBandlar] = useState(false)
  const [liboslar, setLiboslar] = useState(null)
  const [tanlangan, setTanlangan] = useState([])
  const [aksessuarlar, setAksessuarlar] = useState([])
  const [aksSoni, setAksSoni] = useState({})
  const [xabar, setXabar] = useState('')
  const [zakaz, setZakaz] = useState(null)
  const [vitrina, setVitrina] = useState(false)
  const [manekin, setManekin] = useState(null) // 4.5: tanlangan libos manekinda
  // FT-3.2: kategoriya, o'lcham, rang, narx bo'yicha filtr; qidiruvda band libos ham chiqadi (FT-2.2)
  const [filtr, setFiltr] = useState({ kat: '', olcham: '', rang: '', narx: '', q: '', filial: '' })
  // Filiallar: standart — shu qurilma filiali; biriktirilmagan libos hamma filialda ko'rinadi
  const [fil, setFil] = useState([])
  useEffect(() => {
    filiallar().then((r) => { setFil(r.filiallar); if (r.joriy) setFiltr((f) => ({ ...f, filial: String(r.joriy) })) }).catch(() => {})
  }, [])

  const aksJami = aksessuarlar.reduce((s, a) => s + a.ijara_narxi * (aksSoni[a.id] || 0), 0)
  const asosiy = tanlangan.reduce((s, l) => s + l.ijara_narxi, 0) + aksJami
  // FT-15.2: mavsumiy ustama olib ketish kuniga qarab; yakuniy narxni server hisoblaydi
  const [ustama, setUstama] = useState({ foiz: 0, nomi: null })
  useEffect(() => {
    let bekor = false
    const nol = { foiz: 0, nomi: null }
    const so = dan ? ustamaFoiz(dan).then((r) => ({ foiz: Number(r.foiz), nomi: r.nomi })).catch(() => nol) : Promise.resolve(nol)
    so.then((r) => { if (!bekor) setUstama(r) })
    return () => { bekor = true }
  }, [dan])
  const ustamaSumma = Math.round((asosiy * ustama.foiz) / 100)
  const jami = asosiy + ustamaSumma

  const mijozniTekshir = async () => {
    setMijoz(null)
    if (!telefon) return
    try {
      setMijoz(await mijozQidir(telefon))
    } catch {
      setMijoz({ yangi: true })
    }
  }

  const qidirish = async () => {
    setXabar('')
    if (!dan || !gacha || !telefon) return setXabar('Sanalar va mijoz telefonini kiriting.')
    setTanlangan([])
    setAksSoni({})
    const [l, a] = await Promise.all([boshLiboslar(dan, gacha, bandlar, filtr.q), boshAksessuarlar(dan, gacha)])
    setLiboslar(l)
    setAksessuarlar(a)
    const mo = mijoz?.kiyim_olchami
    if (mo && l.some((x) => x.olcham === mo)) setFiltr((f) => ({ ...f, olcham: mo }))
  }

  const tanlash = async (l) => {
    setXabar('')
    if (tanlangan.some((t) => t.id === l.id)) {
      return setTanlangan(tanlangan.filter((t) => t.id !== l.id))
    }
    try {
      await qulf(l.id, dan, gacha) // 15 daqiqaga boshqa sotuvchidan yashiriladi
      setTanlangan([...tanlangan, l])
    } catch (e) {
      setXabar(e.response?.data?.detail || 'Libosni tanlab bo\'lmadi.')
      setLiboslar(await boshLiboslar(dan, gacha, bandlar, filtr.q))
    }
  }

  const saqlash = async () => {
    setXabar('')
    try {
      setZakaz(await zakazYarat({ telefon, fio: mijoz?.yangi ? fio : '', manba: mijoz?.yangi && !salonchi ? manba : undefined,
        salonchi: salonchi ? Number(salonchi) : undefined, dan, gacha, liboslar: tanlangan.map((l) => l.id),
        aksessuarlar: Object.entries(aksSoni).flatMap(([id, n]) => Array(n).fill(Number(id))) }))
    } catch (e) {
      setXabar(e.response?.data?.detail || 'Zakazni saqlab bo\'lmadi.')
      setLiboslar(await boshLiboslar(dan, gacha, bandlar, filtr.q))
      setTanlangan([])
    }
  }

  const yangi = () => {
    setZakaz(null); setLiboslar(null); setTanlangan([]); setMijoz(null); setAksessuarlar([]); setAksSoni({})
    setDan(''); setGacha(''); setTelefon(''); setFio(''); setSalonchi(''); setManba('boshqa')
  }

  // FT-1.4: boshqa sotuvchi libosni band qilsa yoki qulflasa, ro'yxat sahifani yangilamasdan o'zgaradi.
  const royxatOchiq = liboslar !== null && !zakaz
  useEffect(() => {
    if (!royxatOchiq || !dan || !gacha) return undefined
    const t = setInterval(async () => {
      try {
        const [l, a] = await Promise.all([boshLiboslar(dan, gacha, bandlar, filtr.q), boshAksessuarlar(dan, gacha)])
        setLiboslar(l)
        setAksessuarlar(a)
        // tanlangan libos orada band bo'lib qolgan bo'lsa (masalan, qulf muddati o'tib), tanlovdan chiqariladi
        setTanlangan((eski) => {
          const mavjud = eski.filter((t2) => l.some((x) => x.id === t2.id && !x.band && !x.qulflangan))
          if (mavjud.length !== eski.length) setXabar("Tanlangan libos band bo'lib qoldi va ro'yxatdan chiqarildi.")
          return mavjud.length === eski.length ? eski : mavjud
        })
      } catch { /* tarmoq uzilsa keyingi urinishda yangilanadi */ }
    }, 4000)
    return () => clearInterval(t)
  }, [royxatOchiq, dan, gacha, bandlar, filtr.q])

  // Qidiruv matni o'zgarsa ro'yxat darhol (300 ms kechikish bilan) qayta olinadi.
  useEffect(() => {
    if (!royxatOchiq || !dan || !gacha) return undefined
    const t = setTimeout(() => boshLiboslar(dan, gacha, bandlar, filtr.q).then(setLiboslar).catch(() => {}), 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtr.q])

  const noyob = (kalit) => [...new Set((liboslar || []).map((l) => l[kalit]).filter(Boolean))].sort()
  const korinadi = (liboslar || []).filter((l) => (!filtr.kat || l.kategoriya === filtr.kat)
    && (!filtr.olcham || l.olcham === filtr.olcham) && (!filtr.rang || l.rang === filtr.rang)
    && (!filtr.narx || l.ijara_narxi <= Number(filtr.narx))
    && (!filtr.filial || l.filial == null || l.filial === Number(filtr.filial)))

  const korsatiladigan = tanlangan.length > 0 ? tanlangan : (liboslar || []).filter((l) => !l.band && !l.qulflangan)
  if (vitrina && korsatiladigan.length > 0) {
    return <Vitrina liboslar={korsatiladigan} onChiqish={() => setVitrina(false)} />
  }

  if (zakaz) {
    return (
      <div className="stack">
        <h2>Zakaz #{zakaz.raqam} saqlandi</h2>
        <p>Jami: <b>{som(zakaz.jami)}</b></p>
        <p>Holat: vaqtinchalik bron (24 soat). Avans kiritilmasa bekor bo'ladi.</p>
        <button onClick={() => onTayyor(zakaz.id)}>Zakaz kartasini ochish</button>
        <button className="ikkinchi" onClick={yangi}>Yangi zakaz</button>
      </div>
    )
  }

  return (
    <div className="stack">
      <section>
        <h2>Yangi zakaz</h2>
        <label>Mijoz telefoni
          <input value={telefon} inputMode="tel" placeholder="+998 90 123 45 67"
            onChange={(e) => setTelefon(e.target.value)} onBlur={mijozniTekshir} />
        </label>
        {mijoz?.yangi && (
          <label>Yangi mijoz — F.I.O.<input value={fio} onChange={(e) => setFio(e.target.value)} /></label>
        )}
        {mijoz && !mijoz.yangi && (
          <div className={mijoz.qora_royxat ? 'ogohlantirish' : 'malumot'}>
            {mijoz.qora_royxat && <b>Qora ro'yxat: {mijoz.qora_royxat_sabab}. </b>}
            {mijoz.fio} · oldingi zakazlar: {mijoz.tarix.length}
            {mijoz.olchamlar && Object.values(mijoz.olchamlar).some((v) => v != null) && (
              <> · o'lchamlar: {[mijoz.olchamlar.kokrak, mijoz.olchamlar.bel, mijoz.olchamlar.son].map((v) => v ?? '—').join('/')}{mijoz.olchamlar.boy ? `, bo'y ${mijoz.olchamlar.boy}` : ''}</>
            )}
          </div>
        )}
        {mijoz?.yangi && !salonchi && (
          <label>Mijoz qayerdan keldi
            <select value={manba} onChange={(e) => setManba(e.target.value)}>
              <option value="instagram">Instagram</option><option value="tavsiya">Tavsiya</option><option value="boshqa">Boshqa</option>
            </select>
          </label>
        )}
        <label>Salonchi (makiyaj ustasi)
          <select value={salonchi} onChange={(e) => setSalonchi(e.target.value)}>
            <option value="">— yo'q —</option>
            {salonchiRoyxat.map((s) => <option key={s.id} value={s.id}>{s.ism}{s.salon_nomi ? ` · ${s.salon_nomi}` : ''}</option>)}
          </select>
        </label>
        {tanlanganSalonchi?.instagram && (
          <a className="tugma-havola" href={tanlanganSalonchi.instagram} target="_blank" rel="noreferrer">
            {tanlanganSalonchi.ism} ishlarini Instagramda ko'rish
          </a>
        )}
        <SalonchiForma onYuborish={async (b) => {
          try {
            const yangiS = await salonchiQosh(b)
            setSalonchiRoyxat(await salonchilar()); setSalonchi(String(yangiS.id)); setXabar('')
            return true
          } catch (e) { setXabar(xatoMatni(e)); return false }
        }} />
        <label>Olib ketish<input type="date" value={dan} onChange={(e) => setDan(e.target.value)} /></label>
        <label>Qaytarish<input type="date" value={gacha} min={dan} onChange={(e) => setGacha(e.target.value)} /></label>
        <label className="qator">
          <input type="checkbox" checked={bandlar} onChange={(e) => setBandlar(e.target.checked)} />
          Bandlarni ham ko'rsatish
        </label>
        <button onClick={qidirish}>Liboslarni ko'rsatish</button>
        {xabar && <p className="xato">{xabar}</p>}
      </section>
      {korsatiladigan.length > 0 && (
        <button className="ikkinchi" onClick={() => setVitrina(true)}>
          Mijozga ko'rsatish ({tanlangan.length > 0 ? 'tanlanganlar' : "bo'sh liboslar"})
        </button>
      )}
      {liboslar && (
        <section className="stack filtrlar">
          <input placeholder="Artikul yoki nom bo'yicha qidirish (band libos ham chiqadi)" value={filtr.q}
            onChange={(e) => setFiltr({ ...filtr, q: e.target.value })} />
          <div className="chiplar">
            <button className={filtr.kat ? 'ikkinchi kichik' : 'kichik'} onClick={() => setFiltr({ ...filtr, kat: '' })}>Hammasi</button>
            {noyob('kategoriya').map((k) => (
              <button key={k} className={filtr.kat === k ? 'kichik' : 'ikkinchi kichik'} onClick={() => setFiltr({ ...filtr, kat: k })}>{k}</button>
            ))}
          </div>
          <div className="qator">
            {fil.length > 0 && (
              <select value={filtr.filial} aria-label="Filial" onChange={(e) => setFiltr({ ...filtr, filial: e.target.value })}>
                <option value="">Barcha filiallar</option>
                {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
              </select>
            )}
            <select value={filtr.olcham} onChange={(e) => setFiltr({ ...filtr, olcham: e.target.value })}>
              <option value="">O'lcham</option>
              {noyob('olcham').map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
            <select value={filtr.rang} onChange={(e) => setFiltr({ ...filtr, rang: e.target.value })}>
              <option value="">Rang</option>
              {noyob('rang').map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
            <input className="narx-filtr" type="number" min="0" placeholder="Narx gacha" value={filtr.narx}
              onChange={(e) => setFiltr({ ...filtr, narx: e.target.value })} />
          </div>
        </section>
      )}
      {liboslar && (
        <ul className="liboslar">
          {korinadi.length === 0 && <li>{liboslar.length === 0 ? "Bu sanalarga bo'sh libos yo'q." : 'Filtrga mos libos topilmadi.'}</li>}
          {korinadi.map((l) => {
            const tanlandi = tanlangan.some((t) => t.id === l.id)
            const yopiq = l.band || l.qulflangan
            return (
              <li key={l.id} className={`${yopiq ? 'band' : ''} ${tanlandi ? 'tanlandi' : ''}`}>
                {l.rasm && <img className="eskiz" src={l.rasm} alt="" />}
                <span className="matn-ustun">
                  <span><b>{l.artikul}</b> {l.nomi} · {l.kategoriya}</span>
                  <span>{som(l.ijara_narxi)}</span>
                </span>
                {l.qulflangan && <em>Hozir boshqa sotuvchi rasmiylashtiryapti</em>}
                {l.band && (
                  <em>
                    Band{l.eng_yaqin_bosh ? ` · eng yaqin bo'sh sana: ${l.eng_yaqin_bosh}` : ''}
                    {l.oxshashlar?.length > 0 && ` · o'xshash bo'sh: ${l.oxshashlar.map((o) => `${o.artikul} ${o.nomi}`).join(', ')}`}
                  </em>
                )}
                {l.manekin && (
                  <button type="button" className="ikkinchi kichik" onClick={() => setManekin(l)}>Manekinda</button>
                )}
                {!yopiq && (
                  <button className={tanlandi ? '' : 'ikkinchi'} onClick={() => tanlash(l)}>
                    {tanlandi ? 'Olib tashlash' : "Qo'shish"}
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {manekin && (
        <Manekin sarlavha={manekin.nomi} faylNomi={manekin.artikul} onYopish={() => setManekin(null)}
          qatlamlar={[
            { kalit: 'libos', nomi: 'Libos', standart: { x: 0, y: 0.08, k: 0.8 }, ...manekin.manekin, saqla: (b) => manekinSaqla(manekin.id, b) },
            // FT-5.2: zakazga tanlangan (soni > 0) va manekin rasmi bor aksessuarlar libos ustidan qo'yiladi
            ...aksessuarlar.filter((a) => a.manekin && aksSoni[a.id] > 0)
              .map((a) => ({ kalit: `a${a.id}`, nomi: a.nomi, ...a.manekin, saqla: (b) => aksessuarManekinSaqla(a.id, b) })),
          ]}
          onSaqlandi={(q) => {
            const yangi = (eski, kalit) => { const v = q.find((x) => x.kalit === kalit); return v ? { ...eski, x: v.x, y: v.y, kattalik: v.kattalik } : eski }
            setLiboslar(liboslar.map((x) => (x.id === manekin.id ? { ...x, manekin: yangi(x.manekin, 'libos') } : x)))
            setAksessuarlar(aksessuarlar.map((a) => (a.manekin ? { ...a, manekin: yangi(a.manekin, `a${a.id}`) } : a)))
            setManekin({ ...manekin, manekin: yangi(manekin.manekin, 'libos') })
          }} />
      )}
      {liboslar && aksessuarlar.length > 0 && (
        <section className="blok">
          <h3>Aksessuarlar</h3>
          {aksessuarlar.map((a) => {
            const n = aksSoni[a.id] || 0
            const o = (d) => setAksSoni({ ...aksSoni, [a.id]: Math.max(0, Math.min(a.bosh_soni, n + d)) })
            return (
              <div key={a.id} className="qator aks-qator">
                <span className="matn-ustun">
                  <span><b>{a.nomi}</b> · {a.kategoriya}</span>
                  <span className="malumot">{som(a.ijara_narxi)} · bo'sh: {a.bosh_soni} dona</span>
                </span>
                <button type="button" className="ikkinchi kichik" onClick={() => o(-1)} disabled={n === 0}>−</button>
                <b className="son">{n}</b>
                <button type="button" className="ikkinchi kichik" onClick={() => o(1)} disabled={n >= a.bosh_soni}>+</button>
              </div>
            )
          })}
        </section>
      )}
      {tanlangan.length > 0 && (
        <footer className="jami">
          <span>
            {tanlangan.length} ta libos{aksJami > 0 ? ` + aksessuar ${som(aksJami)}` : ''}
            {ustama.foiz > 0 && ` + ustama ${ustama.foiz}% (${som(ustamaSumma)})`} · <b>{som(jami)}</b>
          </span>
          <button onClick={saqlash} disabled={mijoz?.qora_royxat}>Zakazni saqlash</button>
        </footer>
      )}
    </div>
  )
}
