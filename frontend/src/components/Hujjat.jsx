import { useEffect, useState } from 'react'
import { hujjat, sanaMatni, som, xatoMatni } from '../api'

// Shartnoma, kvitansiya va zalog dalolatnomasi (FT-10.2, FT-7.4). «Chop etish» brauzerning chop etish oynasini
// ochadi — u yerdan printerga yuborish yoki PDF sifatida saqlash mumkin.
export default function Hujjat({ zakazId, tur, onYop }) {
  const [h, setH] = useState(null)
  const [xato, setXato] = useState('')

  useEffect(() => {
    hujjat(zakazId, tur).then(setH).catch((e) => setXato(xatoMatni(e)))
  }, [zakazId, tur])

  return (
    <div className="hujjat-oyna">
      <div className="hujjat-tugmalar chop-etilmaydi">
        <button className="ikkinchi" onClick={onYop}>← Orqaga</button>
        {h && <button onClick={() => window.print()}>Chop etish / PDF</button>}
      </div>
      {xato && <p className="xato">{xato}</p>}
      {h && (
        <article className="hujjat">
          <header>
            <h1>{h.sarlavha}</h1>
            <p>{sanaMatni(h.sana)}</p>
          </header>

          <table className="hujjat-tomonlar"><tbody>
            <tr>
              <td>
                <b>Salon:</b> {h.salon.yuridik_nom}<br />
                {h.salon.stir && <>STIR: {h.salon.stir}<br /></>}
                {h.salon.manzil && <>{h.salon.manzil}<br /></>}
                {h.salon.telefon}
              </td>
              <td>
                <b>Mijoz:</b> {h.mijoz.fio || '________________'}<br />
                Tel.: {h.mijoz.telefon}<br />
                Olib ketish: {sanaMatni(h.olib_ketish)}<br />
                Qaytarish: {sanaMatni(h.qaytarish)}
              </td>
            </tr>
          </tbody></table>

          {h.pozitsiyalar && (
            <table className="hujjat-jadval">
              <thead><tr><th>№</th><th>Buyum</th><th>Ijara narxi</th></tr></thead>
              <tbody>
                {h.pozitsiyalar.map((p, i) => (
                  <tr key={i}><td>{i + 1}</td><td>{p.nomi}</td><td>{som(p.narx)}</td></tr>
                ))}
              </tbody>
            </table>
          )}

          {h.tolovlar && (
            <table className="hujjat-jadval">
              <thead><tr><th>Sana</th><th>To'lov</th><th>Usul</th><th>Summa</th><th>Qabul qildi</th></tr></thead>
              <tbody>
                {h.tolovlar.map((t, i) => (
                  <tr key={i}><td>{sanaMatni(t.sana)}</td><td>{t.tur}</td><td>{t.usul}</td><td>{som(t.summa)}</td><td>{t.xodim}</td></tr>
                ))}
              </tbody>
            </table>
          )}

          {h.narx && (
            <table className="hujjat-jami"><tbody>
              {h.narx.ustama > 0 && <tr><td>Mavsumiy ustama</td><td>{som(h.narx.ustama)}</td></tr>}
              {h.narx.chegirma > 0 && <tr><td>Chegirma</td><td>−{som(h.narx.chegirma)}</td></tr>}
              <tr><td><b>Jami</b></td><td><b>{som(h.narx.jami)}</b></td></tr>
              <tr><td>To'langan</td><td>{som(h.narx.tolangan)}</td></tr>
              <tr><td>Qoldiq</td><td>{som(h.narx.qoldiq)}</td></tr>
            </tbody></table>
          )}

          {h.zaloglar && (
            <table className="hujjat-jadval">
              <thead><tr><th>Yorliq</th><th>Turi</th><th>Tavsif</th><th>Olingan</th><th>Qaytarilgan</th></tr></thead>
              <tbody>
                {h.zaloglar.map((z) => (
                  <tr key={z.yorliq}>
                    <td>{z.yorliq}</td><td>{z.turi}</td><td>{z.tavsif}</td><td>{z.olingan}</td>
                    <td>{z.qaytarilgan || z.holat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {h.qaytarish_akti && (
            <p>
              Qaytarish: {h.qaytarish_akti.sana}. Holat tekshiruvi: {h.qaytarish_akti.tekshiruv.toLowerCase()}.
              {h.qaytarish_akti.kechikish_kunlari > 0 && ` Kechikish: ${h.qaytarish_akti.kechikish_kunlari} kun.`}
              {h.qaytarish_akti.jarima > 0 && ` Jarima: ${som(h.qaytarish_akti.jarima)} (zalogdan ushlandi: ${som(h.qaytarish_akti.ushlab_qolingan)}, qarz: ${som(h.qaytarish_akti.qarz)}).`}
              {h.qaytarish_akti.tortilgan_gr != null && ` Tillo buyum qayta tortildi: ${h.qaytarish_akti.tortilgan_gr} g — ${h.qaytarish_akti.ogirlik_mos ? 'mos keldi' : 'mos kelmadi'}.`}
            </p>
          )}

          {h.bandlar && (
            <ol className="hujjat-bandlar">
              {h.bandlar.map((b) => <li key={b.raqam}><b>{b.sarlavha}.</b> {b.matn}</li>)}
            </ol>
          )}

          <table className="hujjat-imzolar"><tbody>
            <tr>{h.imzolar.map((i) => <td key={i}>{i}: ____________________</td>)}</tr>
          </tbody></table>
          <p className="hujjat-izoh">Zakazni rasmiylashtirdi: {h.sotuvchi}</p>
        </article>
      )}
    </div>
  )
}
