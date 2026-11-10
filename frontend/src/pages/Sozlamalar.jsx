import { Fragment, useCallback, useEffect, useState } from 'react'
import Integratsiyalar from '../components/Integratsiyalar'
import MavsumiyNarx from '../components/MavsumiyNarx'
import TayyorChegirmalar from '../components/TayyorChegirmalar'
import Promokodlar from './Promokodlar'
import Jurnal from '../components/Jurnal'
import NavIkona from '../components/NavIkona'
import Sahifali from '../components/Sahifalash'
import Oyna from '../components/Oyna'
import Tasdiq from '../components/Tasdiq'
import { BoshAmal, SozlamaYon } from '../components/BoshJoy'
import { Almash, BelgiKarta, Qadam, RadioKarta, SPanel, SQator, Yorliq } from '../components/SozlamaUI'
import { ESKI_BOLIM, GURUHLAR, SOZLAMA_BOLIMLAR, sozlamaQidir } from './sozlamaBolimlari'
import {
  smsJurnali, filialOzgartir, filialQosh, filiallar, qurilmaFilial, qurilmaOchirish, qurilmaTasdiq, qurilmalar, salonParol, salonRekvizit, salonRekvizitSaqla, yordamBekor, yordamBer,
  yordamRuxsati, sozlamalar, sozlamaSaqla, xatoMatni, guruhla, xodimOzgartir, xodimQosh, xodimTelegramUlash, xodimlarBoshqaruv,
} from '../api'

// GET /sozlamalar/ javobidagi faqat o'qiladigan belgilar (integratsiyalardan) saqlashga yuborilmaydi
const faqatSozlama = ({ fiskal_eslatma: _f, fiskal_izoh: _i, tolov_havolasi: _t, ...qolgan }) => qolgan
const ROLLAR = [['sotuvchi', 'Sotuvchi'], ['kassir', 'Kassir'], ['rahbar', 'Rahbar']]
// Rol o'zgarganda nima bo'lishi — tasdiq oynasida (B-07)
const ROL_IZOH = {
  rahbar: "hamma bo'limni ko'radi: hisobot, sozlama, tannarx va xodimlar",
  kassir: "pul qabul qiladi va kassani yuritadi; hisobot va sozlamani ko'rmaydi",
  sotuvchi: "zakaz oladi; hisobot, sozlama va tannarxni ko'rmaydi",
}
// Server vaqti → mahalliy «07.11.2026 02:10» (boshqa joylardagi sana formati bilan bir xil, B-38)
const vaqtMatni = (v) => {
  if (!v) return ''
  const t = new Date(v), n = (x) => String(x).padStart(2, '0')
  return `${n(t.getDate())}.${n(t.getMonth() + 1)}.${t.getFullYear()} ${n(t.getHours())}:${n(t.getMinutes())}`
}
const boshHarf = (ism) => String(ism || '?').trim().split(/\s+/).slice(0, 2).map((s) => s.charAt(0).toUpperCase()).join('')

// Kanvas (SozlamaBolimShisha): bo'lim tanlansa uning GURUHI bir sahifada — har bo'lim alohida panel. Panellar tartibi kanvasdagidek
// (chap ro'yxat tartibi sozlamaBolimlari.js da); ichki massiv — yonma-yon ikki panel.
const PANEL_TARTIBI = {
  'Zakaz qoidalari': ['bandlik', 'kechikish', 'qaytarish', 'shartnoma'],
  'Narx va chegirma': ['promokod', 'chegirmalar', 'mavsumiy'],
  Liboslar: ['katalog', 'artikul'],
  'Salon va xodimlar': ['xodimlar', 'kassa', 'bonus', ['rekvizitlar', 'filiallar']],
  "Ko'rinish va xabarlar": ['integratsiyalar', 'sms', 'dashbord'],
  Xavfsizlik: ['qurilmalar', 'yordam', 'jurnal'],
}
const ZALOG = [
  ['zalog_pul', 'Pul', 'Naqd yoki karta — libos qaytgach qaytariladi'],
  ['zalog_hujjat', 'Hujjat', 'Pasport nusxasi yoki ID karta'],
  ['zalog_tillo', 'Tillo buyum', "Uzuk, bilaguzuk — qarz yopilguncha ushlanadi"],
]
const foizRang = (f) => (Number(f) >= 100 ? 'yashil' : Number(f) <= 0 ? 'qizil' : 'tilla')

// Sozlama bo'limlarining statik ro'yxati (sozlamaBolimlari.js) — chap ro'yxat ham, mazmun ham shu ro'yxatga mos.
// Pastdagi `panellar` dagi kalitlar shu ro'yxatdagi id lar bilan bir xil bo'lishi shart.

// 4.16: admin panel. Keng ekranda bo'limlar sahifaning o'zida chapda; telefonda — sahifa tepasidagi ochiladigan menyu.
export default function Sozlamalar({ menId, bolim, onBolim }) {
  const [s, setS] = useState(null)
  const [xodimlar, setXodimlar] = useState([])
  const [rek, setRek] = useState(null)
  const [rekAsl, setRekAsl] = useState(null)
  const [qur, setQur] = useState([])
  const [yordam, setYordam] = useState(null)
  const [yangiParol, setYangiParol] = useState('')
  const [parolOchiq, setParolOchiq] = useState(false)
  const [fil, setFil] = useState([])
  const [sms, setSms] = useState(null)
  useEffect(() => { smsJurnali().then(setSms).catch(() => {}) }, [])
  const [yangiFilial, setYangiFilial] = useState({ nomi: '', manzil: '' })
  const [filialForma, setFilialForma] = useState(false)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  // Serverdagi holat — o'zgarish bor-yo'qligini bilish uchun (saqlash paneli faqat o'zgarishda chiqadi)
  const [asl, setAsl] = useState(null)
  const [xodimOyna, setXodimOyna] = useState(false)
  const [bandOchiq, setBandOchiq] = useState(null)  // tahrirlanayotgan shartnoma bandi
  // Tor ekranda bo'lim almashish menyusi (keng ekranda bo'limlar chapda doim ko'rinadi).
  const [menuOchiq, setMenuOchiq] = useState(false)
  const [qidiruv, setQidiruv] = useState('')
  const [chiqarSurov, setChiqarSurov] = useState(null)  // ro'yxatdan chiqariladigan qurilma

  const yukla = useCallback(async () => {
    const [a, b, c, d, e, f] = await Promise.all([sozlamalar(), xodimlarBoshqaruv(), salonRekvizit(), qurilmalar(), yordamRuxsati(), filiallar(true)])
    setS(a); setAsl(JSON.stringify(a)); setXodimlar(b); setRek(c); setRekAsl(JSON.stringify(c)); setQur(d); setYordam(e); setFil(f.filiallar)
  }, [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  // Bo'lim tanlanganda: guruh sahifasida shu panelga o'tadi (guruhning birinchi bo'limi — sahifa boshiga)
  const yuklandi = s !== null
  useEffect(() => {
    if (!yuklandi || bolim === 'bosh') return
    const id = ESKI_BOLIM[bolim] || bolim
    const g = SOZLAMA_BOLIMLAR.find((b) => b.id === id)?.guruh
    if (!g || PANEL_TARTIBI[g].flat()[0] === id) window.scrollTo(0, 0)
    else document.getElementById(`soz-${id}`)?.scrollIntoView({ block: 'start' })
  }, [bolim, yuklandi])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }

  if (!s) return <p className="malumot">{xabar.matn || 'Yuklanmoqda…'}</p>
  const set = (k, v) => setS({ ...s, [k]: v })
  const qoida = (i, j) => (e) => set('qaytarish_qoidasi',
    s.qaytarish_qoidasi.map((q, n) => (n === i ? q.map((v, m) => (m === j ? Number(e.target.value) : v)) : q)))
  const vaqt = (k) => String(s[k] || '').slice(0, 5)
  const bandlar = s.shartnoma_bandlari || []
  const setBand = (i, k, v) => set('shartnoma_bandlari', bandlar.map((x, n) => (n === i ? { ...x, [k]: v } : x)))
  const faolFilial = fil.some((f) => f.faol)

  // B-37: har bo'limda bitta usul — maydon va almashtirgichlar (rekvizitlar ham) pastdagi umumiy panel orqali saqlanadi;
  // ro'yxat elementlari (qoida, filial, xodim, qurilma) — har biri o'z tugmasi bilan
  const sOzgardi = JSON.stringify(s) !== asl
  const rekOzgardi = rek !== null && JSON.stringify(rek) !== rekAsl
  const saqlash = () => (rekOzgardi && !String(rek.nomi || '').trim()
    ? setXabar({ turi: 'xato', matn: "Salon nomi bo'sh bo'lmasligi kerak (Rekvizitlar)." })
    : bajar(async () => {
    if (sOzgardi) await sozlamaSaqla({ ...faqatSozlama(s), shartnoma_bandlari: bandlar.filter((b) => b.sarlavha.trim() || b.matn.trim()) })
    // faqat o'zgargan maydonlar: bo'sh qolgan boshqa maydon («yuridik nom» va h.k.) saqlashni to'xtatmasin
    if (rekOzgardi) {
      const a = JSON.parse(rekAsl)
      await salonRekvizitSaqla(Object.fromEntries(Object.entries(rek).filter(([k, v]) => v !== a[k])))
    }
  }, rekOzgardi && !sOzgardi ? 'Rekvizitlar saqlandi.' : 'Sozlamalar saqlandi.'))

  // Almashtirgichli qator (bitta sozlama maydoni)
  const almashQator = (k, nomi, izoh) => (
    <SQator key={k} nomi={nomi} izoh={izoh}><Almash checked={s[k]} onChange={(v) => set(k, v)} nomi={nomi} /></SQator>
  )

  const panellar = {
    bandlik: () => (
      <SPanel id="bandlik" ikon="kalendar" nomi="Bron va garov" izoh="Libos qancha vaqt band turadi va qanday garov olinadi">
        <div className="soz-uch">
          <div className="soz-qiymat-k">
            <b>Tozalash buferi</b>
            <Qadam qiymat={s.bufer_kun} onChange={(v) => set('bufer_kun', v)} nomi="Tozalash buferi, kun" min={0} max={30} birlik="kun" />
            <small>Qaytgan libos keyingi zakazgacha shuncha kun band turadi. Libos yoki kategoriyada alohida berilmagan bo'lsa.</small>
          </div>
          <div className="soz-qiymat-k">
            <b>Avanssiz bron</b>
            <Qadam qiymat={s.vaqtinchalik_bron_soat} onChange={(v) => set('vaqtinchalik_bron_soat', v)} nomi="Avanssiz bron, soat" min={1} max={168} birlik="soat" />
            <small>Avans to'lanmagan «vaqtinchalik» bron shuncha soatdan keyin o'zi bo'shaydi.</small>
          </div>
          <div className="soz-qiymat-k">
            <b>Libosni qulflash</b>
            <Qadam qiymat={s.qulf_daqiqa} onChange={(v) => set('qulf_daqiqa', v)} nomi="Libosni qulflash, daqiqa" min={1} max={120} birlik="daqiqa" />
            <small>Sotuvchi tanlagan libos boshqa sotuvchidan shuncha daqiqa yashiriladi — ikki kishi bir libosni sotmaydi.</small>
          </div>
        </div>
        <div className="soz-kichik-bosh"><b>Garov turlari</b><small>Libos berishda qaysi garovlarni qabul qilasiz. Zakazda faqat belgilanganlari chiqadi.</small></div>
        <div className="soz-uch" role="group" aria-label="Garov turlari">
          {ZALOG.map(([k, nomi, izoh]) => <BelgiKarta key={k} checked={s[k]} onChange={(v) => set(k, v)} nomi={nomi} izoh={izoh} />)}
        </div>
      </SPanel>
    ),
    kechikish: () => (
      <SPanel id="kechikish" ikon="soat" nomi="Kechikish jarimasi" izoh="Libosni vaqtida qaytarmagan mijozga"
        ong={<Almash checked={s.kechikish_jarimasi} onChange={(v) => set('kechikish_jarimasi', v)} nomi="Kechikish jarimasi yoqilgan" />}>
        <SQator nomi="Kunlik summa" className={s.kechikish_jarimasi ? '' : 'ochiq-emas'}
          izoh={s.kechikish_jarimasi
            ? `Qaytarishda o'zi hisoblanadi: libos 2 kun kechiksa — ${guruhla(2 * (Number(s.kechikish_kunlik_summa) || 0))} so'm.`
            : "O'chiq: kechikkan mijozdan jarima olinmaydi."}>
          <Qadam qiymat={s.kechikish_kunlik_summa} onChange={(v) => set('kechikish_kunlik_summa', v)} nomi="Kunlik jarima, so'm" summa
            qadam={10000} max={100_000_000} birlik="so'm" disabled={!s.kechikish_jarimasi} />
        </SQator>
        <SQator nomi="Qaytmagan libos eslatmasi"
          izoh="Qaytish kuni kelgan, lekin «Qaytarildi» qilinmagan libos haqida sotuvchi va rahbarga Telegramda — har kuni bir marta, libos qabul qilinguncha.">
          <input type="time" className="soz-tanlov" aria-label="Qaytmagan libos eslatmasi vaqti" value={vaqt('qaytarish_tekshiruv_vaqti')}
            onChange={(e) => e.target.value && set('qaytarish_tekshiruv_vaqti', e.target.value)} />
        </SQator>
      </SPanel>
    ),
    qaytarish: () => {
      const q = s.qaytarish_qoidasi
      return (
        <SPanel id="qaytarish" ikon="qaytar" nomi="Avans qaytarish" izoh="Zakaz bekor qilinganda avansning qancha qismi qaytadi">
          {'avans_foizi' in s && <AvansFoizi s={s} set={set} />}
          <SQator nomi="Qoida nimaga qo'llanadi"
            izoh={s.qaytarish_asosi === 'tolangan' ? "Qoida mijoz to'lagan hamma summaga qo'llanadi." : "Avansdan ortiq oldindan to'langan qoldiq har doim to'liq qaytadi."}>
            <select className="soz-tanlov" aria-label="Qoida nimaga qo'llanadi" value={s.qaytarish_asosi} onChange={(e) => set('qaytarish_asosi', e.target.value)}>
              <option value="avans">Faqat avansga</option>
              <option value="tolangan">Hamma to'langan summaga</option>
            </select>
          </SQator>
          <table className="soz-jadval soz-qoida">
            <thead><tr><th>Olib ketishgacha qolgan kun, kamida</th><th className="ong">Qaytariladi</th></tr></thead>
            <tbody>
              {q.map(([kun, foiz], i) => {
                const oxirgi = i === q.length - 1
                return (
                  <tr key={i}>
                    <td>{oxirgi
                      ? (i > 0 ? `${q[i - 1][0]} kundan kam` : 'Har qanday muddat')
                      : <span className="soz-ichki"><input type="number" min="0" value={kun} onChange={qoida(i, 0)} aria-label={`${i + 1}-qoida: qolgan kun, kamida`} />kun</span>}
                    </td>
                    <td className="ong">
                      <span className={`soz-ichki ${foizRang(foiz)}`}>
                        <input type="number" min="0" max="100" value={foiz} onChange={qoida(i, 1)} aria-label={`${i + 1}-qoida: qaytariladigan foiz`} />%
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="soz-misol"><b>Misol:</b> olib ketishgacha qolgan kunga qarab {s.qaytarish_asosi === 'tolangan' ? "to'langan summaning" : 'avansning'} shu
            qismi qaytariladi, qolgani salonda qoladi. Avans 1 mln, qoldiq 4 mln to'langan, qoida 50% — {s.qaytarish_asosi === 'tolangan' ? '2,5 mln' : '4,5 mln'} qaytariladi.</p>
        </SPanel>
      )
    },
    shartnoma: () => (
      <SPanel id="shartnoma" ikon="hujjat" nomi="Shartnoma bandlari" izoh="Ijara shartnomasiga qo'shiladigan bandlar"
        ong={bandlar.length < 15 && (
          <button type="button" className="ikkinchi kichik" onClick={() => { set('shartnoma_bandlari', [...bandlar, { sarlavha: '', matn: '' }]); setBandOchiq(bandlar.length) }}>
            Band qo'shish
          </button>
        )}>
        {bandlar.length === 0 && <p className="soz-izoh">Qo'shimcha band yo'q — shartnomada faqat avtomatik bandlar chiqadi.</p>}
        {bandlar.map((b, i) => (bandOchiq === i ? (
          <div key={i} className="soz-tahrir stack">
            <label>Sarlavha<input value={b.sarlavha} maxLength={100} onChange={(e) => setBand(i, 'sarlavha', e.target.value)} /></label>
            <label>Matn<textarea rows={3} value={b.matn} maxLength={2000} onChange={(e) => setBand(i, 'matn', e.target.value)} /></label>
            <div className="soz-tugmalar">
              <button type="button" className="kichik" onClick={() => setBandOchiq(null)}>Tayyor</button>
              <button type="button" className="ikkinchi kichik" onClick={() => { set('shartnoma_bandlari', bandlar.filter((_, n) => n !== i)); setBandOchiq(null) }}>
                Bandni olib tashlash
              </button>
            </div>
          </div>
        ) : (
          <SQator key={i} className="soz-band" nomi={`${i + 1}. ${b.sarlavha.trim() || 'Sarlavhasiz band'}`} izoh={b.matn}>
            <button type="button" className="havola" onClick={() => setBandOchiq(i)}>Tahrirlash</button>
          </SQator>
        )))}
        <p className="soz-izoh">Ijara muddati, to'lov, garov, jarima va avans qaytarish bandlari sozlamalardan avtomatik yoziladi — bu yerdagilar ulardan keyin chiqadi.</p>
      </SPanel>
    ),
    promokod: () => (
      <SPanel id="promokod" ikon="yorliq" nomi="Promokodlar" izoh="Salonchi va aksiya kodlari — qoidalar va kodlar bir joyda"
        ong={<Almash checked={s.promokodlar_bolimi} onChange={(v) => set('promokodlar_bolimi', v)} nomi="Promokodlar bo'limi yoqilgan" />}>
        {almashQator('promokod_tasdiqsiz', "Sotuvchi tasdiqsiz qo'llaydi", "O'chirilsa, promokod rahbar tasdig'ini kutadi.")}
        {almashQator('promokod_chegirma_birga', "Promokod va qo'shimcha chegirma birga", "O'chiq: bittasi tanlanadi — salon ikki marta chegirma bermaydi.")}
        {almashQator('salonchi_kodlari', "Salonchi kodi zakazni salonchiga bog'laydi", "Salonchi kodi bilan kelgan mijoz Salonchilar statistikasiga o'zi tushadi.")}
        {s.promokodlar_bolimi ? <Promokodlar /> : <p className="soz-izoh">Bo'lim o'chiq — kodlar ro'yxati ko'rinmaydi.</p>}
      </SPanel>
    ),
    chegirmalar: () => <TayyorChegirmalar />,
    mavsumiy: () => (
      <SPanel id="mavsumiy" ikon="quyosh" nomi="Mavsumiy narx" izoh="To'y mavsumida narxga ustama — zakazga o'zi qo'shiladi"
        ong={<Almash checked={s.mavsumiy_narx} onChange={(v) => set('mavsumiy_narx', v)} nomi="Mavsumiy narx yoqilgan" />}>
        {!s.mavsumiy_narx && <p className="soz-izoh">O'chiq: qoidalar saqlanadi, lekin narxga ta'sir qilmaydi.</p>}
        <MavsumiyNarx />
      </SPanel>
    ),
    katalog: () => (
      <SPanel id="katalog" ikon="katalog" nomi="Libos qo'shish va manekin" izoh="Kim katalogga libos va aksessuar qo'sha oladi">
        {almashQator('sotuvchi_libos_qoshadi', "Sotuvchi libos va aksessuar qo'sha oladi",
          "Rahbar narx va tannarxni kiritib tasdiqlagach ijaraga chiqadi — tannarxsiz libos katalogga tushmaydi. O'chirilsa — faqat rahbar qo'shadi.")}
        {almashQator('manekin', 'Raqamli manekin', "Libos rasmini fonsiz qilib manekinda ko'rsatadi.")}
      </SPanel>
    ),
    artikul: () => {
      const xona = s.artikul_xona || 4
      const namuna = (n) => `${s.artikul_prefiks || ''}${String(n).padStart(xona, '0')}`
      const bosh = Number(s.artikul_boshlanish) || 0
      return (
        <SPanel id="artikul" ikon="raqam" nomi="Libos artikuli" izoh="Yorliqdagi kod — sanoq, zakaz va hisobot shu bilan ishlaydi">
          {almashQator('artikul_avto', "Raqam avtomatik qo'yilsin",
            `Libos qo'shishda artikul bo'sh qoldirilsa, tizim keyingisini beradi (oxirgisi ${namuna(57)} bo'lsa — ${namuna(58)}). Ikki xodim bir vaqtda qo'shsa ham takrorlanmaydi.`)}
          <SQator nomi="Prefiks" izoh="Har artikul boshidagi bir xil qism, masalan «L-» yoki «OQ-». Ixtiyoriy.">
            <input className="soz-tanlov soz-prefiks" maxLength={10} placeholder="L-" aria-label="Artikul prefiksi" value={s.artikul_prefiks}
              onChange={(e) => set('artikul_prefiks', e.target.value.replace(/\s/g, ''))} />
          </SQator>
          {s.artikul_avto ? (
            <>
              <SQator nomi="Sanoq nechidan boshlansin" izoh="Salonda shu prefiksli kattaroq raqam bo'lsa, undan keyingisi beriladi.">
                <Qadam qiymat={s.artikul_boshlanish} onChange={(v) => set('artikul_boshlanish', v)} nomi="Sanoq nechidan boshlansin" min={0} max={99_999_999} />
              </SQator>
              <SQator nomi="Raqam necha xonali" izoh={`Namuna: ${namuna(bosh)}, ${namuna(bosh + 1)}, ${namuna(bosh + 2)}…`}>
                <select className="soz-tanlov" aria-label="Raqam necha xonali" value={xona} onChange={(e) => set('artikul_xona', Number(e.target.value))}>
                  {[1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} — {'0'.repeat(n - 1)}1</option>)}
                </select>
              </SQator>
            </>
          ) : <p className="soz-izoh">Avtomatik raqam o'chiq: artikulni har safar o'zingiz yozasiz.</p>}
        </SPanel>
      )
    },
    xodimlar: () => (
      <SPanel id="xodimlar" ikon="mijozlar" nomi="Xodimlar" izoh="Har kim o'z PIN kodi bilan kiradi; rol nimani ko'rishini belgilaydi"
        ong={<button type="button" className="ikkinchi kichik" onClick={() => setXodimOyna(true)}>Xodim qo'shish</button>}>
        <div className="soz-xq bosh" aria-hidden="true"><span>Xodim</span><span>Rol</span><span>PIN</span><span>Telegram</span><span /></div>
        {xodimlar.map((x) => (
          <Xodim key={x.id} x={x} men={x.id === menId} filiallar={fil} onOzgartir={(b, ok) => bajar(() => xodimOzgartir(x.id, b), ok)} />
        ))}
        {xodimlar.some((x) => x.faol && !x.telegram_ulangan) && (
          <p className="soz-izoh">Telegram ulanmagan xodimga pul topshirish tasdig'i va eslatmalar bormaydi — xodim menyusidan ulang.</p>
        )}
        {xodimOyna && (
          <Oyna sarlavha="Xodim qo'shish" onYop={() => setXodimOyna(false)}>
            <XodimForma filiallar={fil} onYuborish={async (b) => { const ok = await bajar(() => xodimQosh(b), "Xodim qo'shildi."); if (ok) setXodimOyna(false); return ok }} />
          </Oyna>
        )}
      </SPanel>
    ),
    kassa: () => (
      <SPanel id="kassa" ikon="kassa" nomi="Kassa — kim pul qabul qiladi" izoh="Ochiq smenani yopib, keyin almashtiring. «Saqlash» bosilgach kuchga kiradi.">
        <div className="soz-ikki" role="radiogroup" aria-label="Kim pul qabul qiladi">
          <RadioKarta name="kassa_rejimi" checked={s.kassa_rejimi === 'sotuvchi'} onChange={() => set('kassa_rejimi', 'sotuvchi')} nomi="Sotuvchining o'zi kassir"
            izoh="Har sotuvchi o'z mijozidan pul oladi va o'z naqdiga javob beradi. Ketishda pulni topshiradi — qabul qiluvchi Telegramda tasdiqlaydi." />
          <RadioKarta name="kassa_rejimi" checked={s.kassa_rejimi === 'kassir'} onChange={() => set('kassa_rejimi', 'kassir')} nomi="Alohida kassir"
            izoh="Sotuvchi faqat zakaz oladi; pulni kassir qabul qiladi. Kassada sotuvchining zakazi «To'lov kutayotganlar» da chiqadi. Kamida bitta xodimga «Kassir» roli kerak." />
        </div>
        {almashQator('otkazma_tasdigi', "O'tkazmani rahbar tasdiqlaydi", "Telegramda «Hisobingizga tushdimi?» — Keldi / Kelmadi. «Kelmadi» bo'lsa, to'lov hisobdan chiqadi va qoldiq qayta chiqadi.")}
        {almashQator('terminal_sverkasi', 'Smena yopishda terminal hisobotini solishtirish', "Terminal chiqargan kunlik summa kiritiladi; farq bo'lsa rahbarga xabar.")}
      </SPanel>
    ),
    bonus: () => (
      <SPanel id="bonus" ikon="sovga" nomi="Sotuvchi bonusi" izoh="Qaytarib olingan zakazlar summasidan foiz"
        ong={<Almash checked={s.sotuvchi_bonusi} onChange={(v) => set('sotuvchi_bonusi', v)} nomi="Sotuvchi bonusi yoqilgan" />}>
        <SQator nomi="Bonus foizi" className={s.sotuvchi_bonusi ? '' : 'ochiq-emas'}
          izoh="Zakaz qaytarilgan oyda foydadan o'zi ayiriladi — bonusni berganda xarajatga qayta yozmang. Har sotuvchi summasi: Hisobot → «Sotuvchi bonusi».">
          <Qadam qiymat={s.bonus_foiz} kasr qadam={0.5} max={100} birlik="%" nomi="Bonus, zakazlar summasidan %" disabled={!s.sotuvchi_bonusi}
            onChange={(v) => set('bonus_foiz', v)} />
        </SQator>
      </SPanel>
    ),
    rekvizitlar: () => (
      <SPanel id="rekvizitlar" ikon="bino" nomi="Rekvizitlar" izoh="Shartnoma va kvitansiyada chiqadi">
        {!rek ? <p className="soz-izoh">Yuklanmoqda…</p> : (
          <div className="soz-kv-royxat">
            {[['nomi', 'Salon nomi *'], ['yuridik_nom', 'Yuridik nom'], ['stir', 'STIR'], ['manzil', 'Manzil'], ['telefon', 'Telefon']].map(([k, nom]) => (
              <label key={k} className="soz-kv"><span>{nom}</span>
                <input value={rek[k] || ''} placeholder="kiritilmagan" onChange={(e) => setRek({ ...rek, [k]: e.target.value })} />
              </label>
            ))}
          </div>
        )}
      </SPanel>
    ),
    filiallar: () => (
      <SPanel id="filiallar" ikon="joy" nomi="Filiallar" izoh="Qurilma qaysi filialga biriktirilgan bo'lsa, zakaz o'shanga yoziladi"
        ong={<button type="button" className="ikkinchi kichik" aria-expanded={filialForma} onClick={() => setFilialForma(!filialForma)}>{filialForma ? 'Yopish' : "Filial qo'shish"}</button>}>
        {fil.length === 0 && <p className="soz-izoh">Filial yo'q — salon bitta joyda ishlaydi.</p>}
        {fil.map((f) => (
          <FilialQator key={f.id} f={f} qurilma={qur.filter((q) => q.filial === f.id).length}
            onFaol={() => bajar(() => filialOzgartir(f.id, { faol: !f.faol }), f.faol ? 'Filial nofaol qilindi.' : 'Filial faollashtirildi.')}
            onSaqla={(b) => bajar(() => filialOzgartir(f.id, b), 'Filial saqlandi.')} />
        ))}
        {filialForma && (
          <div className="stack soz-tahrir">
            <h4 className="r2-kichik-sarlavha">Yangi filial</h4>
            <label>Filial nomi *<input placeholder="masalan: Chilonzor" value={yangiFilial.nomi} maxLength={100} onChange={(e) => setYangiFilial({ ...yangiFilial, nomi: e.target.value })} /></label>
            <label>Manzil<input value={yangiFilial.manzil} maxLength={300} onChange={(e) => setYangiFilial({ ...yangiFilial, manzil: e.target.value })} /></label>
            <div className="soz-tugmalar">
              <button type="button" className="kichik" disabled={!yangiFilial.nomi.trim()}
                onClick={() => bajar(() => filialQosh(yangiFilial), "Filial qo'shildi.").then((ok) => { if (ok) { setYangiFilial({ nomi: '', manzil: '' }); setFilialForma(false) } })}>Qo'shish</button>
            </div>
          </div>
        )}
        {faolFilial && almashQator('filial_kassasi', 'Har filialda alohida kassa',
          "Yoqilsa, har filial qurilmasi o'z smenasini ochadi; o'chiq bo'lsa salonda bitta umumiy kassa. Ochiq smenalarni avval yoping.")}
        <p className="soz-izoh">Filiallar soni tarif bilan cheklangan.</p>
      </SPanel>
    ),
    integratsiyalar: () => <Integratsiyalar />,
    sms: () => (
      <SPanel id="sms" ikon="xabar" nomi="Mijozga SMS" izoh="Eskiz orqali — har SMS balansdan (Eskiz tarifi)">
        {almashQator('sms_eslatma', 'Ertaga olib ketish va qaytarish eslatmasi', "Mijozga kechqurun: ertaga libosni olib ketish yoki qaytarish haqida. Har zakazga bir marta.")}
        {almashQator('sms_kvitansiya', "To'lovdan keyin SMS kvitansiya",
          "«Zakaz #123 uchun 2 000 000 so'm qabul qilindi (naqd)» — xodim kamroq yoki boshqa usul bilan yozsa, mijoz darhol ko'radi.")}
        {sms && !sms.sozlangan && (
          <p className="soz-ogoh">Eskiz.uz hisobi kiritilmagan (Integratsiyalar → Eskiz SMS): SMS lar hozircha yuborilmaydi, faqat jurnalga yoziladi.</p>
        )}
        {sms && sms.xabarlar.length > 0 && (
          <table className="soz-jadval">
            <thead><tr><th>Oxirgi SMS</th><th>Kimga</th><th className="ong">Holat</th></tr></thead>
            <tbody>
              {sms.xabarlar.slice(0, 5).map((x, i) => (
                <tr key={i}>
                  <td className="soz-mute">{vaqtMatni(x.vaqt)}</td>
                  <td>{x.telefon}</td>
                  <td className="ong">{x.holat === 'yuborildi' ? <Yorliq tur="yashil">yetkazildi</Yorliq>
                    : x.holat === 'xato' ? <Yorliq tur="qizil" title={x.xato}>xato</Yorliq> : <Yorliq tur="ogoh">kutilmoqda</Yorliq>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SPanel>
    ),
    dashbord: () => (
      <SPanel id="dashbord" ikon="ustun" nomi="Dashboard va kunlik hisobot" izoh="Rahbar nimani ko'radi va qachon xabar oladi">
        {almashQator('kunlik_hisobot', 'Rahbarga kunlik hisobot Telegramda',
          s.kunlik_hisobot ? `Kassa, zakazlar, qarz — bir xabarda. Yuborish vaqti: ${vaqt('kunlik_hisobot_vaqti')}.` : "O'chiq: kunlik hisobot yuborilmaydi.")}
        {s.kunlik_hisobot && (
          <SQator nomi="Yuborish vaqti" izoh="Salon yopilishiga yaqin vaqtni qo'ying.">
            <input type="time" className="soz-tanlov" aria-label="Kunlik hisobot yuborish vaqti" value={vaqt('kunlik_hisobot_vaqti')}
              onChange={(e) => e.target.value && set('kunlik_hisobot_vaqti', e.target.value)} />
          </SQator>
        )}
        {almashQator('qoplamagan_royxat', "Uzoq bo'sh turgan liboslar ro'yxati",
          s.qoplamagan_royxat ? `${s.qoplamagan_kun} kundan beri berilmagan va o'zini qoplamagan libos Dashboardda chiqadi.` : "O'chiq: Dashboardda bu ro'yxat chiqmaydi.")}
        {s.qoplamagan_royxat && (
          <SQator nomi="Necha kundan keyin ro'yxatga tushadi">
            <Qadam qiymat={s.qoplamagan_kun} onChange={(v) => set('qoplamagan_kun', v)} nomi="Bo'sh turgan kun" min={1} max={730} qadam={5} birlik="kun" />
          </SQator>
        )}
      </SPanel>
    ),
    qurilmalar: () => (
      <SPanel id="qurilmalar" ikon="qurilma" nomi="Qurilmalar va salon paroli" izoh="Faqat ruxsat berilgan qurilmadan kiriladi">
        <Sahifali royxat={qur} hajm={8} nomi="qurilma">{(qism) => qism.map((q) => (
          <QurilmaQator key={q.id} q={q} fil={faolFilial ? fil : null} onChiqar={() => setChiqarSurov(q)}
            onRuxsat={() => bajar(() => qurilmaTasdiq(q.id), 'Qurilmaga ruxsat berildi.')}
            onFilial={(filial) => bajar(() => qurilmaFilial(q.id, filial), 'Qurilma filiali saqlandi.')} />
        ))}</Sahifali>
        <SQator nomi="Salon paroli" izoh="Yangi qurilmada birinchi kirish uchun — salon logini bilan birga.">
          {parolOchiq ? (
            <span className="soz-parol">
              <input type="password" className="soz-tanlov" aria-label="Yangi salon paroli (kamida 8 belgi)" placeholder="kamida 8 belgi" value={yangiParol}
                autoComplete="new-password" onChange={(e) => setYangiParol(e.target.value)} />
              <button type="button" className="kichik" disabled={yangiParol.length < 8}
                onClick={() => bajar(() => salonParol(yangiParol), "Salon paroli o'zgartirildi.").then((ok) => { if (ok) { setYangiParol(''); setParolOchiq(false) } })}>Saqlash</button>
              <button type="button" className="ikkinchi kichik" onClick={() => { setYangiParol(''); setParolOchiq(false) }}>Bekor</button>
            </span>
          ) : <button type="button" className="ikkinchi kichik" onClick={() => setParolOchiq(true)}>O'zgartirish</button>}
        </SQator>
        <p className="soz-izoh">Yangi qurilmada salon logini kiritilgach, u shu yerda ruxsat kutadi. Telegram ulangan bo'lsa, ruxsatni botdagi tugma yoki qurilma
          ekranidagi havola/QR orqali ham berasiz. Chiqarilgan qurilmadagi ochiq sessiyalar darhol yopiladi.</p>
        {chiqarSurov && (
          <Tasdiq sarlavha={`«${chiqarSurov.nomi}» ${chiqarSurov.tasdiqlangan ? 'chiqarilsinmi' : 'rad etilsinmi'}?`} tugma={chiqarSurov.tasdiqlangan ? 'Ha, chiqarish' : 'Ha, rad etish'}
            matn="Undagi ochiq sessiyalar darhol yopiladi; qayta kirish uchun salon logini va rahbar ruxsati kerak bo'ladi. Agar bu shu qurilma bo'lsa — siz ham tizimdan chiqasiz."
            onYop={() => setChiqarSurov(null)}
            onTasdiq={() => { const q = chiqarSurov; setChiqarSurov(null); bajar(() => qurilmaOchirish(q.id), "Qurilma ro'yxatdan chiqarildi.") }} />
        )}
      </SPanel>
    ),
    yordam: () => (
      <SPanel id="yordam" ikon="yordam" nomi="Texnik yordam ruxsati" izoh="Platforma egasi salon ma'lumotini faqat siz bergan muddatda ko'radi (faqat o'qish)"
        ong={yordam && (yordam.amalda ? <Yorliq tur="ogoh">ochiq</Yorliq> : <Yorliq>Ruxsat yo'q</Yorliq>)}>
        {!yordam ? <p className="soz-izoh">Yuklanmoqda…</p> : yordam.amalda ? (
          <SQator nomi="Ruxsat amalda" izoh={`${vaqtMatni(yordam.tugaydi)} gacha. Har kirish jurnalga yoziladi.`}>
            <button type="button" className="xavfli kichik" onClick={() => bajar(yordamBekor, 'Ruxsat bekor qilindi.')}>Ruxsatni bekor qilish</button>
          </SQator>
        ) : (
          <SQator nomi="Muddatli ruxsat berish" izoh="Har kirish jurnalga yoziladi. Istalgan payt bekor qilasiz.">
            <button type="button" className="ikkinchi kichik" aria-label="2 soatga ruxsat berish" onClick={() => bajar(() => yordamBer(2), '2 soatga ruxsat berildi.')}>2 soat</button>
            <button type="button" className="ikkinchi kichik" aria-label="24 soatga ruxsat berish" onClick={() => bajar(() => yordamBer(24), '24 soatga ruxsat berildi.')}>24 soat</button>
          </SQator>
        )}
      </SPanel>
    ),
    jurnal: () => <Jurnal />,
  }

  // Kanvas: umumiy ko'rinishda har bo'limning joriy qiymati (saqlangan holat bo'yicha — tahrirdagi o'zgarish emas)
  const sa = asl ? JSON.parse(asl) : s
  const faolXodim = xodimlar.filter((x) => x.faol !== false)
  const faolFil = fil.filter((f) => f.faol).length
  const kutQur = qur.filter((q) => !q.tasdiqlangan).length
  const qiymat = {
    bandlik: `${sa.bufer_kun} kun · ${sa.vaqtinchalik_bron_soat} soat · ${sa.qulf_daqiqa} daq`,
    kechikish: sa.kechikish_jarimasi ? `${guruhla(sa.kechikish_kunlik_summa || 0)} / kun` : "o'chiq",
    qaytarish: `${sa.avans_foizi ? `avans ${sa.avans_foizi}%` : "to'liq avans"} · ${(sa.qaytarish_qoidasi || []).length} qoida`,
    shartnoma: `${(sa.shartnoma_bandlari || []).length} band`,
    mavsumiy: sa.mavsumiy_narx ? 'yoqilgan' : "o'chiq",
    promokod: sa.promokodlar_bolimi ? 'yoqilgan' : "o'chiq",
    katalog: !sa.sotuvchi_libos_qoshadi ? 'faqat rahbar' : "rahbar tasdig'i bilan",
    artikul: sa.artikul_avto ? `avtomatik${sa.artikul_prefiks ? ` · ${sa.artikul_prefiks}` : ''}` : "qo'lda",
    xodimlar: `${faolXodim.length} xodim`,
    bonus: sa.sotuvchi_bonusi ? `${sa.bonus_foiz}%` : "o'chiq",
    kassa: sa.kassa_rejimi === 'kassir' ? 'alohida kassir' : "sotuvchi o'zi oladi",
    filiallar: fil.length ? `${faolFil} faol${fil.length - faolFil ? ` · ${fil.length - faolFil} nofaol` : ''}` : "yo'q",
    rekvizitlar: rekAsl ? (JSON.parse(rekAsl).yuridik_nom || JSON.parse(rekAsl).nomi || '') : '',
    dashbord: sa.kunlik_hisobot ? `har kuni ${String(sa.kunlik_hisobot_vaqti).slice(0, 5)}` : "hisobot o'chiq",
    sms: sa.sms_eslatma || sa.sms_kvitansiya ? 'yoqilgan' : "o'chiq",
    qurilmalar: kutQur ? `${kutQur} ruxsat kutmoqda` : `${qur.length} qurilma`,
    yordam: yordam ? (yordam.amalda ? 'ochiq' : 'yopiq') : '',
  }
  const diqqat = new Set([kutQur && 'qurilmalar', faolXodim.some((x) => !x.telegram_ulangan) && 'xodimlar'].filter(Boolean))

  // 'bosh' — «Barcha sozlamalar»: guruhlar kartalar to'rida; aks holda tanlangan bo'lim guruhi (hamma panellari)
  const joriyId = ESKI_BOLIM[bolim] || bolim
  const guruh = bolim === 'bosh' ? null : (SOZLAMA_BOLIMLAR.find((b) => b.id === joriyId)?.guruh || GURUHLAR[0].nomi)
  const topildi = sozlamaQidir(qidiruv)

  return (
    <div className="sozlama-joy">
    {/* Bo'limlar ro'yxati: keng ekranda (≥1200) chap panelda — App joy beradi (foydalanuvchi qarori); 1024–1199 da sahifaning
        o'zida chapda; telefon va planshetda — ☰ menyu */}
    <SozlamaYon>
      <nav className="sozlama-yon" aria-label="Sozlama menyusi">
        <div className="sozlama-guruh">
          <button type="button" className={bolim === 'bosh' ? 'faol' : ''} aria-current={bolim === 'bosh' ? 'page' : undefined}
            onClick={() => onBolim('bosh')}><NavIkona nom="bosh" /><span>Barcha sozlamalar</span></button>
        </div>
        <BolimRoyxati bolim={joriyId} guruh={guruh} onTanla={onBolim} diqqat={diqqat} />
      </nav>
    </SozlamaYon>
    <div className="sozlama-mazmun">
      <div className="sozlama-menu">
        <button type="button" className="sozlama-menu-tugma" aria-expanded={menuOchiq}
          onClick={() => setMenuOchiq(!menuOchiq)}>
          <span className="sozlama-menu-belgi" aria-hidden="true">☰</span>
          <span className="sozlama-menu-nom">{guruh || 'Barcha sozlamalar'}</span>
          <span className="sozlama-menu-chevron" aria-hidden="true">▾</span>
        </button>
        {menuOchiq && (
          <div className="sozlama-menu-rohat">
            <div className="sozlama-guruh">
              <button type="button" className={bolim === 'bosh' ? 'faol' : ''} aria-current={bolim === 'bosh' ? 'page' : undefined}
                onClick={() => { onBolim('bosh'); setMenuOchiq(false) }}><NavIkona nom="bosh" /><span>Barcha sozlamalar</span></button>
            </div>
            <BolimRoyxati bolim={joriyId} guruh={guruh} diqqat={diqqat} onTanla={(id) => { onBolim(id); setMenuOchiq(false) }} />
          </div>
        )}
      </div>
      {/* Qidiruv: «PIN», «SMS», «artikul», «filial»… — 20 ta bo'lim ichida adashmaslik uchun (B-36); kanvas: sarlavha o'ngida */}
      <BoshAmal>
      <div className="r2-sozlama-qidiruv">
        <label className="qidiruv-maydon">
          <NavIkona nom="qidiruv" className="tugma-ikon" />
          <input type="search" className="jadval-qidiruv" aria-label="Sozlamadan qidirish" placeholder="Sozlamani qidirish: jarima, PIN, SMS…"
            value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        </label>
        {qidiruv.trim() && (
          <div className="r2-qidiruv-natija" role="list" aria-label="Topilgan bo'limlar">
            {topildi.length === 0 && <p className="malumot">Topilmadi. Boshqacha yozib ko'ring: masalan, «jarima», «parol».</p>}
            {topildi.map((b) => (
              <button key={b.id} type="button" role="listitem" onClick={() => { onBolim(b.id); setQidiruv(''); setMenuOchiq(false) }}>
                <NavIkona nom={b.ikon} /><span>{b.nomi}</span><small>{b.guruh}</small>
              </button>
            ))}
          </div>
        )}
      </div>
      </BoshAmal>
      {guruh === null
        ? <SozlamaMarkazi onTanla={onBolim} qiymat={qiymat} diqqat={diqqat} />
        : (
          <>
            <nav className="soz-yol" aria-label="Sozlama yo'li">
              <button type="button" className="havola" onClick={() => onBolim('bosh')}>Barcha sozlamalar</button>
              <span aria-hidden="true">/</span><b>{guruh}</b>
            </nav>
            {PANEL_TARTIBI[guruh].map((x) => (Array.isArray(x)
              ? <div key={x.join('-')} className="soz-juft">{x.map((id) => <Fragment key={id}>{panellar[id]()}</Fragment>)}</div>
              : <Fragment key={x}>{panellar[x]()}</Fragment>))}
          </>
        )}
      {/* Pastda yopishib turadi: xabar va (o'zgarish bo'lsa) saqlash paneli — uzun guruh sahifasida ham ko'rinadi */}
      {(xabar.matn || sOzgardi || rekOzgardi) && (
        <div className="soz-past">
          {xabar.matn && <p role="status" className={`soz-xabar ${xabar.turi === 'xato' ? 'xato' : ''}`}>{xabar.matn}</p>}
          {(sOzgardi || rekOzgardi) && (
            <div className="sozlama-saqlash" role="region" aria-label="Saqlanmagan o'zgarishlar">
              <NavIkona nom="soat" className="tugma-ikon" />
              <span>Saqlanmagan o'zgarishlar bor</span>
              <button type="button" className="ikkinchi kichik" onClick={() => { setS(JSON.parse(asl)); if (rekAsl) setRek(JSON.parse(rekAsl)); setBandOchiq(null) }}>Bekor qilish</button>
              <button type="button" className="kichik" onClick={saqlash}>Saqlash</button>
            </div>
          )}
        </div>
      )}
    </div>
    </div>
  )
}

// C-21 (foydalanuvchi qarori): har salon o'zi tanlaydi — qaysi qism «avans» (qoida bo'yicha ushlab qolinishi mumkin),
// qaysi qism «oldindan to'lov» (bekor qilinganda to'liq qaytariladi). null — birinchi to'lov to'liq avans.
const MISOL_JAMI = 3_000_000
function AvansFoizi({ s, set }) {
  const foiz = s.avans_foizi
  const avans = foiz ? (MISOL_JAMI * foiz) / 100 : null
  return (
    <fieldset className="soz-qator soz-avans">
      <legend className="sr-only">Avans qancha</legend>
      <span className="soz-matn">
        <b>Avans miqdori</b>
        <small>
          {foiz == null
            ? "Misol: mijoz 3 000 000 lik zakazga birinchi marta 1 500 000 to'lasa — hammasi avans, bekor qilinganda pastdagi qoida qo'llanadi; keyingi to'lovlar to'liq qaytariladi."
            : `Misol: ${guruhla(MISOL_JAMI)} lik zakazda ${foiz}% → avans ${guruhla(avans)}. Mijoz 1 500 000 to'lagan bo'lsa, bekor qilinganda `
              + (1_500_000 > avans ? `${guruhla(1_500_000 - avans)} to'liq qaytariladi, ${guruhla(avans)} ga pastdagi qoida qo'llanadi.` : "hammasi avans — pastdagi qoida qo'llanadi.")}
        </small>
      </span>
      <span className="soz-ong soz-avans-tanlov">
        <label className="soz-chip">
          <input type="radio" name="avans_foizi" checked={foiz == null} onChange={() => set('avans_foizi', null)} />
          Birinchi to'lov to'liq avans
        </label>
        <label className="soz-chip">
          <input type="radio" name="avans_foizi" checked={foiz != null} onChange={() => set('avans_foizi', foiz ?? 30)} />
          Zakazdan foiz
        </label>
        <Qadam qiymat={foiz ?? 30} disabled={foiz == null} nomi="Avans, zakaz summasidan foiz" min={1} max={100} qadam={5} birlik="%"
          onChange={(v) => set('avans_foizi', v)} />
      </span>
    </fieldset>
  )
}

// Qurilma qatori (kanvas): belgi, nom va holat · oxirgi kirish · filial; ruxsat kutayotgani ajralib turadi.
// Filial — matnda; «Filial» bosilsa tanlov ochiladi (har qatorda doim ochiq tanlov ro'yxatni og'irlashtirardi)
function QurilmaQator({ q, fil, onChiqar, onRuxsat, onFilial }) {
  const [filialOchiq, setFilialOchiq] = useState(false)
  const filialNomi = fil && (fil.find((f) => f.id === q.filial)?.nomi || 'filialsiz')
  return (
    <div className={`soz-qurilma${q.tasdiqlangan ? '' : ' kutadi'}`}>
      <span className="soz-plitka kichik" aria-hidden="true"><NavIkona nom="qurilma" className="tugma-ikon" /></span>
      <span className="soz-matn">
        <b>{q.nomi}{q.tasdiqlangan ? '' : ' — yangi qurilma'}</b>
        <small>{[q.tasdiqlangan ? 'ishonchli' : 'ruxsat kutmoqda', q.oxirgi_kirish && `oxirgi kirish ${vaqtMatni(q.oxirgi_kirish)}`,
          q.modeli, filialNomi].filter(Boolean).join(' · ')}</small>
        {fil && filialOchiq && <QurilmaFiliali q={q} fil={fil} onSaqla={(v) => onFilial(v).then((ok) => ok && setFilialOchiq(false))} />}
      </span>
      <span className="soz-ong">
        {fil && <button type="button" className="havola soz-mute-havola" aria-expanded={filialOchiq} onClick={() => setFilialOchiq(!filialOchiq)}>Filial</button>}
        {q.tasdiqlangan ? <button type="button" className="havola" onClick={onChiqar}>Chiqarish</button> : (
          <>
            <button type="button" className="ikkinchi kichik" onClick={onChiqar}>Rad etish</button>
            <button type="button" className="kichik soz-yashil" onClick={onRuxsat}>Ruxsat berish</button>
          </>
        )}
      </span>
    </div>
  )
}

function QurilmaFiliali({ q, fil, onSaqla }) {
  const [v, setV] = useState(q.filial ? String(q.filial) : '')
  return (
    <span className="soz-qurilma-filial">
      <select className="soz-tanlov" value={v} aria-label="Qurilma filiali" onChange={(e) => setV(e.target.value)}>
        <option value="">Filialga biriktirilmagan</option>
        {fil.filter((f) => f.faol || f.id === q.filial).map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
      </select>
      {v !== (q.filial ? String(q.filial) : '') && (
        <button type="button" className="ikkinchi kichik" onClick={() => onSaqla(v ? Number(v) : null)}>Saqlash</button>
      )}
    </span>
  )
}

// «Barcha sozlamalar» (kanvas SozlamaBolimShisha): 6 guruh — ikki ustunda kartalar, har qator — bo'lim nomi va joriy qiymati
// (tilla), bosilsa bo'lim ochiladi. Qisqa izoh — sichqoncha ostida (title). E'tibor talab qiladigan holatlar (Telegram ulamagan xodim,
// ruxsat kutayotgan qurilma) — qo'ng'iroqchada (foydalanuvchi so'rovi); bu yerda faqat qiymat rangi va chap ro'yxatdagi nuqta.
function SozlamaMarkazi({ onTanla, qiymat, diqqat }) {
  const ustunlar = [GURUHLAR.slice(0, 3), GURUHLAR.slice(3)]
  return (
    <div className="sozlama-umumiy">
      <div className="sozlama-tor ikki-ustun" role="group" aria-label="Sozlama bo'limlari">
        {ustunlar.map((guruhlar, i) => (
          <div key={i} className="sozlama-ustun">
            {guruhlar.map(({ nomi: g, ikon }) => (
              <section key={g} className="blok dash-karta sozlama-guruh-karta" aria-label={g}>
                <div className="dash-karta-bosh"><h3><NavIkona nom={ikon} className="tugma-ikon" />{g}</h3></div>
                <ul className="sozlama-qatorlar">
                  {SOZLAMA_BOLIMLAR.filter((b) => b.guruh === g).map((b) => (
                    <li key={b.id}>
                      <button type="button" title={b.izoh} onClick={() => onTanla(b.id)}>
                        <span className="sozlama-matn"><b>{b.nomi}</b></span>
                        {qiymat[b.id] && <span className={`sozlama-qiymat${diqqat.has(b.id) ? ' diqqat' : ''}`}>{qiymat[b.id]}</span>}
                        <NavIkona nom="ong" className="tugma-ikon sozlama-ong" />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// Chap ro'yxat: ochiq guruhning hamma bo'limlari belgilanadi (guruh sahifasida hammasi ko'rinib turadi); e'tibor kerak bo'lsa — tilla nuqta
function BolimRoyxati({ bolim, guruh, onTanla, diqqat }) {
  return GURUHLAR.map(({ nomi: g }) => (
    <div key={g} className="sozlama-guruh">
      <h4>{g}</h4>
      {SOZLAMA_BOLIMLAR.filter((b) => b.guruh === g).map((b) => (
        <button key={b.id} type="button" className={`${b.id === bolim ? 'faol' : ''}${g === guruh ? ' guruhda' : ''}`.trim()}
          aria-current={b.id === bolim ? 'page' : undefined} onClick={() => onTanla(b.id)}>
          <NavIkona nom={b.ikon} /><span>{b.nomi}</span>
          {diqqat?.has(b.id) && <i className="soz-nuqta" aria-hidden="true" title="e'tibor kerak" />}
        </button>
      ))}
    </div>
  ))
}

function FilialQator({ f, qurilma, onFaol, onSaqla }) {
  const [tahrir, setTahrir] = useState(false)
  return (
    <div className={`tasdiq soz-filial${f.faol ? '' : ' bajarilgan'}`}>
      <div className="soz-qator">
        <span className="soz-matn"><b>{f.nomi}</b>
          <small>{[f.manzil, qurilma ? `${qurilma} qurilma` : ''].filter(Boolean).join(' · ') || 'manzil kiritilmagan'}</small>
        </span>
        <span className="soz-ong">
          <Yorliq tur={f.faol ? 'yashil' : 'yopiq'}>{f.faol ? 'Faol' : 'Nofaol'}</Yorliq>
          <button type="button" className="havola" aria-expanded={tahrir} onClick={() => setTahrir(!tahrir)}>Tahrirlash</button>
        </span>
      </div>
      {tahrir && <FilialTahrir f={f} onFaol={onFaol} onSaqla={(b) => onSaqla(b).then((ok) => ok && setTahrir(false))} />}
    </div>
  )
}

function FilialTahrir({ f, onSaqla, onFaol }) {
  const [nomi, setNomi] = useState(f.nomi)
  const [manzil, setManzil] = useState(f.manzil || '')
  return (
    <div className="stack soz-tahrir">
      <label>Nomi<input value={nomi} maxLength={100} onChange={(e) => setNomi(e.target.value)} /></label>
      <label>Manzil<input value={manzil} maxLength={300} onChange={(e) => setManzil(e.target.value)} /></label>
      <div className="soz-tugmalar">
        <button type="button" className="kichik" disabled={!nomi.trim() || (nomi.trim() === f.nomi && manzil === (f.manzil || ''))}
          onClick={() => onSaqla({ nomi: nomi.trim(), manzil })}>Saqlash</button>
        <button type="button" className="ikkinchi kichik" onClick={onFaol}>{f.faol ? 'Nofaol qilish' : 'Faollashtirish'}</button>
      </div>
    </div>
  )
}

// Xodim qatori (kanvas jadvali): ism va telefon, rol, PIN, Telegram; «···» — tahrirlash menyusi qator ostida ochiladi
function Xodim({ x, men, filiallar, onOzgartir }) {
  const [ochiq, setOchiq] = useState(false)
  const [yangiRol, setYangiRol] = useState(null)
  const [pin, setPin] = useState('')
  const [ism, setIsm] = useState(x.ism)
  const [telefon, setTelefon] = useState(x.telefon || '')
  const rolNomi = ROLLAR.find(([k]) => k === x.rol)?.[1]
  // Filial — faqat salonda filial bo'lsa (biriktirilmagan xodim — barcha filiallarda)
  const filialBor = filiallar.some((f) => f.faol) || x.filial != null
  const filialNomi = filialBor ? (filiallar.find((f) => f.id === x.filial)?.nomi || 'barcha filiallar') : null
  return (
    <div className={`soz-xodim${x.faol ? '' : ' nofaol'}`}>
      <div className="soz-xq">
        <span className="soz-xodim-ism">
          <i className="soz-avatar" aria-hidden="true">{boshHarf(x.ism)}</i>
          <span className="soz-matn"><b className="xodim-ism">{x.ism}</b>
            <small>{[x.telefon, filialNomi, men && 'siz', !x.faol && 'nofaol'].filter(Boolean).join(' · ') || '—'}</small></span>
        </span>
        <span><Yorliq tur={x.rol === 'rahbar' ? 'tilla' : 'yopiq'}>{rolNomi}</Yorliq></span>
        <span className="soz-mute">{x.bloklangan ? <Yorliq tur="qizil">bloklangan</Yorliq> : "o'rnatilgan"}</span>
        <span>{x.telegram_ulangan ? <Yorliq tur="yashil">ulangan</Yorliq> : (
          <button type="button" className="soz-holat ogoh" title="Xodim menyusida «Telegram» → «Kod olish»" onClick={() => setOchiq(true)}>ulanmagan · ulash</button>
        )}</span>
        <button type="button" className="soz-uch-nuqta" aria-label="Xodim menyusi" aria-expanded={ochiq} onClick={() => setOchiq(!ochiq)}>
          <NavIkona nom="koproq" className="tugma-ikon" />
        </button>
      </div>
      {ochiq && (
        <div className="xodim-menyu stack soz-tahrir">
          <XodimTelegram x={x} />
          <label>Ism<input value={ism} maxLength={200} aria-label="Ism" onChange={(e) => setIsm(e.target.value)} /></label>
          <label>Telefon<input value={telefon} maxLength={20} inputMode="tel" aria-label="Telefon" onChange={(e) => setTelefon(e.target.value)} /></label>
          <button className="ikkinchi" disabled={!ism.trim() || (ism.trim() === x.ism && telefon === (x.telefon || ''))}
            onClick={() => onOzgartir({ ism: ism.trim(), telefon }, "Xodim ma'lumoti saqlandi.")}>Ism / telefonni saqlash</button>
          <label>Yangi PIN (4–6 raqam)
            <input type="password" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} />
          </label>
          <button className="ikkinchi" disabled={!/^\d{4,6}$/.test(pin)}
            onClick={() => onOzgartir({ pin }, 'PIN tiklandi.').then((ok) => ok && setPin(''))}>PIN ni tiklash</button>
          <label>Rol
            <select value={x.rol} onChange={(e) => e.target.value !== x.rol && setYangiRol(e.target.value)}>
              {ROLLAR.map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
            </select>
          </label>
          {filialBor && (
            <label>Filial
              <select value={x.filial ?? ''} onChange={(e) => onOzgartir({ filial: e.target.value ? Number(e.target.value) : null }, "Xodim filiali o'zgartirildi.")}>
                <option value="">Barcha filiallar</option>
                {filiallar.filter((f) => f.faol || f.id === x.filial).map((f) => (
                  <option key={f.id} value={f.id}>{f.nomi}{f.faol ? '' : ' (nofaol)'}</option>
                ))}
              </select>
              <small className="soz-izoh">Kirish ekranida shu filial planshetida birinchi chiqadi; boshqa filialda ham kira oladi.</small>
            </label>
          )}
          {yangiRol && (
            <Tasdiq sarlavha={`${x.ism} — ${ROLLAR.find(([k]) => k === yangiRol)[1]}?`} tugma="Ha, rolni o'zgartirish"
              xavfli={yangiRol === 'rahbar'}
              matn={`${x.ism} ${ROLLAR.find(([k]) => k === yangiRol)[1].toLowerCase()} bo'ladi: ${ROL_IZOH[yangiRol]}.`}
              onYop={() => setYangiRol(null)}
              onTasdiq={() => { const rol = yangiRol; setYangiRol(null); onOzgartir({ rol }, "Rol o'zgartirildi.") }} />
          )}
          <button className="ikkinchi" onClick={() => onOzgartir({ faol: !x.faol }, x.faol ? 'Xodim nofaol qilindi.' : 'Xodim faollashtirildi.')}>
            {x.faol ? 'Nofaol qilish' : 'Faollashtirish'}
          </button>
        </div>
      )}
    </div>
  )
}

function XodimTelegram({ x }) {
  const [ulash, setUlash] = useState(null)
  const [ulangan, setUlangan] = useState(x.telegram_ulangan)

  // Boshqa joyda yangilansa (masalan, ro'yxat qayta yuklansa) holatni moslab turadi
  useEffect(() => { if (x.telegram_ulangan) { setUlangan(true); setUlash(null) } }, [x.telegram_ulangan])

  // Kod ko'rsatilganda xodim ulanganini kuzatib turadi (TelegramBlok bilan bir xil usul)
  useEffect(() => {
    if (!ulash || ulangan) return undefined
    const t = setInterval(async () => {
      const roy = await xodimlarBoshqaruv().catch(() => null)
      if (roy?.find((v) => v.id === x.id)?.telegram_ulangan) { setUlangan(true); setUlash(null) }
    }, 3000)
    return () => clearInterval(t)
  }, [ulash, ulangan, x.id])

  return (
    <details className="amal telegram">
      <summary>Telegram · {ulangan ? 'ulangan' : 'ulanmagan'}</summary>
      <div className="stack">
        {ulangan ? (
          <p className="malumot">Bu xodim Telegramga ulangan — yangi bron, eslatma va ogohlantirishlar uning akkauntiga boradi.</p>
        ) : (
          <>
            <p>Telegram nima uchun kerak: bot bu xodimga yangi bron, eslatma va ogohlantirishlarni yuboradi.
              Ulanmasa, xodim bu xabarlarni olmaydi.</p>
            {ulash ? (
              <>
                <p>Telegramda botni oching{ulash.bot ? <> (<b>@{ulash.bot}</b>)</> : ''} va shu xabarni yuboring:</p>
                <p className="kod">/start {ulash.kod}</p>
                {ulash.havola && <a className="tugma-havola" href={ulash.havola} target="_blank" rel="noreferrer">Botni ochish</a>}
                <p className="malumot">Kod 15 daqiqa amal qiladi. Xodim ulangach bu oyna o'zi yangilanadi.</p>
              </>
            ) : (
              <button className="ikkinchi" onClick={async () => setUlash(await xodimTelegramUlash(x.id))}>Kod olish</button>
            )}
          </>
        )}
      </div>
    </details>
  )
}

function XodimForma({ filiallar, onYuborish }) {
  const [f, setF] = useState({ rol: 'sotuvchi' })
  const faollar = filiallar.filter((v) => v.faol)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="stack">
        <label>Ism *<input value={f.ism || ''} onChange={set('ism')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon || ''} placeholder="masalan: +998 90 123 45 67" onChange={set('telefon')} /></label>
        <label>Rol
          <select value={f.rol} onChange={set('rol')}>
            {ROLLAR.map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
          </select>
        </label>
        {faollar.length > 0 && (
          <label>Filial
            <select value={f.filial || ''} onChange={set('filial')}>
              <option value="">Barcha filiallar</option>
              {faollar.map((v) => <option key={v.id} value={v.id}>{v.nomi}</option>)}
            </select>
          </label>
        )}
        <label>PIN (4–6 raqam) *
          <input type="password" inputMode="numeric" maxLength={6} value={f.pin || ''} onChange={set('pin')} />
        </label>
        <button disabled={!f.ism?.trim() || !/^\d{4,6}$/.test(f.pin || '')}
          onClick={() => onYuborish({ ism: f.ism, telefon: f.telefon || '', rol: f.rol, pin: f.pin, filial: f.filial ? Number(f.filial) : null })
            .then((ok) => ok && setF({ rol: 'sotuvchi' }))}>
          Qo'shish
        </button>
        {(!f.ism?.trim() || !/^\d{4,6}$/.test(f.pin || '')) && (
          <p className="malumot r2-sabab">To'ldiring: {[!f.ism?.trim() && 'Ism', !/^\d{4,6}$/.test(f.pin || '') && 'PIN (4–6 raqam)'].filter(Boolean).join(', ')}</p>
        )}
    </div>
  )
}
