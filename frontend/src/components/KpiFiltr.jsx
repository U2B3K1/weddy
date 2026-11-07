import { Belgi } from './ZakazQatorlari'

// Ko'rsatkich kartasi-filtr (maket uslubi; Zakazlar, Liboslar…): rangli plitka-belgi, nom, katta son, izoh.
// Butun karta — bitta tugma (nom tugmasining cho'zilgan ::after i), `pastki` — uning ustidagi alohida kichik tugma
// (masalan, «ertaga — N ta»); bo'lmasa izoh matni. `xavf` — son qizil (kechikkan va h.k.).
// `onBos` berilmasa — oddiy ko'rsatkich (bosilmaydi; masalan, Smena hisoboti summalari). `trend` — o'ng tepadagi belgi.
export default function KpiFiltr({ nom, son, ikon, rang, izoh, tanlangan, xavf, onBos, pastki, trend }) {
  return (
    <div className={`dash-kpi-karta${onBos ? ' kpi-filtr' : ''}${tanlangan ? ' tanlangan' : ''}${xavf ? ' xavf' : ''}`}>
      <span className={`kpi-plitka ${xavf ? 'qizil' : rang}`}><Belgi nom={ikon} className="kpi-ikon" /></span>
      <div className="kpi-matn">
        {onBos ? (
          <button type="button" className="kpi-filtr-tugma kpi-nom" aria-pressed={Boolean(tanlangan)}
            aria-label={`${nom}: ${son ?? 0}`} onClick={onBos}>{nom}</button>
        ) : <span className="kpi-nom">{nom}</span>}
        <b>{son ?? '—'}</b>
        {pastki || <small>{izoh}</small>}
      </div>
      {trend}
    </div>
  )
}
