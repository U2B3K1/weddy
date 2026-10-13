import { useCallback, useEffect, useState } from 'react'
import Integratsiyalar from '../components/Integratsiyalar'
import MavsumiyNarx from '../components/MavsumiyNarx'
import TayyorChegirmalar from '../components/TayyorChegirmalar'
import {
  smsJurnali, filialOzgartir, filialQosh, filiallar, qurilmaFilial, qurilmaOchirish, qurilmaTasdiq, qurilmalar, salonParol, salonRekvizit, salonRekvizitSaqla, yordamBekor, yordamBer,
  yordamRuxsati, sozlamalar, sozlamaSaqla, xatoMatni, xodimOzgartir, xodimQosh, xodimTelegramUlash, xodimlarBoshqaruv,
} from '../api'

// GET /sozlamalar/ javobidagi faqat o'qiladigan belgilar (integratsiyalardan) saqlashga yuborilmaydi
const faqatSozlama = ({ fiskal_eslatma: _f, fiskal_izoh: _i, tolov_havolasi: _t, ...qolgan }) => qolgan

// Sozlama bo'limlarining statik ro'yxati — chap paneldagi nav (App.jsx) ham, mazmun ham shu ro'yxatga mos.
// Pastdagi `bolimlar` massivi bilan bir xil tartibda va nomlarda bo'lishi shart.
export const SOZLAMA_BOLIMLAR = [
  { id: 'bandlik', nomi: 'Bandlik' },
  { id: 'zalog', nomi: 'Zalog turlari' },
  { id: 'kechikish', nomi: 'Kechikish jarimasi' },
  { id: 'qaytarish', nomi: 'Avans qaytarish' },
  { id: 'katalog', nomi: 'Katalog' },
  { id: 'dashbord', nomi: 'Dashbord va hisobot' },
  { id: 'sms', nomi: 'SMS eslatma' },
  { id: 'shartnoma', nomi: 'Shartnoma bandlari' },
  { id: 'primerka', nomi: 'Primerka va baho' },
  { id: 'mavsumiy', nomi: 'Mavsumiy narx' },
  { id: 'bonus', nomi: 'Sotuvchi bonusi' },
  { id: 'promokod', nomi: 'Promokodlar' },
  { id: 'chegirmalar', nomi: 'Tayyor chegirmalar' },
  { id: 'integratsiyalar', nomi: 'Integratsiyalar' },
  { id: 'rekvizitlar', nomi: 'Rekvizitlar' },
  { id: 'filiallar', nomi: 'Filiallar' },
  { id: 'qurilmalar', nomi: 'Qurilmalar' },
  { id: 'yordam', nomi: 'Texnik yordam' },
  { id: 'xodimlar', nomi: 'Xodimlar' },
]

// 4.16: admin panel. Bo'limlar chap paneldagi umumiy navda chiqadi (App.jsx); bu yerda faqat mazmun.
export default function Sozlamalar({ menId, bolim, onBolim }) {
  const [s, setS] = useState(null)
  const [xodimlar, setXodimlar] = useState([])
  const [rek, setRek] = useState(null)
  const [qur, setQur] = useState([])
  const [yordam, setYordam] = useState(null)
  const [yangiParol, setYangiParol] = useState('')
  const [fil, setFil] = useState([])
  const [sms, setSms] = useState(null)
  useEffect(() => { smsJurnali().then(setSms).catch(() => {}) }, [])
  const [yangiFilial, setYangiFilial] = useState({ nomi: '', manzil: '' })
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  // Tor ekranda bo'lim almashish menyusi (keng ekranda chap paneldagi sidebar ishlaydi).
  const [menuOchiq, setMenuOchiq] = useState(false)

  const yukla = useCallback(async () => {
    const [a, b, c, d, e, f] = await Promise.all([sozlamalar(), xodimlarBoshqaruv(), salonRekvizit(), qurilmalar(), yordamRuxsati(), filiallar(true)])
    setS(a); setXodimlar(b); setRek(c); setQur(d); setYordam(e); setFil(f.filiallar)
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

  const saqlash = () => bajar(() => sozlamaSaqla({ ...faqatSozlama(s), shartnoma_bandlari: (s.shartnoma_bandlari || []).filter((b) => b.sarlavha.trim() || b.matn.trim()) }), 'Sozlamalar saqlandi.')

  const bolimlar = [
    {
      id: 'bandlik', nomi: 'Bandlik',
      render: () => (
        <section className="blok stack">
          <h3>Bandlik</h3>
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
      ),
    },
    {
      id: 'zalog', nomi: 'Zalog turlari',
      render: () => (
        <section className="blok stack">
          <h3>Zalog turlari</h3>
          {[['zalog_pul', 'Pul'], ['zalog_hujjat', 'Hujjat'], ['zalog_tillo', 'Tillo buyum']].map(([k, nom]) => (
            <label key={k} className="qator">
              <input type="checkbox" checked={s[k]} onChange={(e) => set(k, e.target.checked)} /> {nom}
            </label>
          ))}
        </section>
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
              <input type="number" min="0" value={s.kechikish_kunlik_summa} onChange={son('kechikish_kunlik_summa')} />
            </label>
          )}
        </section>
      ),
    },
    {
      id: 'qaytarish', nomi: 'Avans qaytarish',
      render: () => (
        <section className="blok stack">
          <h3>Bekor qilishda avans qaytarish</h3>
          {s.qaytarish_qoidasi.map(([kun, foiz], i) => (
            <div key={i} className="qator">
              <input type="number" min="0" value={kun} disabled={i === s.qaytarish_qoidasi.length - 1} onChange={qoida(i, 0)} />
              <span>kun va undan ko'p qolsa —</span>
              <input type="number" min="0" max="100" value={foiz} onChange={qoida(i, 1)} />
              <span>%</span>
            </div>
          ))}
          <p className="malumot">Olib ketishgacha qolgan kunga qarab avansning shu qismi qaytariladi; qolgani «boshqa daromad».</p>
        </section>
      ),
    },
    {
      id: 'katalog', nomi: 'Katalog',
      render: () => (
        <section className="blok stack">
          <h3>Katalog</h3>
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
      id: 'dashbord', nomi: 'Dashbord va hisobot',
      render: () => (
        <section className="blok stack">
          <h3>Dashbord va kunlik hisobot</h3>
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
          {sms && !sms.sozlangan && (
            <p className="ogohlantirish">Eskiz.uz hisobi kiritilmagan (Integratsiyalar → SMS): SMS lar hozircha yuborilmaydi, faqat jurnalga yoziladi.</p>
          )}
          {sms && sms.xabarlar.length > 0 && (
            <details className="amal">
              <summary>Oxirgi SMS lar ({sms.xabarlar.length})</summary>
              {sms.xabarlar.slice(0, 20).map((x, i) => (
                <p key={i} className="qator-matn">
                  {String(x.vaqt).slice(0, 10)} · {x.telefon} · {x.holat === 'yuborildi' ? 'yuborildi' : x.holat === 'xato' ? `xato: ${x.xato}` : 'kutilmoqda'}
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
      id: 'primerka', nomi: 'Primerka va baho',
      render: () => (
        <section className="blok stack">
          <h3>Primerka va mijoz bahosi</h3>
          <label className="qator">
            <input type="checkbox" checked={s.primerka} onChange={(e) => set('primerka', e.target.checked)} />
            Primerka (zakazga sana va vaqt, moslash xizmati narxi bilan)
          </label>
          <label className="qator">
            <input type="checkbox" checked={s.mijoz_bahosi} onChange={(e) => set('mijoz_bahosi', e.target.checked)} />
            Qaytarishda mijoz bahosi (1–5) yoziladi
          </label>
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
            ? <p className="malumot">Yoqish yoki o'chirish «Sozlamalarni saqlash» bosilgach kuchga kiradi; qoidalar darhol saqlanadi.</p>
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
            Yoqilgan (tushumdan foiz)
          </label>
          {s.sotuvchi_bonusi && (
            <>
              <label>Bonus, tushumdan %
                <input type="number" min="0" max="100" step="0.5" value={s.bonus_foiz} onChange={son('bonus_foiz')} />
              </label>
              <p className="malumot">Bonus foyda va zarar hisobotida operatsion xarajatga avtomatik qo'shiladi — xarajat sifatida qayta kiritmang. Har bir sotuvchi summasi «Hisobot» bo'limida.</p>
            </>
          )}
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
          <p className="malumot">Kodlarni «Mijozlar» → «Promokodlar» bo'limida yaratasiz.</p>
        </section>
      ),
    },
    {
      id: 'chegirmalar', nomi: 'Tayyor chegirmalar',
      render: () => <TayyorChegirmalar />,
    },
    {
      id: 'integratsiyalar', nomi: 'Integratsiyalar',
      render: () => <Integratsiyalar />,
    },
    {
      id: 'rekvizitlar', nomi: 'Rekvizitlar',
      render: () => !rek ? <p className="malumot">Yuklanmoqda…</p> : (
        <section className="blok stack">
          <h3>Salon va shartnoma rekvizitlari</h3>
          {[['nomi', 'Salon nomi'], ['yuridik_nom', 'Yuridik nom'], ['stir', 'STIR (9 raqam)'], ['manzil', 'Manzil'], ['telefon', 'Telefon']].map(([k, nom]) => (
            <label key={k}>{nom}<input value={rek[k] || ''} onChange={(e) => setRek({ ...rek, [k]: e.target.value })} /></label>
          ))}
          <button className="ikkinchi" onClick={() => bajar(() => salonRekvizitSaqla(rek), 'Rekvizitlar saqlandi.')}>Rekvizitlarni saqlash</button>
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
            <input placeholder="Filial nomi" value={yangiFilial.nomi} maxLength={100} onChange={(e) => setYangiFilial({ ...yangiFilial, nomi: e.target.value })} />
            <input placeholder="Manzil" value={yangiFilial.manzil} maxLength={300} onChange={(e) => setYangiFilial({ ...yangiFilial, manzil: e.target.value })} />
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
                salonda bitta umumiy kassa. «Sozlamalarni saqlash» bosilgach kuchga kiradi; ochiq smenalarni avval yoping.
              </p>
            </>
          )}
        </section>
      ),
    },
    {
      id: 'qurilmalar', nomi: 'Qurilmalar',
      render: () => (
        <section className="blok stack">
          <h3>Qurilmalar</h3>
          {qur.map((q) => (
            <div key={q.id} className="tasdiq">
              <span>
                <b>{q.nomi}</b> · {q.tasdiqlangan ? 'ishonchli' : <span className="qizil">ruxsat kutmoqda</span>}
                {q.oxirgi_kirish ? ` · oxirgi kirish ${new Date(q.oxirgi_kirish).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })}` : ''}
              </span>
              {fil.some((f) => f.faol) && (
                <select value={q.filial || ''} aria-label="Qurilma filiali"
                  onChange={(e) => bajar(() => qurilmaFilial(q.id, e.target.value ? Number(e.target.value) : null), 'Qurilma filiali saqlandi.')}>
                  <option value="">Filialga biriktirilmagan</option>
                  {fil.filter((f) => f.faol || f.id === q.filial).map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
                </select>
              )}
              <div className="qator">
                {!q.tasdiqlangan && <button onClick={() => bajar(() => qurilmaTasdiq(q.id), 'Qurilmaga ruxsat berildi.')}>Ruxsat berish</button>}
                <button className="ikkinchi" onClick={() => bajar(() => qurilmaOchirish(q.id), "Qurilma ro'yxatdan chiqarildi.")}>Chiqarish</button>
              </div>
            </div>
          ))}
          <p className="malumot">Yangi qurilmada salon logini kiritilgach, u shu yerda ruxsat kutadi. Chiqarilgan qurilmadagi ochiq sessiyalar darhol yopiladi.</p>
          <div className="qator">
            <input type="password" placeholder="Yangi salon paroli (kamida 8 belgi)" value={yangiParol} onChange={(e) => setYangiParol(e.target.value)} />
            <button className="ikkinchi" disabled={yangiParol.length < 8}
              onClick={() => bajar(() => salonParol(yangiParol), "Salon paroli o'zgartirildi.").then((ok) => ok && setYangiParol(''))}>O'zgartirish</button>
          </div>
        </section>
      ),
    },
    {
      id: 'yordam', nomi: 'Texnik yordam',
      render: () => !yordam ? <p className="malumot">Yuklanmoqda…</p> : (
        <section className="blok stack">
          <h3>Texnik yordam ruxsati</h3>
          <p className="malumot">
            Platforma egasi salon zakazlari va hisobotini faqat siz bergan muddatli ruxsat bilan ko'ra oladi (faqat o'qish).
            Har bir kirish jurnalga yoziladi.
          </p>
          {yordam.amalda ? (
            <>
              <p className="ogohlantirish">Ruxsat amalda: {new Date(yordam.tugaydi).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })} gacha.</p>
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
      id: 'xodimlar', nomi: 'Xodimlar',
      render: () => (
        <section className="blok stack">
          <h3>Xodimlar</h3>
          {xodimlar.map((x) => (
            <Xodim key={x.id} x={x} men={x.id === menId}
              onOzgartir={(b, ok) => bajar(() => xodimOzgartir(x.id, b), ok)} />
          ))}
          <XodimForma onYuborish={(b) => bajar(() => xodimQosh(b), "Xodim qo'shildi.")} />
        </section>
      ),
    },
  ]

  const joriy = bolimlar.find((b) => b.id === bolim) || bolimlar[0]

  return (
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
            {SOZLAMA_BOLIMLAR.map((b) => (
              <button key={b.id} type="button" className={b.id === bolim ? 'faol' : ''}
                onClick={() => { onBolim(b.id); setMenuOchiq(false) }}>
                {b.nomi}
              </button>
            ))}
          </div>
        )}
      </div>
      {joriy.render()}
      <div className="sozlama-saqlash">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <button onClick={saqlash}>Sozlamalarni saqlash</button>
      </div>
    </div>
  )
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
  const [pin, setPin] = useState('')
  const [ism, setIsm] = useState(x.ism)
  const [telefon, setTelefon] = useState(x.telefon || '')
  return (
    <div className={`xodim ${x.faol ? '' : 'nofaol'}`}>
      <div className="xodim-sarlavha">
        <span className="xodim-ism">
          {x.ism} · {x.rol === 'rahbar' ? 'rahbar' : 'sotuvchi'}{men ? ' (siz)' : ''}
          {!x.faol && ' · nofaol'}{x.bloklangan && ' · PIN bloklangan'}
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
          <button className="ikkinchi" onClick={() => onOzgartir({ rol: x.rol === 'rahbar' ? 'sotuvchi' : 'rahbar' }, "Rol o'zgartirildi.")}>
            {x.rol === 'rahbar' ? 'Sotuvchi qilish' : 'Rahbar qilish'}
          </button>
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
    <details className="amal">
      <summary>Xodim qo'shish</summary>
      <div className="stack">
        <label>Ism<input value={f.ism || ''} onChange={set('ism')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon || ''} onChange={set('telefon')} /></label>
        <select value={f.rol} onChange={set('rol')}>
          <option value="sotuvchi">Sotuvchi</option><option value="rahbar">Rahbar</option>
        </select>
        <label>PIN (4–6 raqam)
          <input type="password" inputMode="numeric" maxLength={6} value={f.pin || ''} onChange={set('pin')} />
        </label>
        <button disabled={!f.ism?.trim() || !/^\d{4,6}$/.test(f.pin || '')}
          onClick={() => onYuborish({ ism: f.ism, telefon: f.telefon || '', rol: f.rol, pin: f.pin }).then((ok) => ok && setF({ rol: 'sotuvchi' }))}>
          Qo'shish
        </button>
      </div>
    </details>
  )
}
