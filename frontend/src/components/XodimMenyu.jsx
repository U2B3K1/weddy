import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import NavIkona from './NavIkona'
import { smenaHolati, som } from '../api'

// Xodim menyusi: belgi (profil rasmi yoki ismning bosh harfi) bosilsa — salon nomi, profil rasmi va «Ilovadan chiqish».
// Kompyuterda yuqori panelda ism va rol bilan; telefonda (`ixcham`) shapkada faqat doira belgi.
// `onKassa` (ixtiyoriy) — smenada naqd bilan chiqmoqchi bo'lganda «Kassaga o'tish» tugmasi shu bo'limni ochadi.
// `yon` — chap panel pastida faqat «Chiqish» tugmasi (smena ogohlantirishi bilan); xodim belgisi va menyusi yuqori panelda.
export default function XodimMenyu({ xodim, rol, onChiqish, onRasm, onRasmOchir, onKassa, ixcham = false, yon = false }) {
  const [ochiq, setOchiq] = useState(false)
  const [rasmXato, setRasmXato] = useState('')
  const [yuklanmoqda, setYuklanmoqda] = useState(false)
  const [tekshirilmoqda, setTekshirilmoqda] = useState(false)
  const [ogoh, setOgoh] = useState(null)  // { naqd, yolgiz } — smenada pul bilan chiqmoqchi
  const ogohYop = useCallback(() => setOgoh(null), [])
  const joy = useRef(null)
  const fayl = useRef(null)
  useEffect(() => {
    if (!ochiq) return undefined
    const yop = (e) => { if (!joy.current?.contains(e.target)) setOchiq(false) }
    const esc = (e) => { if (e.key === 'Escape') setOchiq(false) }
    document.addEventListener('pointerdown', yop)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', yop); document.removeEventListener('keydown', esc) }
  }, [ochiq])

  const rasmTanla = async (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''  // shu faylni qayta tanlasa ham ishlasin
    if (!f) return
    setRasmXato(''); setYuklanmoqda(true)
    try { await onRasm(f); setOchiq(false) } catch (err) { setRasmXato(err.message) } finally { setYuklanmoqda(false) }
  }
  // Smenada qo'lida naqd bilan ilovadan chiqsa — ogohlantirish: pul topshirilmasa hamkasbi smenani yopa olmaydi.
  // Tanaffusga chiqish odatiy hol — «Baribir chiqish» doim bor. Holatni bilib bo'lmasa (internet yo'q) — oddiy chiqish.
  const chiqishBos = async () => {
    setTekshirilmoqda(true)
    let s = null
    try { s = await smenaHolati() } catch { /* tarmoq — chiqishni to'xtatmaydi */ }
    setTekshirilmoqda(false); setOchiq(false)
    if (s?.ochiq && s.men_ishtirokchi && s.mening_hisobim > 0) setOgoh({ naqd: s.mening_hisobim, yolgiz: s.ishtirokchilar.length === 1 })
    else onChiqish()
  }
  const harf = (xodim.ism || '?').trim().charAt(0).toUpperCase()

  if (yon) {
    return (
      <div className="ustki-joy yon-joy">
        <button type="button" className="yon-chiqish" disabled={tekshirilmoqda} onClick={chiqishBos}>
          <NavIkona nom="chiqish" className="tugma-ikon" />Chiqish
        </button>
        {ogoh && (
          <ChiqishOgohlantirish {...ogoh} onYop={ogohYop}
            onKassa={onKassa && (() => { setOgoh(null); onKassa() })}
            onChiqish={() => { setOgoh(null); onChiqish() }} />
        )}
      </div>
    )
  }

  return (
    <div className="ustki-joy" ref={joy}>
      <button type="button" className={ixcham ? 'shapka-xodim' : 'ustki-xodim'} aria-expanded={ochiq} aria-haspopup="menu"
        aria-label={ixcham ? `${xodim.ism}: profil va chiqish` : undefined} onClick={() => setOchiq(!ochiq)}>
        <span className="xodim-chip">
          <XodimBelgi xodim={xodim} harf={harf} />
          {!ixcham && <span><b>{xodim.ism}</b>{xodim.ism?.trim() !== rol && <small>{rol}</small>}</span>}
        </span>
        {!ixcham && <NavIkona nom="ong" className="tugma-ikon pastga" />}
      </button>
      {ochiq && (
        <div className="ustki-menyu" role="menu">
          {/* salon nomi bu yerda ham ortiqcha (foydalanuvchi) — telefonda faqat kim kirgani */}
          {ixcham && <p className="malumot"><b>{xodim.ism}</b>{xodim.ism?.trim() !== rol && ` · ${rol}`}</p>}
          {/* profil rasmi — kirish ekranidagi kartochkada va shapkada ko'rinadi */}
          <button type="button" role="menuitem" disabled={yuklanmoqda} onClick={() => fayl.current?.click()}>
            <NavIkona nom="kamera" className="tugma-ikon" />
            {yuklanmoqda ? 'Yuklanmoqda…' : xodim.rasm ? 'Profil rasmini almashtirish' : 'Profil rasmini yuklash'}
          </button>
          <input ref={fayl} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={rasmTanla} />
          {xodim.rasm && (
            <button type="button" role="menuitem" onClick={() => onRasmOchir().catch((err) => setRasmXato(err.message))}>
              <NavIkona nom="yop" className="tugma-ikon" />Rasmni olib tashlash
            </button>
          )}
          {rasmXato && <p className="xato ustki-menyu-xato" role="alert">{rasmXato}</p>}
          {/* xodim ilovadan chiqadi (PIN ekrani); salon logini qurilmada qoladi — keyingi xodim o'z PIN'i bilan kiradi.
              Smenadan chiqish bu emas — u Kassadagi «Pulni topshirib chiqish» */}
          <button type="button" role="menuitem" disabled={tekshirilmoqda} onClick={chiqishBos}>
            <NavIkona nom="chiqish" className="tugma-ikon" />Ilovadan chiqish
          </button>
        </div>
      )}
      {ogoh && (
        <ChiqishOgohlantirish {...ogoh} onYop={ogohYop}
          onKassa={onKassa && (() => { setOgoh(null); onKassa() })}
          onChiqish={() => { setOgoh(null); onChiqish() }} />
      )}
    </div>
  )
}

// «Siz hali smenadasiz» — Tasdiq oynasi uslubida. Ilova ildiziga (.ilova) chiqariladi: shapka shishasi ichida `fixed`
// kichrayib qolmasin, body'da esa yangi dizayn tokenlari (shrift, ranglar) tushmaydi.
function ChiqishOgohlantirish({ naqd, yolgiz, onKassa, onChiqish, onYop }) {
  const asosiy = useRef(null)
  useEffect(() => {
    asosiy.current?.focus()
    const esc = (e) => { if (e.key === 'Escape') onYop() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onYop])
  return createPortal(
    <div className="oyna-parda" onClick={onYop}>
      <div className="oyna" role="alertdialog" aria-modal="true" aria-labelledby="chiqish-ogoh-nom" aria-describedby="chiqish-ogoh-matn"
        onClick={(e) => e.stopPropagation()}>
        <h3 id="chiqish-ogoh-nom">Siz hali smenadasiz</h3>
        <p className="malumot" id="chiqish-ogoh-matn">
          Sizda <b>{som(naqd)}</b> naqd. {yolgiz
            ? "Ish kuni tugagan bo'lsa, avval smenani yoping."
            : "Ketayotgan bo'lsangiz, avval pulni topshirib chiqing — aks holda hamkasbingiz smenani yopa olmaydi."}
        </p>
        <div className="oyna-tugmalar">
          <button type="button" className="ikkinchi" onClick={onChiqish}>Baribir chiqish</button>
          {onKassa
            ? <button type="button" ref={asosiy} onClick={onKassa}>Kassaga o'tish</button>
            : <button type="button" ref={asosiy} onClick={onYop}>Qolish</button>}
        </div>
      </div>
    </div>,
    document.querySelector('.ilova') || document.body,
  )
}

// Xodim belgisi: profil rasmi, bo'lmasa ismning bosh harfi
export function XodimBelgi({ xodim, harf }) {
  return <i aria-hidden="true">{xodim.rasm ? <img src={xodim.rasm} alt="" /> : harf}</i>
}
