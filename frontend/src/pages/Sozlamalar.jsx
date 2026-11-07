import { useCallback, useEffect, useState } from 'react'
import Integratsiyalar from '../components/Integratsiyalar'
import MavsumiyNarx from '../components/MavsumiyNarx'
import TayyorChegirmalar from '../components/TayyorChegirmalar'
import Promokodlar from './Promokodlar'
import Jurnal from '../components/Jurnal'
import NavIkona from '../components/NavIkona'
import Info from '../components/Info'
import Oyna from '../components/Oyna'
import Tasdiq from '../components/Tasdiq'
import { ESKI_BOLIM, GURUHLAR, SOZLAMA_BOLIMLAR, sozlamaQidir } from './sozlamaBolimlari'
import {
  smsJurnali, filialOzgartir, filialQosh, filiallar, qurilmaFilial, qurilmaOchirish, qurilmaTasdiq, qurilmalar, salonParol, salonRekvizit, salonRekvizitSaqla, yordamBekor, yordamBer,
  yordamRuxsati, sozlamalar, sozlamaSaqla, xatoMatni, guruhla, xodimOzgartir, xodimQosh, xodimTelegramUlash, xodimlarBoshqaruv,
} from '../api'
import SummaInput from '../components/SummaInput'

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

// Sozlama bo'limlarining statik ro'yxati (sozlamaBolimlari.js) — chap paneldagi nav (App.jsx) ham, mazmun ham shu ro'yxatga mos.
// Pastdagi `bolimlar` massividagi id lar shu ro'yxatdagi bilan bir xil bo'lishi shart.

// 4.16: admin panel. Keng ekranda bo'limlar chap paneldagi Sozlama menyusida (App, akkordeon); telefonda — sahifa tepasidagi ochiladigan menyu.
export default function Sozlamalar({ menId, bolim, onBolim }) {
  const [s, setS] = useState(null)
  const [xodimlar, setXodimlar] = useState([])
  const [rek, setRek] = useState(null)
  const [rekAsl, setRekAsl] = useState(null)
  const [qur, setQur] = useState([])
  const [yordam, setYordam] = useState(null)
  const [yangiParol, setYangiParol] = useState('')
  const [fil, setFil] = useState([])
  const [sms, setSms] = useState(null)
  useEffect(() => { smsJurnali().then(setSms).catch(() => {}) }, [])
  const [yangiFilial, setYangiFilial] = useState({ nomi: '', manzil: '' })
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  // Serverdagi holat — o'zgarish bor-yo'qligini bilish uchun (saqlash paneli faqat o'zgarishda chiqadi)
  const [asl, setAsl] = useState(null)
  const [xodimOyna, setXodimOyna] = useState(false)
  // Tor ekranda bo'lim almashish menyusi (keng ekranda bo'limlar chapda doim ko'rinadi).
  const [menuOchiq, setMenuOchiq] = useState(false)
  const [qidiruv, setQidiruv] = useState('')
  const [chiqarSurov, setChiqarSurov] = useState(null)  // ro'yxatdan chiqariladigan qurilma

  const yukla = useCallback(async () => {
    const [a, b, c, d, e, f] = await Promise.all([sozlamalar(), xodimlarBoshqaruv(), salonRekvizit(), qurilmalar(), yordamRuxsati(), filiallar(true)])
    setS(a); setAsl(JSON.stringify(a)); setXodimlar(b); setRek(c); setRekAsl(JSON.stringify(c)); setQur(d); setYordam(e); setFil(f.filiallar)
  }, [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }

  if (!s) return <p className="malumot">{xabar.matn || 'Yuklanmoqda…'}</p>
  const set = (k, v) => setS({ ...s, [k]: v })
  const son = (k) => (e) => set(k, e.target.value === '' ? '' : Number(e.target.value))
  const qoida = (i, j) => (e) => set('qaytarish_qoidasi',
    s.qaytarish_qoidasi.map((q, n) => (n === i ? q.map((v, m) => (m === j ? Number(e.target.value) : v)) : q)))

  // B-37: har bo'limda bitta usul — maydon va almashtirgichlar (rekvizitlar ham) pastdagi umumiy panel orqali saqlanadi;
  // ro'yxat elementlari (qoida, filial, xodim, qurilma) — har biri o'z tugmasi bilan
  const sOzgardi = JSON.stringify(s) !== asl
  const rekOzgardi = rek !== null && JSON.stringify(rek) !== rekAsl
  const saqlash = () => (rekOzgardi && !String(rek.nomi || '').trim()
    ? setXabar({ turi: 'xato', matn: "Salon nomi bo'sh bo'lmasligi kerak (Rekvizitlar)." })
    : bajar(async () => {
    if (sOzgardi) await sozlamaSaqla({ ...faqatSozlama(s), shartnoma_bandlari: (s.shartnoma_bandlari || []).filter((b) => b.sarlavha.trim() || b.matn.trim()) })
    // faqat o'zgargan maydonlar: bo'sh qolgan boshqa maydon («yuridik nom» va h.k.) saqlashni to'xtatmasin
    if (rekOzgardi) {
      const a = JSON.parse(rekAsl)
      await salonRekvizitSaqla(Object.fromEntries(Object.entries(rek).filter(([k, v]) => v !== a[k])))
    }
  }, rekOzgardi && !sOzgardi ? 'Rekvizitlar saqlandi.' : 'Sozlamalar saqlandi.'))

  const bolimlar = [
    {
      id: 'bandlik', nomi: 'Bron va zalog',
      render: () => (
        <>
        <section className="blok stack">
          <h3>Bron va bandlik</h3>
          <label>Tozalash uchun bufer kun (kategoriya yoki libosda alohida belgilanmagan bo'lsa)
            <input type="number" min="0" max="30" value={s.bufer_kun} onChange={son('bufer_kun')} />
          </label>
          <label>Avanssiz bron necha soat saqlanadi
            <input type="number" min="1" max="168" value={s.vaqtinchalik_bron_soat} onChange={son('vaqtinchalik_bron_soat')} />
          </label>
          <label>Tanlangan libos necha daqiqa qulflanadi (boshqa sotuvchidan yashiriladi)
            <input type="number" min="1" max="120" value={s.qulf_daqiqa} onChange={son('qulf_daqiqa')} />
          </label>
        </section>
        <section className="blok stack">
          <h3>Zalog turlari</h3>
          <p className="malumot">Libos berishda qaysi garovlarni qabul qilasiz.</p>
          {[['zalog_pul', 'Pul'], ['zalog_hujjat', 'Hujjat'], ['zalog_tillo', 'Tillo buyum']].map(([k, nom]) => (
            <label key={k} className="qator">
              <input type="checkbox" checked={s[k]} onChange={(e) => set(k, e.target.checked)} /> {nom}
            </label>
          ))}
        </section>
        </>
      ),
    },
    {
      id: 'kechikish', nomi: 'Kechikish jarimasi',
      render: () => (
        <section className="blok stack">
          <h3>Kechikish jarimasi</h3>
          <label className="qator">
            <input type="checkbox" checked={s.kechikish_jarimasi} onChange={(e) => set('kechikish_jarimasi', e.target.checked)} />
            Yoqilgan (qaytarishda avtomatik hisoblanadi)
          </label>
          {s.kechikish_jarimasi && (
            <label>Kunlik summa, so'm
              <SummaInput value={s.kechikish_kunlik_summa} onChange={son('kechikish_kunlik_summa')} />
            </label>
          )}
          <label>Qaytmagan libos eslatmasi vaqti
            <input type="time" value={String(s.qaytarish_tekshiruv_vaqti).slice(0, 5)} onChange={(e) => e.target.value && set('qaytarish_tekshiruv_vaqti', e.target.value)} />
          </label>
          <p className="malumot">Qaytarish kuni kelgan, lekin «Qaytarildi» deb qabul qilinmagan libos haqida shu vaqtdan keyin sotuvchi va
            rahbarga Telegramda eslatma boradi (har kuni bir marta, libos qabul qilinguncha). Salon yopilishidan oldingi vaqtni qo'ying.</p>
        </section>
      ),
    },
    {
      id: 'qaytarish', nomi: 'Avans qaytarish',
      render: () => (
        <section className="blok stack">
          <h3>Bekor qilishda avans qaytarish</h3>
          <label>Qoida nimaga qo'llanadi
            <select className="r2-tor-select" value={s.qaytarish_asosi} onChange={(e) => set('qaytarish_asosi', e.target.value)}>
              <option value="avans">Faqat avansga</option>
              <option value="tolangan">Hamma to'langan summaga</option>
            </select>
          </label>
          {s.qaytarish_asosi === 'avans' && ('avans_foizi' in s ? <AvansFoizi s={s} set={set} /> : (
            <p className="malumot">Avansdan keyin oldindan to'langan qoldiq to'liq qaytariladi.</p>
          ))}
          {/* Qoida — 2 ustunli kichik jadval (avval bitta qator telefonda uchga sinib, sahifani surardi) */}
          <table className="hisobot r2-qoida">
            <thead><tr><th>Olib ketishgacha qolgan kun, kamida</th><th className="ong">Qaytariladi, %</th></tr></thead>
            <tbody>
              {s.qaytarish_qoidasi.map(([kun, foiz], i) => (
                <tr key={i}>
                  <td><input type="number" min="0" value={kun} disabled={i === s.qaytarish_qoidasi.length - 1} onChange={qoida(i, 0)}
                    aria-label={`${i + 1}-qoida: qolgan kun, kamida`} /></td>
                  <td className="ong"><input type="number" min="0" max="100" value={foiz} onChange={qoida(i, 1)}
                    aria-label={`${i + 1}-qoida: qaytariladigan foiz`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="malumot">Olib ketishgacha qolgan kunga qarab {s.qaytarish_asosi === 'tolangan' ? "to'langan summaning" : 'avansning'} shu
            qismi qaytariladi; qolgani salonda qoladi. Misol: avans 1 mln, qoldiq 4 mln to'langan, qoida 50% —{' '}
            {s.qaytarish_asosi === 'tolangan' ? '2,5 mln' : '4,5 mln'} qaytariladi.</p>
        </section>
      ),
    },
    {
      id: 'katalog', nomi: "Libos qo'shish va manekin",
      render: () => (
        <section className="blok stack">
          <h3>Libos qo'shish va manekin</h3>
          <label className="qator">
            <input type="checkbox" checked={s.libos_tasdigi} onChange={(e) => set('libos_tasdigi', e.target.checked)} />
            Sotuvchi qo'shgan libos va aksessuarni rahbar tasdiqlaydi
          </label>
          {!s.libos_tasdigi && <p className="malumot">O'chirilgan: sotuvchi libosi darhol katalogga chiqadi, tannarxni keyin kiritasiz.</p>}
          <label className="qator">
            <input type="checkbox" checked={s.sotuvchi_libos_qoshadi} onChange={(e) => set('sotuvchi_libos_qoshadi', e.target.checked)} />
            Sotuvchi libos va aksessuar qo'sha oladi (o'chirilsa — faqat rahbar)
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.manekin} onChange={(e) => set('manekin', e.target.checked)} />
            Raqamli manekin (libos rasmini fonsiz qilib manekinda ko'rsatish)
          </label>
        </section>
      ),
    },
    {
      id: 'artikul', nomi: 'Libos artikuli',
      render: () => {
        const xona = s.artikul_xona || 4
        const namuna = (n) => `${s.artikul_prefiks || ''}${String(n).padStart(xona, '0')}`
        const bosh = Number(s.artikul_boshlanish) || 0
        return (
          <section className="blok stack">
            <h3>Libos artikuli</h3>
            {/* «i» matn yonida: label htmlFor bilan inputga bog'langan (ichidagi tugmaga emas) */}
            <label htmlFor="artikul-prefiks">
              <span>Prefiks (ixtiyoriy)
                <Info nom="Prefiks">Har artikul boshidagi bir xil qism, masalan «L-» yoki «OQ-». Avtomatik raqamlash o'chiq bo'lsa ham,
                  libos qo'shishda Artikul maydoni shu prefiks bilan boshlanadi — faqat raqamini yozasiz.</Info>
              </span>
              <input id="artikul-prefiks" maxLength={10} placeholder="L-" value={s.artikul_prefiks} onChange={(e) => set('artikul_prefiks', e.target.value.replace(/\s/g, ''))} />
            </label>
            <label className="qator">
              <input type="checkbox" checked={s.artikul_avto} onChange={(e) => set('artikul_avto', e.target.checked)} />
              <span>Raqam avtomatik qo'yilsin
                <Info nom="Avtomatik raqam">Libos qo'shishda Artikul bo'sh qoldirilsa, tizim keyingi raqamni o'zi beradi. Qo'lda yozilgan
                  artikul ham hisobga olinadi: oxirgisi {namuna(57)} bo'lsa, keyingisi {namuna(58)}. Ikki xodim bir vaqtda qo'shsa ham raqam takrorlanmaydi.</Info>
              </span>
            </label>
            {s.artikul_avto && (
              <div className="qator keng">
                <label>Sanoq nechidan boshlansin
                  <input type="number" min="0" max="99999999" value={s.artikul_boshlanish} onChange={son('artikul_boshlanish')} />
                </label>
                <label>Raqam necha xonali
                  <select value={xona} onChange={(e) => set('artikul_xona', Number(e.target.value))}>
                    {[1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} — {'0'.repeat(n - 1)}1</option>)}
                  </select>
                </label>
              </div>
            )}
            <p className="malumot">
              {s.artikul_avto
                ? <>Namuna: <b>{namuna(bosh)}</b>, <b>{namuna(bosh + 1)}</b>, <b>{namuna(bosh + 2)}</b>… Agar salonda shu prefiksli kattaroq raqam bo'lsa, undan keyingisi beriladi.</>
                : "Avtomatik raqam o'chiq: artikulni har safar o'zingiz yozasiz."}
            </p>
          </section>
        )
      },
    },
    {
      id: 'dashbord', nomi: 'Dashboard va hisobot',
      render: () => (
        <section className="blok stack">
          <h3>Dashboard va kunlik hisobot</h3>
          <label className="qator">
            <input type="checkbox" checked={s.qoplamagan_royxat} onChange={(e) => set('qoplamagan_royxat', e.target.checked)} />
            Qoplamagan va uzoq bo'sh turgan liboslar ro'yxati
          </label>
          {s.qoplamagan_royxat && (
            <label>Necha kundan beri berilmagan libos ro'yxatga tushadi
              <input type="number" min="1" max="730" value={s.qoplamagan_kun} onChange={son('qoplamagan_kun')} />
            </label>
          )}
          <label className="qator">
            <input type="checkbox" checked={s.kunlik_hisobot} onChange={(e) => set('kunlik_hisobot', e.target.checked)} />
            Rahbarga Telegram orqali kunlik hisobot
          </label>
          {s.kunlik_hisobot && (
            <label>Yuborish vaqti
              <input type="time" value={String(s.kunlik_hisobot_vaqti).slice(0, 5)} onChange={(e) => e.target.value && set('kunlik_hisobot_vaqti', e.target.value)} />
            </label>
          )}
        </section>
      ),
    },
    {
      id: 'sms', nomi: 'SMS eslatma',
      render: () => (
        <section className="blok stack">
          <h3>Mijozga SMS eslatma</h3>
          <label className="qator">
            <input type="checkbox" checked={s.sms_eslatma} onChange={(e) => set('sms_eslatma', e.target.checked)} />
            Ertaga olib ketish va qaytarish haqida mijozga SMS
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.sms_kvitansiya} onChange={(e) => set('sms_kvitansiya', e.target.checked)} />
            Har to'lovdan keyin mijozga SMS kvitansiya
          </label>
          <p className="malumot">Avans, qoldiq, jarima yoki zalog qabul qilinishi bilan mijozga boradi: «zakaz #123 uchun 2 000 000 so'm qabul
            qilindi (naqd). To'langan: 2 000 000 / 10 000 000». Xodim kamroq yoki boshqa usul bilan yozsa, mijoz buni darhol ko'radi.
            Har SMS pullik (Eskiz tarifi); matnni Eskiz kabinetida shablon sifatida tasdiqlatish kerak.</p>
          {sms && !sms.sozlangan && (
            <p className="ogohlantirish">Eskiz.uz hisobi kiritilmagan (Integratsiyalar → SMS): SMS lar hozircha yuborilmaydi, faqat jurnalga yoziladi.</p>
          )}
          {sms && sms.xabarlar.length > 0 && (
            <details className="amal">
              <summary>Oxirgi SMS lar ({sms.xabarlar.length})</summary>
              {sms.xabarlar.slice(0, 20).map((x, i) => (
                <p key={i} className="qator-matn">
                  {vaqtMatni(x.vaqt)} · {x.telefon} · {x.holat === 'yuborildi' ? 'yuborildi' : x.holat === 'xato' ? `xato: ${x.xato}` : 'kutilmoqda'}
                </p>
              ))}
            </details>
          )}
          <p className="malumot">Sotuvchi eslatmalari o'z o'rnida qoladi; SMS — qo'shimcha kanal. Har zakazga har turdagi SMS bir marta yuboriladi.</p>
        </section>
      ),
    },
    {
      id: 'shartnoma', nomi: 'Shartnoma bandlari',
      render: () => (
        <section className="blok stack">
          <h3>Shartnoma: qo'shimcha bandlar</h3>
          <p className="malumot">
            Ijara muddati, to'lov, zalog, jarima va avans qaytarish bandlari sozlamalardan avtomatik yoziladi. Bu yerga salonning o'z
            shartlarini qo'shasiz — ular shartnomada avtomatik bandlardan keyin chiqadi.
          </p>
          {(s.shartnoma_bandlari || []).map((b, i) => (
            <div key={i} className="tasdiq">
              <label>Sarlavha
                <input value={b.sarlavha} maxLength={100}
                  onChange={(e) => set('shartnoma_bandlari', s.shartnoma_bandlari.map((x, n) => (n === i ? { ...x, sarlavha: e.target.value } : x)))} />
              </label>
              <label>Matn
                <textarea rows={3} value={b.matn} maxLength={2000}
                  onChange={(e) => set('shartnoma_bandlari', s.shartnoma_bandlari.map((x, n) => (n === i ? { ...x, matn: e.target.value } : x)))} />
              </label>
              <button type="button" className="ikkinchi kichik" onClick={() => set('shartnoma_bandlari', s.shartnoma_bandlari.filter((_, n) => n !== i))}>
                Bandni olib tashlash
              </button>
            </div>
          ))}
          {(s.shartnoma_bandlari || []).length < 15 && (
            <button type="button" className="ikkinchi" onClick={() => set('shartnoma_bandlari', [...(s.shartnoma_bandlari || []), { sarlavha: '', matn: '' }])}>
              Band qo'shish
            </button>
          )}
        </section>
      ),
    },
    {
      id: 'mavsumiy', nomi: 'Mavsumiy narx',
      render: () => (
        <section className="blok stack">
          <h3>Mavsumiy narx</h3>
          <label className="qator">
            <input type="checkbox" checked={s.mavsumiy_narx} onChange={(e) => set('mavsumiy_narx', e.target.checked)} />
            Yoqilgan (ustama zakaz narxiga avtomatik qo'shiladi)
          </label>
          {s.mavsumiy_narx
            ? <p className="malumot">Yoqish yoki o'chirish — pastdagi «Saqlash» bilan. Har bir qoida o'z tugmalari bilan saqlanadi.</p>
            : <p className="malumot">O'chirilgan: qoidalar saqlanadi, lekin narxga ta'sir qilmaydi.</p>}
          <MavsumiyNarx />
        </section>
      ),
    },
    {
      id: 'bonus', nomi: 'Sotuvchi bonusi',
      render: () => (
        <section className="blok stack">
          <h3>Sotuvchi bonusi</h3>
          <label className="qator">
            <input type="checkbox" checked={s.sotuvchi_bonusi} onChange={(e) => set('sotuvchi_bonusi', e.target.checked)} />
            Yoqilgan (qaytarib olingan zakazlar summasidan foiz)
          </label>
          {s.sotuvchi_bonusi && (
            <>
              <label>Bonus, zakazlar summasidan %
                <input type="number" min="0" max="100" step="0.5" value={s.bonus_foiz} onChange={son('bonus_foiz')} />
              </label>
              <p className="malumot">Bonus foydadan avtomatik ayiriladi — xarajat sifatida qayta kiritmang. Har bir sotuvchi summasi: Hisobot → «Sotuvchi bonusi».</p>
            </>
          )}
        </section>
      ),
    },
    {
      id: 'kassa', nomi: 'Kassa',
      render: () => (
        <section className="blok stack">
          <h3>Kim pul qabul qiladi</h3>
          <label className="qator">
            <input type="radio" name="kassa_rejimi" checked={s.kassa_rejimi === 'sotuvchi'} onChange={() => set('kassa_rejimi', 'sotuvchi')} />
            Sotuvchining o'zi kassir
          </label>
          <p className="malumot">Har sotuvchi o'z mijozidan pul oladi va o'z qo'lidagi naqdga javob beradi (har biriga alohida quti yoki hamyon).
            Ketayotganda pulini smenada qolgan xodimga yoki rahbarga topshiradi — qabul qiluvchi Telegramda tasdiqlaydi.
            Kamomad faqat topshirgan xodimga yoziladi.</p>
          <label className="qator">
            <input type="radio" name="kassa_rejimi" checked={s.kassa_rejimi === 'kassir'} onChange={() => set('kassa_rejimi', 'kassir')} />
            Alohida kassir
          </label>
          <p className="malumot">Sotuvchilar faqat zakaz oladi; pulni kassir (yoki rahbar) qabul qiladi — xuddi restoranda ofitsiant buyurtma
            olib, hisobni kassir yopgandek. Kassada sotuvchining zakazi «To'lov kutayotganlar» ro'yxatida chiqadi.
            Har sotuvchining zakazlaridan qancha pul kirgani Hisobot → «Xodimlar nazorati» da ko'rinadi.
            Xodimlar bo'limida kamida bitta xodimga «Kassir» rolini bering.</p>
          <p className="malumot">Rejimni o'zgartirishdan oldin ochiq smenani yoping. Pastdagi «Saqlash» bosilgach kuchga kiradi.</p>
          <h3>Naqdsiz pul nazorati</h3>
          <label className="qator">
            <input type="checkbox" checked={s.otkazma_tasdigi} onChange={(e) => set('otkazma_tasdigi', e.target.checked)} />
            O'tkazmani rahbar tasdiqlaydi
          </label>
          <p className="malumot">O'tkazma bilan to'lov olinganda rahbarga Telegramda «Hisobingizga tushdimi?» — «Keldi / Kelmadi».
            «Kelmadi» bosilsa to'lov hisobdan chiqadi va zakaz qoldig'i qayta chiqadi. O'chirilsa o'tkazma tasdiqsiz hisobga olinadi.</p>
          <label className="qator">
            <input type="checkbox" checked={s.terminal_sverkasi} onChange={(e) => set('terminal_sverkasi', e.target.checked)} />
            Smena yopishda terminal hisobotini solishtirish
          </label>
          <p className="malumot">Smenada terminal orqali to'lov bo'lsa, yopishda terminal chiqarib bergan kunlik hisobot summasi kiritiladi va
            tizim bilan solishtiriladi; farq bo'lsa rahbarga xabar. O'chirilsa smena solishtirmasdan yopiladi.</p>
          <p className="malumot">To'lovdan keyin mijozga SMS kvitansiya — «SMS eslatma» bo'limida.</p>
        </section>
      ),
    },
    {
      id: 'promokod', nomi: 'Promokodlar',
      render: () => (
        <section className="blok stack">
          <h3>Promokodlar</h3>
          <label className="qator">
            <input type="checkbox" checked={s.promokodlar_bolimi} onChange={(e) => set('promokodlar_bolimi', e.target.checked)} />
            Promokodlar bo'limi yoqilgan
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.promokod_tasdiqsiz} onChange={(e) => set('promokod_tasdiqsiz', e.target.checked)} />
            Sotuvchi promokodni rahbar tasdig'isiz qo'llaydi
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.promokod_chegirma_birga} onChange={(e) => set('promokod_chegirma_birga', e.target.checked)} />
            Promokod va qo'shimcha chegirmani birga qo'llash mumkin
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.salonchi_kodlari} onChange={(e) => set('salonchi_kodlari', e.target.checked)} />
            Salonchi kodi zakazni o'sha salonchiga bog'laydi
          </label>
        </section>
      ),
      // Qoidalar va kodlar bir joyda: bo'lim o'chirilgan bo'lsa kodlar ro'yxati ko'rinmaydi
      keyin: () => s.promokodlar_bolimi && <Promokodlar />,
    },
    {
      id: 'chegirmalar', nomi: 'Tayyor chegirmalar', saqlashsiz: true, // o'z formalari bilan saqlanadi
      render: () => <TayyorChegirmalar />,
    },
    { id: 'jurnal', nomi: 'Jurnal', saqlashsiz: true, render: () => <Jurnal /> },
    {
      id: 'integratsiyalar', nomi: 'Integratsiyalar', saqlashsiz: true,
      render: () => <Integratsiyalar />,
    },
    {
      id: 'rekvizitlar', nomi: 'Rekvizitlar',
      render: () => !rek ? <p className="malumot">Yuklanmoqda…</p> : (
        <section className="blok stack">
          <h3>Salon va shartnoma rekvizitlari</h3>
          {[['nomi', 'Salon nomi *'], ['yuridik_nom', 'Yuridik nom'], ['stir', 'STIR (9 raqam)'], ['manzil', 'Manzil'], ['telefon', 'Telefon']].map(([k, nom]) => (
            <label key={k}>{nom}<input value={rek[k] || ''} onChange={(e) => setRek({ ...rek, [k]: e.target.value })} /></label>
          ))}
          <p className="malumot">Shartnoma va hujjatlarda shu ma'lumotlar chiqadi. O'zgartirgach — pastdagi «Saqlash».</p>
        </section>
      ),
    },
    {
      id: 'filiallar', nomi: 'Filiallar',
      render: () => (
        <section className="blok stack">
          <h3>Filiallar</h3>
          {fil.length === 0 && <p className="malumot">Filial yo'q — salon bitta joyda ishlaydi.</p>}
          {fil.map((f) => (
            <div key={f.id} className={`tasdiq ${f.faol ? '' : 'bajarilgan'}`}>
              <span><b>{f.nomi}</b>{f.manzil ? ` · ${f.manzil}` : ''}{f.faol ? '' : ' · nofaol'}</span>
              <button className="ikkinchi kichik" onClick={() => bajar(() => filialOzgartir(f.id, { faol: !f.faol }), f.faol ? 'Filial nofaol qilindi.' : 'Filial faollashtirildi.')}>
                {f.faol ? 'Nofaol qilish' : 'Faollashtirish'}
              </button>
              <FilialTahrir key={`${f.nomi}-${f.manzil}`} f={f} onSaqla={(b) => bajar(() => filialOzgartir(f.id, b), 'Filial saqlandi.')} />
            </div>
          ))}
          <div className="stack">
            <h4 className="r2-kichik-sarlavha">Yangi filial</h4>
            <div className="libos-narxlar">
              <label>Filial nomi *<input placeholder="masalan: Chilonzor" value={yangiFilial.nomi} maxLength={100} onChange={(e) => setYangiFilial({ ...yangiFilial, nomi: e.target.value })} /></label>
              <label>Manzil<input value={yangiFilial.manzil} maxLength={300} onChange={(e) => setYangiFilial({ ...yangiFilial, manzil: e.target.value })} /></label>
            </div>
            <button className="ikkinchi" disabled={!yangiFilial.nomi.trim()}
              onClick={() => bajar(() => filialQosh(yangiFilial), "Filial qo'shildi.").then((ok) => ok && setYangiFilial({ nomi: '', manzil: '' }))}>Qo'shish</button>
          </div>
          <p className="malumot">
            Qurilmani (planshetni) filialga biriktirsangiz, undan ochilgan zakaz va qo'shilgan libos shu filialga yoziladi.
            Filiallar soni tarif bilan cheklangan.
          </p>
          {fil.some((f) => f.faol) && (
            <>
              <label className="qator">
                <input type="checkbox" checked={s.filial_kassasi} onChange={(e) => set('filial_kassasi', e.target.checked)} />
                Har filialda alohida kassa (smena)
              </label>
              <p className="malumot">
                Yoqilsa, har filial qurilmasi o'z smenasini ochadi va to'lov sotuvchi ishlayotgan kassaga yoziladi. O'chirilgan bo'lsa
                salonda bitta umumiy kassa. Pastdagi «Saqlash» bosilgach kuchga kiradi; ochiq smenalarni avval yoping.
              </p>
            </>
          )}
        </section>
      ),
    },
    {
      id: 'qurilmalar', nomi: 'Qurilmalar va parol', saqlashsiz: true,
      render: () => (
        <section className="blok stack">
          <h3>Qurilmalar</h3>
          {qur.map((q) => (
            <div key={q.id} className="tasdiq">
              <span>
                <b>{q.nomi}</b> · {q.tasdiqlangan ? 'ishonchli' : <span className="qizil">ruxsat kutmoqda</span>}
                {q.oxirgi_kirish ? ` · oxirgi kirish ${vaqtMatni(q.oxirgi_kirish)}` : ''}
                <br /><small className="malumot r2-model"><NavIkona nom="qurilma" className="tugma-ikon" />{q.modeli || "Model noma'lum — qurilmadan keyingi kirishda aniqlanadi"}</small>
              </span>
              {fil.some((f) => f.faol) && (
                <QurilmaFiliali key={`${q.id}-${q.filial}`} q={q} fil={fil}
                  onSaqla={(filial) => bajar(() => qurilmaFilial(q.id, filial), 'Qurilma filiali saqlandi.')} />
              )}
              <div className="qator">
                {!q.tasdiqlangan && <button onClick={() => bajar(() => qurilmaTasdiq(q.id), 'Qurilmaga ruxsat berildi.')}>Ruxsat berish</button>}
                <button className="ikkinchi" onClick={() => setChiqarSurov(q)}>Chiqarish</button>
              </div>
            </div>
          ))}
          {chiqarSurov && (
            <Tasdiq sarlavha={`«${chiqarSurov.nomi}» chiqarilsinmi?`} tugma="Ha, chiqarish"
              matn="Undagi ochiq sessiyalar darhol yopiladi; qayta kirish uchun salon logini va rahbar ruxsati kerak bo'ladi. Agar bu shu qurilma bo'lsa — siz ham tizimdan chiqasiz."
              onYop={() => setChiqarSurov(null)}
              onTasdiq={() => { const q = chiqarSurov; setChiqarSurov(null); bajar(() => qurilmaOchirish(q.id), "Qurilma ro'yxatdan chiqarildi.") }} />
          )}
          <p className="malumot">Yangi qurilmada salon logini kiritilgach, u shu yerda ruxsat kutadi. Telegram ulagan bo'lsangiz, ruxsatni botdagi tugma yoki qurilma ekranidagi havola/QR orqali ham berasiz. Chiqarilgan qurilmadagi ochiq sessiyalar darhol yopiladi.</p>
          <h4 className="r2-kichik-sarlavha">Salon paroli</h4>
          <div className="qator r2-parol">
            <label>Yangi salon paroli (kamida 8 belgi)<input type="password" value={yangiParol} autoComplete="new-password" onChange={(e) => setYangiParol(e.target.value)} /></label>
            <button className="ikkinchi" disabled={yangiParol.length < 8}
              onClick={() => bajar(() => salonParol(yangiParol), "Salon paroli o'zgartirildi.").then((ok) => ok && setYangiParol(''))}>O'zgartirish</button>
          </div>
        </section>
      ),
    },
    {
      id: 'yordam', nomi: 'Texnik yordam', saqlashsiz: true,
      render: () => !yordam ? <p className="malumot">Yuklanmoqda…</p> : (
        <section className="blok stack">
          <h3>Texnik yordam ruxsati</h3>
          <p className="malumot">
            Platforma egasi salon zakazlari va hisobotini faqat siz bergan muddatli ruxsat bilan ko'ra oladi (faqat o'qish).
            Har bir kirish jurnalga yoziladi.
          </p>
          {yordam.amalda ? (
            <>
              <p className="ogohlantirish">Ruxsat amalda: {vaqtMatni(yordam.tugaydi)} gacha.</p>
              <button className="xavfli" onClick={() => bajar(yordamBekor, 'Ruxsat bekor qilindi.')}>Ruxsatni bekor qilish</button>
            </>
          ) : (
            <div className="qator">
              <button className="ikkinchi" onClick={() => bajar(() => yordamBer(2), '2 soatga ruxsat berildi.')}>2 soatga ruxsat</button>
              <button className="ikkinchi" onClick={() => bajar(() => yordamBer(24), '24 soatga ruxsat berildi.')}>24 soatga ruxsat</button>
            </div>
          )}
        </section>
      ),
    },
    {
      id: 'xodimlar', nomi: 'Xodimlar', saqlashsiz: true,
      render: () => (
        <section className="blok stack">
          <div className="blok-sarlavha">
            <h3>Xodimlar ({xodimlar.length})</h3>
            <button type="button" className="kichik" onClick={() => setXodimOyna(true)}><NavIkona nom="qosh" className="tugma-ikon" />Xodim qo'shish</button>
          </div>
          {xodimlar.map((x) => (
            <Xodim key={x.id} x={x} men={x.id === menId}
              onOzgartir={(b, ok) => bajar(() => xodimOzgartir(x.id, b), ok)} />
          ))}
          {xodimOyna && (
            <Oyna sarlavha="Xodim qo'shish" onYop={() => setXodimOyna(false)}>
              <XodimForma onYuborish={async (b) => { const ok = await bajar(() => xodimQosh(b), "Xodim qo'shildi."); if (ok) setXodimOyna(false); return ok }} />
            </Oyna>
          )}
        </section>
      ),
    },
  ]

  // 'bosh' — «Barcha sozlamalar»: guruhlar kartalar to'rida (maket uslubi); aks holda tanlangan bo'lim
  const joriy = bolim === 'bosh'
    ? { id: 'bosh', nomi: 'Barcha sozlamalar', render: () => <SozlamaMarkazi onTanla={onBolim} /> }
    : bolimlar.find((b) => b.id === (ESKI_BOLIM[bolim] || bolim)) || bolimlar[0]
  const topildi = sozlamaQidir(qidiruv)

  return (
    <div className="sozlama-joy">
    <div className="sozlama-mazmun">
      <div className="sozlama-menu">
        <button type="button" className="sozlama-menu-tugma" aria-expanded={menuOchiq}
          onClick={() => setMenuOchiq(!menuOchiq)}>
          <span className="sozlama-menu-belgi" aria-hidden="true">☰</span>
          <span className="sozlama-menu-nom">{joriy.nomi}</span>
          <span className="sozlama-menu-chevron" aria-hidden="true">▾</span>
        </button>
        {menuOchiq && (
          <div className="sozlama-menu-rohat">
            <div className="sozlama-guruh">
              <button type="button" className={bolim === 'bosh' ? 'faol' : ''} aria-current={bolim === 'bosh' ? 'page' : undefined}
                onClick={() => { onBolim('bosh'); setMenuOchiq(false) }}><NavIkona nom="katalog" /><span>Barcha sozlamalar</span></button>
            </div>
            <BolimRoyxati bolim={bolim} onTanla={(id) => { onBolim(id); setMenuOchiq(false) }} />
          </div>
        )}
      </div>
      {/* Qidiruv: «PIN», «SMS», «artikul», «filial»… — 20 ta bo'lim ichida adashmaslik uchun (B-36) */}
      <div className="r2-sozlama-qidiruv">
        <label className="qidiruv-maydon">
          <NavIkona nom="qidiruv" className="tugma-ikon" />
          <input type="search" className="jadval-qidiruv" aria-label="Sozlamadan qidirish" placeholder="Qidirish: PIN, SMS, artikul, filial…"
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
      {joriy.render()}
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot sozlama-xabar'}>{xabar.matn}</p>}
      {/* Saqlash paneli faqat o'zgarish bo'lganda (professional sozlama sahifalaridagidek); bo'lim almashsa ham turadi */}
      {(sOzgardi || rekOzgardi) && (
        <div className="sozlama-saqlash" role="region" aria-label="Saqlanmagan o'zgarishlar">
          <span>Saqlanmagan o'zgarishlar bor</span>
          <button type="button" className="ikkinchi kichik" onClick={() => { setS(JSON.parse(asl)); if (rekAsl) setRek(JSON.parse(rekAsl)) }}>Bekor qilish</button>
          <button type="button" className="kichik" onClick={saqlash}>Saqlash</button>
        </div>
      )}
      {joriy.keyin?.()}
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
    <fieldset className="guruh r3z-avans">
      <legend>Avans qancha</legend>
      <label className="qator">
        <input type="radio" name="avans_foizi" checked={foiz == null} onChange={() => set('avans_foizi', null)} />
        Birinchi to'lov to'liq avans
      </label>
      <label className="qator r3z-foiz">
        <input type="radio" name="avans_foizi" checked={foiz != null} onChange={() => set('avans_foizi', foiz ?? 30)} />
        <span>Avans — zakaz summasining</span>
        <input type="number" min="1" max="100" value={foiz ?? ''} disabled={foiz == null} aria-label="Avans, zakaz summasidan foiz"
          onChange={(e) => set('avans_foizi', e.target.value === '' ? 30 : Math.min(100, Math.max(1, Number(e.target.value))))} />
        <span>%, ortig'i to'liq qaytariladi</span>
      </label>
      <p className="malumot">
        {foiz == null
          ? "Misol: mijoz 3 000 000 lik zakazga birinchi marta 1 500 000 to'lasa — hammasi avans, bekor qilinganda yuqoridagi qoida qo'llanadi; keyingi to'lovlar to'liq qaytariladi."
          : `Misol: ${guruhla(MISOL_JAMI)} lik zakazda ${foiz}% → avans ${guruhla(avans)}. Mijoz 1 500 000 to'lagan bo'lsa, bekor qilinganda `
            + (1_500_000 > avans ? `${guruhla(1_500_000 - avans)} to'liq qaytariladi, ${guruhla(avans)} ga yuqoridagi qoida qo'llanadi.` : "hammasi avans — yuqoridagi qoida qo'llanadi.")}
      </p>
    </fieldset>
  )
}

function QurilmaFiliali({ q, fil, onSaqla }) {
  const [v, setV] = useState(q.filial ? String(q.filial) : '')
  return (
    <div className="qator r2z-qurilma-filial">
      <select value={v} aria-label="Qurilma filiali" onChange={(e) => setV(e.target.value)}>
        <option value="">Filialga biriktirilmagan</option>
        {fil.filter((f) => f.faol || f.id === q.filial).map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
      </select>
      <button type="button" className="ikkinchi kichik" disabled={v === (q.filial ? String(q.filial) : '')}
        onClick={() => onSaqla(v ? Number(v) : null)}>Saqlash</button>
    </div>
  )
}

// «Barcha sozlamalar»: 6 guruh — kartalar to'rida; har qator — bo'limga o'tish (belgi, nom, qisqa izoh)
function SozlamaMarkazi({ onTanla }) {
  return (
    <div className="sozlama-tor" role="group" aria-label="Sozlama bo'limlari">
      {GURUHLAR.map(({ nomi: g, ikon }) => (
        <section key={g} className="blok dash-karta sozlama-guruh-karta" aria-label={g}>
          <div className="dash-karta-bosh"><h3><NavIkona nom={ikon} className="tugma-ikon" />{g}</h3></div>
          <ul className="sozlama-qatorlar">
            {SOZLAMA_BOLIMLAR.filter((b) => b.guruh === g).map((b) => (
              <li key={b.id}>
                <button type="button" onClick={() => onTanla(b.id)}>
                  <span className="sozlama-belgi" aria-hidden="true"><NavIkona nom={b.ikon} /></span>
                  <span className="sozlama-matn"><b>{b.nomi}</b><small>{b.izoh}</small></span>
                  <NavIkona nom="ong" className="tugma-ikon sozlama-ong" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

function BolimRoyxati({ bolim, onTanla }) {
  return GURUHLAR.map(({ nomi: g }) => (
    <div key={g} className="sozlama-guruh">
      <h4>{g}</h4>
      {SOZLAMA_BOLIMLAR.filter((b) => b.guruh === g).map((b) => (
        <button key={b.id} type="button" className={b.id === bolim ? 'faol' : ''} aria-current={b.id === bolim ? 'page' : undefined}
          onClick={() => onTanla(b.id)}><NavIkona nom={b.ikon} /><span>{b.nomi}</span></button>
      ))}
    </div>
  ))
}

function FilialTahrir({ f, onSaqla }) {
  const [nomi, setNomi] = useState(f.nomi)
  const [manzil, setManzil] = useState(f.manzil || '')
  return (
    <details className="amal">
      <summary>Tahrirlash</summary>
      <div className="stack">
        <label>Nomi<input value={nomi} maxLength={100} onChange={(e) => setNomi(e.target.value)} /></label>
        <label>Manzil<input value={manzil} maxLength={300} onChange={(e) => setManzil(e.target.value)} /></label>
        <button className="ikkinchi" disabled={!nomi.trim() || (nomi.trim() === f.nomi && manzil === (f.manzil || ''))}
          onClick={() => onSaqla({ nomi: nomi.trim(), manzil })}>Saqlash</button>
      </div>
    </details>
  )
}

function Xodim({ x, men, onOzgartir }) {
  const [ochiq, setOchiq] = useState(false)
  const [yangiRol, setYangiRol] = useState(null)
  const [pin, setPin] = useState('')
  const [ism, setIsm] = useState(x.ism)
  const [telefon, setTelefon] = useState(x.telefon || '')
  return (
    <div className={`xodim ${x.faol ? '' : 'nofaol'}`}>
      <div className="xodim-sarlavha">
        <span className="xodim-chip">
          <i aria-hidden="true">{(x.ism || '?').trim().charAt(0).toUpperCase()}</i>
          <span><b className="xodim-ism">{x.ism}{men ? ' (siz)' : ''}</b>{x.telefon && <small>{x.telefon}</small>}</span>
        </span>
        <span className="xodim-belgilar">
          <span className={`holat ${x.rol === 'rahbar' ? 'berildi' : 'qaytarildi'}`}>{ROLLAR.find(([k]) => k === x.rol)?.[1]}</span>
          {!x.faol && <span className="holat qarz">Nofaol</span>}
          {x.bloklangan && <span className="holat vaqtinchalik">PIN bloklangan</span>}
        </span>
        <button className="xodim-menu" aria-label="Xodim menyusi" aria-expanded={ochiq} onClick={() => setOchiq(!ochiq)}>⋮</button>
      </div>
      {ochiq && (
        <div className="xodim-menyu stack">
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

function XodimForma({ onYuborish }) {
  const [f, setF] = useState({ rol: 'sotuvchi' })
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
        <label>PIN (4–6 raqam) *
          <input type="password" inputMode="numeric" maxLength={6} value={f.pin || ''} onChange={set('pin')} />
        </label>
        <button disabled={!f.ism?.trim() || !/^\d{4,6}$/.test(f.pin || '')}
          onClick={() => onYuborish({ ism: f.ism, telefon: f.telefon || '', rol: f.rol, pin: f.pin }).then((ok) => ok && setF({ rol: 'sotuvchi' }))}>
          Qo'shish
        </button>
        {(!f.ism?.trim() || !/^\d{4,6}$/.test(f.pin || '')) && (
          <p className="malumot r2-sabab">To'ldiring: {[!f.ism?.trim() && 'Ism', !/^\d{4,6}$/.test(f.pin || '') && 'PIN (4–6 raqam)'].filter(Boolean).join(', ')}</p>
        )}
    </div>
  )
}
