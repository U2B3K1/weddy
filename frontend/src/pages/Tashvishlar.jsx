// "Imkoniyatlar" bo'limi — Orano "Innovation" slayderi uslubida. Avvalgi «Uch tashvish» (Bron / Zalog / Foyda) va
// «Imkoniyatlar» o'yin kartalari shu bitta slayderga birlashtirilgan: 8 slayd, har birida salonning bitta tashvishi
// (shior) va tizimning shu bo'yicha to'rtta imkoniyati. Ma'lumot takrorlanmaydi — har imkoniyat faqat bir joyda.
//
// Har slaydning o'z kadri bor: to'q ko'k fonda tilla sim-karkas (wireframe) chizma (public/tashvish/fon-N.jpg) va
// uning polida turgan milliy libosdagi tilla kelin (kelin-N.mp4).
//
// Slayd almashishi — "skaner": tik tilla nur ekran bo'ylab yuradi, uning ortidan yangi kadr ochilib boradi
// (eski kadr ostida turadi). «Keyingi» — nur o'ngdan chapga, «oldingi» — chapdan o'ngga yuradi.
//
// Qaysi slayd ko'rinishini sahifaning aylantirilgan joyi belgilaydi: bo'lim baland (.rk-tv-yol), ichidagi sahna
// yopishqoq (.rk-tv) — aylantirganda slaydlar birin-ketin almashadi. Strelkalar, nuqtalar va 5 soniyalik
// avtomatik almashish ham shu orqali ishlaydi: ular sahifani kerakli slaydning joyiga aylantirib qo'yadi.
//
// Kelin — aylanma video, bosish bilan boshqariladi: bir marta bosilsa to'liq bir aylanadi, bosib turib yonga
// surilsa qo'lda aylantiriladi. Videolar har kadri kalit kadr qilib kodlangan, shuning uchun surishda sakramaydi.
import { useEffect, useRef, useState } from 'react'
import './tashvishlar.css'

// Kelinning kadrdagi o'rni: x, y — oyog'i turadigan nuqta (bo'lim kengligi / balandligidan %), h — bo'yi (vh).
// Har fonda pol boshqa joyda, shuning uchun har slaydga alohida.
const SLAYDLAR = [
  { nom: 'Bron', obraz: 'Atlas ko\'ylak va zarchopon', joy: 'Saroy zali', x: 38, y: 90, h: 62, shior: 'Bitta libos — ikki kelin emas',
    qatorlar: ["Band libos ikkinchi marta bron bo'lmaydi — buni tizim o'zi tekshiradi", 'Kalendar va bandlik bir qarashda', 'Tozalash uchun bufer kunlar', 'Primerka vaqti'] },
  { nom: 'Zakaz', obraz: 'Buxoro zardo\'zi libosi', joy: 'Saroy zinasi', x: 37, y: 88, h: 60, shior: 'Zalog kimda qolgani — yozilgan',
    qatorlar: ['Avans, qoldiq va qarz', 'Pul, hujjat yoki tillo zalog — har biri yorliq bilan', 'Berish va qaytarish', 'Shartnoma va kvitansiya'] },
  { nom: 'Katalog', obraz: 'Oq to\'y libosi va do\'ppi', joy: 'Primerka xonasi', x: 38.5, y: 82, h: 54, shior: 'Har libosning o\'z pasporti',
    qatorlar: ["Rasm, o'lcham va narx", 'Aksessuarlar donalab', "Ta'mir jurnali", 'Raqamli manekin'] },
  { nom: 'Kassa', obraz: 'Xorazm libosi va taxya', joy: 'Gumbazli zal', x: 33, y: 92, h: 60, shior: 'Kun oxirida kassa to\'g\'ri chiqadi',
    qatorlar: ['Smena ochish va yopish', 'Naqd, karta, Click, Payme', "Zalog tekshiruvi: har biri «joyida» deb belgilanadi", 'Inkassatsiya'] },
  { nom: 'Foyda', obraz: 'Atlas ko\'ylak va kashtali nimcha', joy: 'Peshtoq', x: 34, y: 92, h: 60, shior: 'Oy oxirida foyda qancha',
    qatorlar: ["Oylik foyda-zarar o'zi chiqadi: tushum va xarajat", '16 ta hisobot', 'Sotuvchi bonusi', 'Oyni yopish'] },
  { nom: 'Mijozlar', obraz: 'Surxon libosi, kelin salom', joy: 'Madrasa hovlisi', x: 36, y: 89, h: 58, shior: 'Har kelin — tanish mijoz',
    qatorlar: ["Mijoz kartasi va o'lchamlari", 'Salonchilar statistikasi', 'Promokod va chegirma', "Qora ro'yxat"] },
  { nom: 'Eslatmalar', obraz: 'Farg\'ona libosi va ko\'zgu', joy: 'Sharqona ayvon', x: 22, y: 91, h: 60, shior: 'Hech bir sana esdan chiqmaydi',
    qatorlar: ['Telegram orqali xabar', 'SMS eslatma', 'Rahbarga kunlik hisobot', "Tasdiq so'rovlari"] },
  { nom: 'Filiallar', obraz: 'Toshkent libosi va zardo\'zi yopinchiq', joy: 'Shahar ustida', x: 36, y: 92, h: 58, shior: 'Bir nechta salon — bitta hisob',
    qatorlar: ['Bir hisobda bir nechta filial', "Har filialga o'z qurilmasi", 'Alohida kassa', "Filial bo'yicha foyda"] },
]
const SONI = SLAYDLAR.length
const AVTO = 5000      // ms — bo'lim ekranda turganda slayd shuncha vaqtdan keyin o'zi almashadi
const OTISH = 1150     // ms — skaner nuri ekranni kesib o'tadigan vaqt (tashvishlar.css dagi --tv-vaqt bilan bir xil)
const BOSH = 0.25      // s — videoning birinchi kadrlari (asl rasm) keyingilaridan farq qiladi, tashlab yuboriladi
const TEZLIK = 1.7     // bir bosishdagi to'liq aylanish tezligi (5 s lik video ≈ 3 s da)
const ikki = (n) => String(n).padStart(2, '0')
const aylana = (i) => (i % SONI + SONI) % SONI

export function Tashvishlar() {
  const yol = useRef(null), bolim = useRef(null)
  const videolar = useRef([])
  const [faol, setFaol] = useState(0)             // ostida turgan (to'liq ko'rinadigan) kadr
  const [kir, setKir] = useState(null)            // hozir skaner bilan ochilayotgan kadr
  const [matn, setMatn] = useState(0)             // matni ko'rsatilayotgan slayd (o'tishning o'rtasida almashadi)
  const [yon, setYon] = useState(1)               // 1 — keyingi (nur o'ngdan chapga), -1 — oldingi
  const [ochildi, setOchildi] = useState(false)   // bo'lim ekranga kirib, birinchi kadr ochilganmi
  const [jim, setJim] = useState(true)            // matn yashirin (o'tishning birinchi yarmida)
  const [avto, setAvto] = useState(false)         // avtomatik almashish hozir sanayaptimi (nuqtadagi to'lish chizig'i uchun)
  const faolRef = useRef(0), band = useRef(true), vaqtlar = useRef([])
  const ozgardi = useRef(0)                       // oxirgi almashish yoki foydalanuvchi harakati vaqti (ms)
  const ushlash = useRef(null)                    // { x, t, surildi } — kelin bosib turilgan paytda
  const keyin = (ms, f) => { vaqtlar.current.push(setTimeout(f, ms)) }

  // Aylantirilgan joyga to'g'ri keladigan slayd (0..SONI-1) va slaydning sahifadagi joyi
  const yolUzunligi = () => yol.current.offsetHeight - window.innerHeight
  const joydagi = () => {
    const u = yolUzunligi()
    return u > 0 ? Math.round(Math.min(1, Math.max(0, -yol.current.getBoundingClientRect().top / u)) * (SONI - 1)) : faolRef.current
  }
  const borish = (i) => {
    i = aylana(i)
    ozgardi.current = performance.now()
    const y = yol.current.getBoundingClientRect().top + window.scrollY + (i / (SONI - 1)) * yolUzunligi()
    window.scrollTo({ top: y, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
  }

  // Bo'lim ekranga kirganda birinchi kadr ham skaner bilan ochiladi
  useEffect(() => {
    const v = vaqtlar.current
    const kuzat = new IntersectionObserver(([y]) => {
      if (!y.isIntersecting) return
      kuzat.disconnect()
      setOchildi(true); setKir(0)
      keyin(OTISH * .45, () => setJim(false))
      keyin(OTISH, () => { setKir(null); band.current = false; ozgardi.current = performance.now(); moslaRef.current() })
    }, { threshold: 0.98 })   // birinchi kadr sahna ekranni to'liq egallaganda ochiladi (shu paytgacha qorong'ilik)
    kuzat.observe(bolim.current)
    return () => { kuzat.disconnect(); v.forEach(clearTimeout) }
  }, [])

  // Kursor: faqat fon va kelinning yengil parallaksi (--mx, --my); aylanish bosish bilan
  useEffect(() => {
    const B = bolim.current
    const kursor = (e) => {
      const r = B.getBoundingClientRect()
      B.style.setProperty('--mx', ((e.clientX - r.left) / r.width - .5).toFixed(3))
      B.style.setProperty('--my', ((e.clientY - r.top) / r.height - .5).toFixed(3))
    }
    B.addEventListener('pointermove', kursor)
    return () => B.removeEventListener('pointermove', kursor)
  }, [])

  // Aylantirilgan joyga mos slayd ko'rinmayotgan bo'lsa — skaner bilan o'shanga o'tadi. Aylantirishda ham,
  // har o'tish tugaganda ham chaqiriladi (tez aylantirilganda oraliq slaydlar tashlab ketiladi).
  const mosla = () => {
    const yangi = joydagi(), eski = faolRef.current
    if (band.current || yangi === eski) return
    band.current = true
    ozgardi.current = performance.now()                     // 5 soniya slayd almasha boshlagan paytdan sanaladi
    videolar.current[eski]?.pause()
    setYon(yangi > eski ? 1 : -1); setKir(yangi); setJim(true)
    faolRef.current = yangi
    keyin(OTISH * .45, () => { setMatn(yangi); setJim(false) })
    keyin(OTISH, () => {
      setFaol(yangi); setKir(null); band.current = false
      const v = videolar.current[eski]
      if (v && v.duration) v.currentTime = BOSH             // eski kelin keyingi safar yana old tomoni bilan chiqadi
      moslaRef.current()
    })
  }
  const moslaRef = useRef(mosla)
  useEffect(() => { moslaRef.current = mosla })

  // Aylantirish va 5 soniyalik avtomatik almashish
  useEffect(() => {
    const aylandi = () => moslaRef.current()
    window.addEventListener('scroll', aylandi, { passive: true })
    window.addEventListener('resize', aylandi)
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return () => { window.removeEventListener('scroll', aylandi); window.removeEventListener('resize', aylandi) }
    // Avtomatik almashish faqat bo'lim ekranni egallab turganda, sahifa ko'rinib turganda va kelin bilan
    // o'ynalmayotganda sanaydi; oxirgi slaydda to'xtaydi (sahifani bo'limdan o'zi chiqarib yubormaydi).
    const soat = setInterval(() => {
      const r = yol.current.getBoundingClientRect(), vh = window.innerHeight, hozir = performance.now()
      const v = videolar.current[faolRef.current]
      const sanaydi = !document.hidden && r.top < vh * .4 && r.bottom > vh * .6
        && faolRef.current < SONI - 1 && !ushlash.current && (!v || v.paused)
      if (!sanaydi) ozgardi.current = hozir
      else if (!band.current && hozir - ozgardi.current >= AVTO) borish(faolRef.current + 1)
      setAvto(sanaydi)
    }, 250)
    return () => { clearInterval(soat); window.removeEventListener('scroll', aylandi); window.removeEventListener('resize', aylandi) }
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  // --- Kelinni bosish bilan boshqarish ---
  const oxiri = (v) => v.duration - 0.05
  const aylantir = (v) => {                        // bir marta bosildi: to'liq bir aylanadi va old tomonida to'xtaydi
    if (!v.duration || !v.paused) return
    if (v.currentTime >= oxiri(v) - .1) v.currentTime = BOSH
    v.playbackRate = TEZLIK
    v.play().catch(() => {})
  }
  const tugadi = (e) => { const v = e.currentTarget; v.pause(); v.currentTime = BOSH; ozgardi.current = performance.now() }
  const bosildi = (e, i) => {
    const v = videolar.current[i]
    if (!v || !v.duration || band.current) return
    e.currentTarget.setPointerCapture(e.pointerId)
    ozgardi.current = performance.now()
    v.pause()
    ushlash.current = { x: e.clientX, t: v.currentTime, surildi: false }
  }
  const surildi = (e, i) => {
    const u = ushlash.current, v = videolar.current[i]
    if (!u || !v) return
    const dx = e.clientX - u.x
    if (!u.surildi && Math.abs(dx) < 5) return
    u.surildi = true
    if (v.seeking) return                           // oldingi kadrga o'tish tugamaguncha yangisini so'ramaymiz
    // kelin kengligicha surish — to'liq bir aylanish; chetidan o'tsa aylana bo'ylab davom etadi
    const uz = oxiri(v) - BOSH, r = e.currentTarget.getBoundingClientRect()
    const t = BOSH + (((u.t - BOSH + (dx / r.width) * uz) % uz) + uz) % uz
    if (Math.abs(v.currentTime - t) > 0.03) v.currentTime = t
  }
  const qoyildi = (i) => {
    const u = ushlash.current, v = videolar.current[i]
    ushlash.current = null
    if (u && v && !u.surildi) aylantir(v)
  }

  const s = SLAYDLAR[matn]
  // Faqat joriy va ikki qo'shni slaydning fayllari yuklanadi (8 ta video birdan xotirani to'ldirmasin)
  const yaqin = [...new Set([faol, aylana(faol + 1), aylana(faol - 1), ...(kir === null ? [] : [kir])])]
  return (
    <div className="rk-tv-yol" ref={yol} id="imkoniyatlar" data-sahna data-kir style={{ '--soni': SONI }}>
    <div className={'rk-tv' + (jim ? ' rk-tv-jim' : '') + (avto ? ' rk-tv-avto' : '')} ref={bolim}>
      {/* Kadrlar: har slaydga tilla chizma + kelin. Ostida joriy kadr, ustida — skaner bilan ochilayotgani */}
      <div className="rk-tv-sahna">
        {yaqin.map((i) => {
          const k = SLAYDLAR[i]
          const holat = i === kir ? ` rk-tv-kiruvchi rk-tv-${yon > 0 ? 'ongdan' : 'chapdan'}` : i === faol && ochildi ? ' rk-tv-faol' : ''
          return (
            <div key={i} className={'rk-tv-kadr' + holat} style={{ '--kx': k.x, '--ky': k.y, '--kh': k.h }}>
              <img className="rk-tv-fon" src={`/tashvish/fon-${i + 1}.jpg`} alt="" />
              <div className="rk-tv-kelin" role="button" tabIndex={i === matn ? 0 : -1} aria-label={`${k.obraz} — bosilsa aylanadi`}
                onPointerDown={(e) => bosildi(e, i)} onPointerMove={(e) => surildi(e, i)}
                onPointerUp={() => qoyildi(i)} onPointerCancel={() => { ushlash.current = null }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); const v = videolar.current[i]; if (v) aylantir(v) } }}>
                <video ref={(el) => { videolar.current[i] = el }} src={`/tashvish/kelin-${i + 1}.mp4`} poster={`/tashvish/kelin-${i + 1}.jpg`}
                  muted playsInline preload="auto" onLoadedMetadata={(e) => { e.currentTarget.currentTime = BOSH }} onEnded={tugadi} />
              </div>
            </div>
          )
        })}
        {kir !== null && <i key={kir} className={`rk-tv-skaner rk-tv-${yon > 0 ? 'ongdan' : 'chapdan'}`} aria-hidden="true" />}
      </div>
      <i className="rk-tv-tor" aria-hidden="true" />

      <p className="rk-tv-yorliq">Imkoniyatlar</p>
      <p className="rk-tv-obraz" aria-hidden="true"><b>{ikki(matn + 1)} · {s.joy}</b>{s.obraz}<small>Kelinni bosing — aylanadi</small></p>

      <div className="rk-tv-matn" aria-live="polite">
        <p className="rk-tv-sanoq"><b>{ikki(matn + 1)}</b><i />{ikki(SONI)}</p>
        <h2>{s.nom}</h2>
        <p className="rk-tv-shior">{s.shior}</p>
        <ul>{s.qatorlar.map((q) => <li key={q}>{q}</li>)}</ul>
        <div className="rk-tv-nuqtalar">
          {SLAYDLAR.map((k, i) => (
            <button key={k.nom + (i === matn ? matn : '')} type="button" className={i === matn ? 'rk-tv-faol' : ''} onClick={() => borish(i)}
              aria-label={k.nom} aria-current={i === matn ? 'true' : undefined} title={k.nom} />
          ))}
        </div>
      </div>

      <button type="button" className="rk-tv-strelka rk-tv-oldingi" onClick={() => borish(faolRef.current - 1)} aria-label="Oldingi imkoniyat">
        <svg viewBox="0 0 40 12" aria-hidden="true"><path d="M40,6 H2 M8,1 L2,6 L8,11" /></svg>
      </button>
      <button type="button" className="rk-tv-strelka rk-tv-keyingi" onClick={() => borish(faolRef.current + 1)} aria-label="Keyingi imkoniyat">
        <svg viewBox="0 0 40 12" aria-hidden="true"><path d="M0,6 H38 M32,1 L38,6 L32,11" /></svg>
      </button>
    </div>
    </div>
  )
}
