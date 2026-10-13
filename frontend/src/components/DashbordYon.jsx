import { useEffect, useState } from 'react'
import { dashbord, qarzdorlar, som } from '../api'

// Chap paneldagi ixcham dashbord xulosasi (faqat rahbar, keng ekran):
// markazdagi ikkilamchi bloklar o'rniga bu yerda tez ko'rinib turadi.
export default function DashbordYon({ onBolim }) {
  const [d, setD] = useState(null)
  const [qarz, setQarz] = useState(null)

  useEffect(() => {
    let faol = true
    const yukla = async () => {
      try {
        const [a, b] = await Promise.all([dashbord('oy', ''), qarzdorlar()])
        if (faol) { setD(a); setQarz(b) }
      } catch { /* jimgina: asosiy dashbord xatoni o'zi ko'rsatadi */ }
    }
    yukla()
    const t = setInterval(yukla, 60000)
    return () => { faol = false; clearInterval(t) }
  }, [])

  if (!d) return null
  const { bugun, qoplamagan } = d
  const och = (b) => () => onBolim?.(b)

  return (
    <div className="dashbord-yon">
      <h4>Bugun</h4>
      <button type="button" className="qator-btn" onClick={och('hisobotlar')}><span>Tushum</span><b>{som(bugun.tushum_jami)}</b></button>
      <button type="button" className="qator-btn" onClick={och('kassa')}><span>Smena</span><b>{bugun.smena_ochiq ? 'ochiq' : 'yopiq'}</b></button>
      <button type="button" className="qator-btn" onClick={och('bosh')}><span>Olib / qaytar</span><b>{bugun.olib_ketiladi} / {bugun.qaytariladi}</b></button>

      {qarz && (qarz.qarzdorlar.length > 0 || qarz.qoldiq_kutilmoqda.length > 0) && (
        <>
          <h4>Qarzdorlar ({qarz.qarzdorlar.length})</h4>
          {qarz.qarzdorlar.slice(0, 6).map((q) => (
            <button key={q.id} type="button" className="qator-btn qizil" onClick={och('zakazlar')}>
              <span>#{q.raqam} {q.mijoz}</span><b>{som(q.qarz)}</b>
            </button>
          ))}
          {qarz.qarzdorlar.length > 6 && <p className="malumot">yana {qarz.qarzdorlar.length - 6} ta…</p>}
          {qarz.qoldiq_kutilmoqda.length > 0 && (
            <>
              <h4>Qoldiq kutilmoqda ({qarz.qoldiq_kutilmoqda.length})</h4>
              {qarz.qoldiq_kutilmoqda.slice(0, 6).map((q) => (
                <button key={q.id} type="button" className="qator-btn" onClick={och('zakazlar')}>
                  <span>#{q.raqam} {q.mijoz}</span><b>{som(q.qoldiq)}</b>
                </button>
              ))}
            </>
          )}
        </>
      )}

      {qoplamagan && qoplamagan.soni > 0 && (
        <>
          <h4>Qoplamagan</h4>
          <button type="button" className="qator-btn" onClick={och('hisobotlar')}>
            <span>{qoplamagan.soni} ta · {qoplamagan.kun} kun</span>
          </button>
        </>
      )}
    </div>
  )
}
