import { useCallback, useEffect, useState } from 'react'
import { telegramHolat, telegramUlash, telegramUzish, xatoMatni } from '../api'

// 4.14: eslatmalar bosh ekranda majburiy chiqadi; Telegram — qo'shimcha kanal. Xodim o'z akkauntini bir martalik kod bilan ulaydi.
export default function TelegramBlok({ rahbar }) {
  const [h, setH] = useState(null)
  const [ulash, setUlash] = useState(null)
  const [xato, setXato] = useState('')

  const yukla = useCallback(() => telegramHolat().then(setH).catch(() => {}), [])
  useEffect(() => { yukla() }, [yukla])

  // Kod ko'rsatilgandan keyin bot ulaganini tekshirib turadi
  useEffect(() => {
    if (!ulash) return undefined
    const t = setInterval(async () => {
      const yangi = await telegramHolat().catch(() => null)
      if (yangi?.ulangan) { setH(yangi); setUlash(null) }
    }, 3000)
    return () => clearInterval(t)
  }, [ulash])

  if (!h) return null
  const bajar = (fn) => async () => { setXato(''); try { await fn() } catch (e) { setXato(xatoMatni(e)) } }

  return (
    <details className="blok amal">
      <summary>Telegram xabarlari · {h.ulangan ? 'ulangan' : 'ulanmagan'}</summary>
      <div className="stack">
        {xato && <p className="xato">{xato}</p>}
        {!h.sozlangan && <p className="ogohlantirish">Bot hali serverda sozlanmagan — xabarlar yuborilmaydi (bosh ekrandagi eslatmalar ishlayveradi).</p>}
        {h.ulangan ? (
          <>
            <p className="malumot">
              Eslatmalar{rahbar ? ', chegirma so\'rovlari, kassa farqi va kunlik hisobot' : ''} shu Telegram akkauntingizga keladi.
              {rahbar && ' Kirishda PIN dan keyin Telegram kod so\'raladi.'}
            </p>
            <button className="ikkinchi" onClick={bajar(async () => { await telegramUzish(); await yukla() })}>Telegramni uzish</button>
          </>
        ) : ulash ? (
          <>
            <p>Telegramda botni oching{ulash.bot ? <> (<b>@{ulash.bot}</b>)</> : ''} va shu xabarni yuboring:</p>
            <p className="kod">/start {ulash.kod}</p>
            {ulash.havola && <a className="tugma-havola" href={ulash.havola} target="_blank" rel="noreferrer">Botni ochish</a>}
            <p className="malumot">Kod 15 daqiqa amal qiladi. Ulangach bu oyna o'zi yangilanadi.</p>
          </>
        ) : (
          <button className="ikkinchi" onClick={bajar(async () => setUlash(await telegramUlash()))}>Telegramni ulash</button>
        )}
      </div>
    </details>
  )
}
