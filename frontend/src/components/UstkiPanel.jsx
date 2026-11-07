import { useCallback, useEffect, useRef, useState } from 'react'
import { chegirmaSorovlari, xarajatlar } from '../api'
import { Tasdiqlar } from '../pages/BoshEkran'
import NavIkona from './NavIkona'
import TelegramBlok from './TelegramBlok'
import XodimMenyu from './XodimMenyu'

// Kontent ustidagi yuqori panel (barcha sahifalarda): chapda sahifa nomi, o'ngda zakaz qidiruvi,
// bildirishnomalar (rahbarga: qaror kutayotganlar va ogohlantirishlar) va xodim menyusi.
export default function UstkiPanel({ sarlavha, izoh, xodim, rahbar, xabarlar, sozlash, qarorSoni, onQarorOzgardi, onQidir, onBolim, onChiqish, onRasm, onRasmOchir, onKassa }) {
  const [q, setQ] = useState('')
  const [ochiq, setOchiq] = useState(null) // 'xabar' | null
  const joy = useRef(null)
  useEffect(() => {
    if (!ochiq) return undefined
    // menyu ichidan ochilgan tasdiq oynasi (portal, body'da) — tashqariga bosish hisoblanmaydi
    const yop = (e) => { if (!joy.current?.contains(e.target) && !e.target.closest?.('.oyna-parda')) setOchiq(null) }
    const esc = (e) => { if (e.key === 'Escape' && !document.querySelector('[role="alertdialog"]')) setOchiq(null) }
    document.addEventListener('pointerdown', yop)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', yop); document.removeEventListener('keydown', esc) }
  }, [ochiq])

  const rol = rahbar ? 'Rahbar' : xodim.rol === 'kassir' ? 'Kassir' : 'Sotuvchi'
  // Rahbar qarorlari (chegirma, xarajat, yangi libos) — menyuning o'zida hal qilinadi; dashboardda alohida blok yo'q
  const qarorJami = rahbar && qarorSoni ? qarorSoni.chegirmalar + qarorSoni.xarajatlar + qarorSoni.liboslar : 0
  const [qarorlar, setQarorlar] = useState(null)
  const qarorYukla = useCallback(() => Promise.all([chegirmaSorovlari(), xarajatlar({ holat: 'kutilmoqda' })])
    .then(([sorovlar, xarajat]) => setQarorlar({ sorovlar, xarajat })).catch(() => {}), [])
  // menyu ochilganda qarorlar va sonlar yangilanadi (2 daqiqalik yangilanishni kutmasdan)
  useEffect(() => {
    if (!rahbar || ochiq !== 'xabar') return
    qarorYukla()
    onQarorOzgardi?.()
  }, [rahbar, ochiq, qarorYukla])  // eslint-disable-line react-hooks/exhaustive-deps
  const qarorKorinadi = rahbar && ((qarorlar && qarorlar.sorovlar.length + qarorlar.xarajat.length > 0) || (qarorSoni?.liboslar || 0) > 0)
  const qarorSon = qarorlar ? qarorlar.sorovlar.length + qarorlar.xarajat.length + (qarorSoni?.liboslar || 0) : qarorJami
  const soni = xabarlar.reduce((s, x) => s + x.soni, 0) + (sozlash?.qolgan.length || 0) + qarorJami
  const bor = (x) => () => { setOchiq(null); onBolim(x.bolim, x) }

  return (
    <header className="ustki" ref={joy}>
      <div className="ustki-nom">
        <h1>{sarlavha}</h1>
        {izoh && <p>{izoh}</p>}
      </div>
      <form className="qidiruv-maydon ustki-qidiruv" role="search"
        onSubmit={(e) => { e.preventDefault(); if (q.trim()) { onQidir(q.trim()); setQ('') } }}>
        <NavIkona nom="qidiruv" className="tugma-ikon" />
        <input type="search" placeholder="Zakaz: raqam, telefon yoki ism" aria-label="Zakaz qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>
      {/* Qo'ng'iroqcha hamma xodimda: rahbarga — qarorlar va ogohlantirishlar, sotuvchiga — chegirma natijasi, pul, qo'ng'iroqlar (R2) */}
      <div className="ustki-joy">
        <button type="button" className="ustki-tugma" aria-label={`Bildirishnomalar: ${soni}`} aria-expanded={ochiq === 'xabar'}
          onClick={() => setOchiq(ochiq === 'xabar' ? null : 'xabar')}>
          <svg className="tugma-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
          </svg>
          {soni > 0 && <span className="ustki-son">{soni > 99 ? '99+' : soni}</span>}
        </button>
        {ochiq === 'xabar' && (
          <div className={`ustki-menyu xabar-menyu${qarorKorinadi ? ' keng' : ''}`}>
            {sozlash && (
              <div className="xabar-sozlash" aria-label="Salonni sozlash">
                <div className="xabar-sozlash-bosh">
                  <b>Salonni sozlash</b><span>{sozlash.bajarilgan} / {sozlash.jami}</span>
                  <button type="button" className="havola" onClick={sozlash.onYashir}>Yashirish</button>
                </div>
                <div className="progress" aria-hidden="true"><i style={{ '--foiz': `${(sozlash.bajarilgan / sozlash.jami) * 100}%` }} /></div>
                {sozlash.qolgan.map((q) => (
                  <button key={q.kalit} type="button" className="xabar-qadam" onClick={() => { setOchiq(null); sozlash.onQadam(q.bolim) }}>
                    <NavIkona nom="doira" className="tugma-ikon" />{q.nomi}
                  </button>
                ))}
              </div>
            )}
            {qarorKorinadi && (
              <div className="xabar-qarorlar" role="region" aria-label="Qaroringiz kerak">
                <b className="xabar-bolim-nom">Qaroringiz kerak <span className="ish-son">{qarorSon}</span></b>
                {qarorlar && (
                  <Tasdiqlar sorovlar={qarorlar.sorovlar} xarajat={qarorlar.xarajat} soni={qarorSoni}
                    onZakaz={(id) => { setOchiq(null); onBolim(`zakaz:${id}`) }} onBolim={(b) => { setOchiq(null); onBolim(b) }}
                    onOzgardi={() => { qarorYukla(); onQarorOzgardi?.() }} />
                )}
              </div>
            )}
            <div role="menu" aria-label="Bildirishnomalar">
              <b>Bildirishnomalar</b>
              {xabarlar.length === 0 && <p className="malumot">Hozircha hammasi joyida.</p>}
              {xabarlar.map((x) => (
                <button key={x.kalit || x.matn} type="button" role="menuitem" onClick={bor(x)}>
                  <i className={`nuqta ${x.tur}`} aria-hidden="true" />{x.matn}
                </button>
              ))}
            </div>
            {/* Telegram — shu xabarlarning qo'shimcha kanali (avval bosh sahifa oxirida edi) */}
            <div className="xabar-telegram"><TelegramBlok rahbar={rahbar} /></div>
          </div>
        )}
      </div>
      {/* onKassa — smenada naqd puli bor xodim «Chiqish»ni bossa ogohlantirishdagi «Kassaga o'tish» (A-19, D3) */}
      <XodimMenyu xodim={xodim} rol={rol} onChiqish={onChiqish} onRasm={onRasm} onRasmOchir={onRasmOchir} onKassa={onKassa} />
    </header>
  )
}

