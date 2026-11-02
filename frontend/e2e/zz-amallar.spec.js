// Brauzerda hali sinalmagan tahrirlash/qo'shish/o'chirish amallari (PROGRESS: 33–41-qismlar).
// Fayl nomi «zz-» bilan — eng oxirida ishlaydi: filial qo'shadi, sozlamalarni o'zgartiradi, boshqa testlarga xalaqit bermasin.
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])
// Zakaz kartasi: asosiy amaldan tashqari hammasi «Boshqa amallar» ostida yig'ilgan
const boshqaAmallar = async (page) => {
  const d = page.locator('details.boshqa-amallar')
  if (!(await d.evaluate((e) => e.open))) await d.locator('summary.havola-tugma').click()
}
const bolim = async (page, nom) => {
  const asosiy = nav(page).getByRole('button', { name: 'Asosiy', exact: true })
  if (await asosiy.isVisible()) await asosiy.click()  // Sozlama menyusidan chiqish
  await nav(page).getByRole('button', { name: nom, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

async function sozlama(page, guruh, nom) {
  const asosiy = nav(page).getByRole('button', { name: 'Sozlama', exact: true })
  if (await asosiy.isVisible()) await asosiy.click()
  const g = nav(page).getByRole('button', { name: guruh })
  if (await g.getAttribute('aria-expanded') !== 'true') await g.click()
  await nav(page).getByRole('button', { name: nom, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

test('sozlama: filial, mavsumiy narx, tayyor chegirma, SMS shabloni', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')

  await test.step('filial: qo\'shish, tahrirlash, nofaol/faol', async () => {
    await sozlama(page, 'Salon', 'Filiallar')
    await page.getByPlaceholder('Filial nomi').fill('Chilonzor')
    await page.getByPlaceholder('Manzil').fill('Bunyodkor 1')
    await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Filial qo'shildi.")).toBeVisible()
    const qator = page.locator('.tasdiq', { hasText: 'Chilonzor' })
    await expect(qator).toContainText('Bunyodkor 1')
    await qator.getByText('Tahrirlash').click()
    await qator.getByLabel('Nomi').fill('Chilonzor filiali')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Filial saqlandi.')).toBeVisible()
    const yangi = page.locator('.tasdiq', { hasText: 'Chilonzor filiali' })
    await yangi.getByRole('button', { name: 'Nofaol qilish' }).click()
    await expect(yangi).toContainText('nofaol')
    await yangi.getByRole('button', { name: 'Faollashtirish' }).click()
    await expect(yangi).not.toContainText('nofaol')
  })

  await test.step('mavsumiy narx: qoida qo\'shish, tahrirlash, o\'chirish, olib tashlash', async () => {
    await sozlama(page, 'Narx va chegirma', 'Mavsumiy narx')
    const yoqilgan = page.getByLabel(/^Yoqilgan/)
    if (!(await yoqilgan.isChecked())) await yoqilgan.check()
    await page.getByText("Qoida qo'shish").click()
    await page.getByLabel(/^Nomi \(masalan/).fill('Dam olish kunlari')
    await page.getByLabel('Ustama, %').last().fill('10')
    await page.getByLabel('Sh', { exact: true }).check()
    await page.getByLabel('Ya', { exact: true }).check()
    await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Qoida qo'shildi.")).toBeVisible()
    const qoida = page.locator('.tasdiq', { hasText: 'Dam olish kunlari' })
    await expect(qoida).toContainText('+10% · Sh, Ya')
    await qoida.getByText('Tahrirlash').click()
    await qoida.getByLabel('Ustama, %').fill('15')
    await qoida.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Qoida saqlandi.')).toBeVisible()
    await expect(qoida).toContainText('+15%')
    await qoida.getByRole('button', { name: "O'chirish" }).click()
    await expect(qoida).toContainText("o'chirilgan")
    await qoida.getByRole('button', { name: 'Olib tashlash' }).click()
    await expect(page.getByText('Qoida olib tashlandi.')).toBeVisible()
    await expect(qoida).toHaveCount(0)
  })

  await test.step('tayyor chegirma: qo\'shish, summaga o\'tkazish, nofaol', async () => {
    await sozlama(page, 'Narx va chegirma', 'Tayyor chegirmalar')
    await page.getByPlaceholder('Nomi (masalan, Doimiy mijoz)').fill('Doimiy mijoz')
    await page.locator('.blok > .stack').getByLabel('Qiymat').fill('10')
    await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Tayyor chegirma qo'shildi.")).toBeVisible()
    const qator = page.locator('.tasdiq', { hasText: 'Doimiy mijoz' })
    await expect(qator).toContainText('Doimiy mijoz · 10%')
    await qator.getByLabel('Chegirma turi').selectOption('summa')
    await qator.getByLabel('Qiymat').fill('150000')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Chegirma saqlandi.')).toBeVisible()
    await expect(qator).toContainText("150 000 so'm")
    await qator.getByRole('button', { name: 'Nofaol qilish' }).click()
    await expect(qator).toContainText('nofaol')
    await qator.getByRole('button', { name: 'Faollashtirish' }).click()
  })

  await test.step('integratsiyalar: SMS yuboruvchi nomi va shablon', async () => {
    await sozlama(page, "Ko'rinish va xabarlar", 'Integratsiyalar')
    await page.getByText(/^SMS \(Eskiz\.uz\)/).click()
    await page.getByLabel(/^Yuboruvchi nomi/).fill('LIBOSA')
    await page.getByLabel('«Ertaga olib ketish» shabloni').fill('{salon}: ertaga {sana} libosni olib ketasiz.')
    await page.locator('details', { hasText: 'Eskiz email' }).getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Saqlandi.', { exact: true })).toBeVisible()
    await sozlama(page, 'Salon', 'Filiallar')
    await sozlama(page, "Ko'rinish va xabarlar", 'Integratsiyalar')  // qayta ochilganda serverdan o'qiladi
    await page.getByText(/^SMS \(Eskiz\.uz\)/).click()
    await expect(page.getByLabel(/^Yuboruvchi nomi/)).toHaveValue('LIBOSA')
  })
  expect(xatolar).toEqual([])
})

test("zakaz kartasi: salonchi, libos almashtirish, summada chegirma va uning tasdig'i", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')

  await test.step("salonchi qo'shish va tahrirlash", async () => {
    await bolim(page, 'Mijozlar')
    await page.getByRole('tab', { name: 'Salonchilar' }).click()
    await page.getByText("Salonchi qo'shish", { exact: true }).click()
    await page.getByLabel('Ism').fill('Gulnora')
    await page.getByLabel('Salon nomi').fill('Gul salon')
    await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Salonchi qo'shildi.")).toBeVisible()
    const karta = page.locator('.blok', { hasText: 'Gulnora' }).last()
    await karta.getByText('Tahrirlash').click()
    await karta.getByLabel('Telefon').fill('+998901234567')
    await karta.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Salonchi saqlandi.')).toBeVisible()
    await expect(karta).toContainText('+998901234567')
  })

  const bosh = (await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${iso(100)}&gacha=${iso(101)}`)).filter((l) => !l.band && !l.qulflangan)
  expect(bosh.length, 'shu sanalarga kamida ikki bo\'sh libos').toBeGreaterThanOrEqual(2)
  const [birinchi, ikkinchi] = bosh
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770011', fio: 'Amal Sinov', dan: iso(100), gacha: iso(101),
    liboslar: [birinchi.id] })
  expect(z.raqam, JSON.stringify(z)).toBeTruthy()

  await test.step('zakaz kartasi: salonchi belgilash', async () => {
    await bolim(page, 'Zakazlar')
    await page.locator('.zakaz-jadval tbody tr', { hasText: 'Amal Sinov' }).click()
    await boshqaAmallar(page)
    await page.getByText('Salonchi', { exact: true }).click()
    await page.getByLabel('Salonchi', { exact: true }).selectOption({ label: 'Gulnora · Gul salon' })
    await page.locator('details', { hasText: 'Salonchisiz' }).getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Salonchi belgilandi.')).toBeVisible()
    await expect(page.getByText('Salonchi: Gulnora')).toBeVisible()
  })

  await test.step('libosni almashtirish', async () => {
    await boshqaAmallar(page)
    await page.getByText('Libosni almashtirish', { exact: true }).click()
    const forma = page.locator('summary', { hasText: /^Libosni almashtirish$/ }).locator('..')  // tashqi «Boshqa amallar» emas
    const tanlov = forma.getByLabel('Yangi libos')
    await tanlov.selectOption(String(ikkinchi.id))
    await forma.getByLabel('Sabab').fill('Mijoz boshqasini tanladi')
    await forma.getByRole('button', { name: 'Almashtirish' }).click()
    await expect(page.getByText('Libos almashtirildi.')).toBeVisible()
    await expect(page.locator('.karta-asosiy')).toContainText(ikkinchi.nomi)
  })

  await test.step("summada chegirma so'rash → dashboardda tasdiqlash", async () => {
    await boshqaAmallar(page)
    await page.getByText('Chegirma', { exact: true }).click()
    await page.getByRole('button', { name: 'Summada' }).click()
    await page.getByLabel("Boshqa chegirma, so'm").fill('100000')
    await expect(page.getByText("Chegirma: 100 000 so'm")).toBeVisible()
    await page.getByRole('button', { name: "Rahbardan so'rash" }).click()
    await expect(page.getByText("Rahbar tasdig'iga yuborildi.")).toBeVisible()
    await bolim(page, 'Dashboard')
    const sorov = page.locator('.tasdiq-qator', { hasText: `#${z.raqam}` })
    await expect(sorov).toContainText("chegirma 100 000 so'm")
    await sorov.getByRole('button', { name: 'Tasdiqlash' }).click()
    await expect(sorov).toHaveCount(0)
    const d = await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)
    expect([d.chegirma, d.holat, d.salonchi?.ism, d.libos_qatorlari.map((l) => l.artikul)]).toEqual([100_000, 'vaqtinchalik', 'Gulnora', [ikkinchi.artikul]])
  })
  expect(xatolar).toEqual([])
})

test('hisobot → xarajatlar: modda, kiritish, tuzatish, bekor qilish, doimiy xarajat', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Hisobot')
  await nav(page).getByRole('button', { name: 'Xarajatlar', exact: true }).click()

  await test.step('yangi modda', async () => {
    await page.getByText('Xarajat moddalari', { exact: true }).click()
    await page.getByLabel('Yangi modda nomi').fill('Gul bezak')
    await page.getByRole('button', { name: "Modda qo'shish" }).click()
    await expect(page.getByText("Modda qo'shildi.")).toBeVisible()
  })

  await test.step('xarajat kiritish, summasini tuzatish va bekor qilish', async () => {
    const forma = page.locator('.blok.amal > .stack > .stack').first()
    await forma.getByLabel('Modda').selectOption({ label: 'Gul bezak' })
    await forma.getByLabel("Summa, so'm").fill('250000')
    await forma.getByLabel('Izoh').fill("To'y zali uchun")
    await forma.getByRole('button', { name: 'Xarajat kiritish' }).click()
    await expect(page.getByText('Xarajat yozildi.')).toBeVisible()
    const qator = page.locator('.tasdiq', { hasText: "To'y zali uchun" })
    await expect(qator).toContainText("Gul bezak · 250 000 so'm")
    await qator.getByText('Tuzatish', { exact: true }).click()
    await qator.getByLabel("Summa, so'm").fill('200000')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Xarajat tuzatildi.')).toBeVisible()
    await expect(qator).toContainText("200 000 so'm")
    await qator.getByText('Tuzatish', { exact: true }).click()
    await qator.getByRole('button', { name: 'Bekor qilish' }).click()
    await expect(page.getByText('Xarajat bekor qilindi.')).toBeVisible()
  })

  await test.step("doimiy oylik xarajat: qo'shish, summani o'zgartirish, o'chirish", async () => {
    const sarlavha = page.locator('summary', { hasText: /^Doimiy oylik xarajatlar/ })
    const blok = sarlavha.locator('..')
    await sarlavha.click()
    await blok.getByLabel('Modda').selectOption({ label: 'Gul bezak' })
    await blok.getByLabel("Summa, so'm").fill('300000')
    await blok.getByLabel('Izoh').last().fill('Har oy gul')
    await blok.getByRole('button', { name: "Doimiy xarajat qo'shish" }).click()
    await expect(page.getByText("Doimiy xarajat qo'shildi.")).toBeVisible()
    const qator = blok.locator('.tasdiq', { hasText: 'Har oy gul' })
    await qator.getByLabel('Summa').fill('350000')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Doimiy xarajat saqlandi.')).toBeVisible()
    await expect(qator).toContainText("350 000 so'm")
    await qator.getByRole('button', { name: "O'chirish" }).click()
    await expect(page.getByText("O'chirildi.")).toBeVisible()
  })
  expect(xatolar).toEqual([])
})

test("katalog: kategoriyalar, libos ta'miri, aksessuar donasi ta'miri", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Liboslar')

  await test.step("kategoriya: qo'shish, nomini o'zgartirish, o'chirish", async () => {
    await page.getByRole('tab', { name: "Ro'yxat" }).click()
    await page.getByRole('button', { name: 'Kategoriyalar' }).click()
    const oyna = page.getByRole('dialog')
    await oyna.getByPlaceholder(/^Yangi kategoriya/).fill('Kuyov kostyumi')
    await oyna.getByRole('button', { name: "Qo'shish" }).click()
    await expect(page.getByText("Kategoriya qo'shildi.")).toBeVisible()
    const qator = oyna.locator('.kategoriya-qator').last()
    await expect(qator.getByLabel('Kategoriya nomi')).toHaveValue('Kuyov kostyumi')
    await qator.getByLabel('Kategoriya nomi').fill('Kuyov libosi')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText("Kategoriya nomi o'zgartirildi.")).toBeVisible()
    await expect(qator.getByLabel('Kategoriya nomi')).toHaveValue('Kuyov libosi')
    await qator.getByRole('button', { name: "O'chirish" }).click()
    await expect(page.getByText("Kategoriya o'chirildi.")).toBeVisible()
    await expect(oyna.locator('.kategoriya-qator')).toHaveCount(2)
    await oyna.getByRole('button', { name: 'Yopish' }).click()
  })

  await test.step("libos ta'miri: berish va tugatish", async () => {
    await page.locator('.libos-karta', { hasText: 'E2E-2' }).click()
    const tafsilot = page.locator('.libos-tafsilot')
    await tafsilot.getByText(/^Ta'mir jurnali/).click()
    await tafsilot.getByLabel('Nima qilinadi').fill('Etagini qisqartirish')
    await tafsilot.getByLabel('Kim qiladi (usta)').fill('Usta Karim')
    await tafsilot.getByRole('button', { name: "Ta'mirga berish" }).click()
    await expect(page.getByText("Libos ta'mirga berildi.")).toBeVisible()
    await expect(tafsilot).toContainText("Ta'mirda: Etagini qisqartirish (Usta Karim)")
    await tafsilot.getByLabel("Ta'mir narxi").fill('50000')
    await tafsilot.getByRole('button', { name: "Ta'mirni tugatish" }).click()
    await expect(page.getByText("Ta'mir tugatildi, libos bo'sh.")).toBeVisible()
    await expect(tafsilot).toContainText("Etagini qisqartirish (Usta Karim) · 50 000 so'm")
    // natija xabari ochiq libos ichida, tugma yonida chiqadi (ro'yxat tepasida emas)
    await tafsilot.getByRole('button', { name: 'Narxlarni saqlash' }).click()
    await expect(tafsilot.getByRole('status')).toHaveText("O'zgartirildi.")
  })

  await test.step("aksessuar donasi ta'miri: berish va tugatish", async () => {
    await page.getByRole('tab', { name: 'Aksessuarlar' }).click()
    await page.locator('.zakaz-katak', { hasText: 'Fata Klassik' }).click()
    const t = page.locator('.aks-tafsilot')
    await expect(t.locator('.dona').first()).toBeVisible()  // tafsilot yuklanguncha sanalmasin
    const oldin = await t.locator('.dona').count()
    await t.getByText("Dona qo'shish", { exact: true }).click()
    await t.locator('details', { hasText: 'Bir dona narxi' }).getByRole('button', { name: "Qo'shish" }).click()
    await expect(t.locator('.dona')).toHaveCount(oldin + 1)
    const dona = (await t.locator('.dona').last().evaluate((e) => e.firstChild.textContent)).trim()  // yorliq — birinchi matn
    await t.getByText(/^Ta'mir \(/).click()
    await t.getByLabel('Dona', { exact: true }).selectOption({ label: dona })
    await t.getByLabel('Nima qilinadi').fill('Gulini tikish')
    await t.getByRole('button', { name: "Ta'mirga berish" }).click()
    await expect(t.getByRole('status')).toHaveText("Dona ta'mirga berildi.")  // xabar ochiq aksessuar ichida
    const qator = t.locator('.tasdiq', { hasText: 'Gulini tikish' })
    await qator.getByPlaceholder("Narxi, so'm").fill('30000')
    await qator.getByRole('button', { name: 'Tugatish' }).click()
    await expect(page.getByText(`${dona}: ta'mir tugadi.`)).toBeVisible()
  })
  expect(xatolar).toEqual([])
})

test("kassa: zalog tekshiruvi, inkassatsiya; rahbar: smena tuzatish, dashboard filial bo'yicha", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Sotuvchi', '2222')

  // Tayyorlov (API): smenada bo'lish, bugun olib ketiladigan zakaz — to'liq to'lab, hujjat zalogi bilan berish
  const smena = await apiSorov(page, 'GET', '/kassa/smena/')
  if (!smena.ochiq) await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  else await apiSorov(page, 'POST', '/kassa/smena/qoshilish/')
  const bosh = await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${iso(0)}&gacha=${iso(1)}`)
  const libos = bosh.find((l) => !l.band && !l.qulflangan && l.ijara_narxi > 0)  // naqd tushsin — inkassatsiyaga pul kerak
  expect(libos, JSON.stringify(bosh)).toBeTruthy()
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770022', fio: 'Zalog Sinov', dan: iso(0), gacha: iso(1), liboslar: [libos.id] })
  expect(z.id, JSON.stringify(z)).toBeTruthy()
  const t = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: z.jami })
  expect(t.detail, JSON.stringify(t)).toBeUndefined()

  await test.step("zakazlar: «Bugun» tasmasi va qo'ng'iroq tugmasi", async () => {
    await bolim(page, 'Zakazlar')
    const chip = page.locator('.bugun-tasma').getByRole('button', { name: /bugun olib ketadi/ })
    await expect(chip).toContainText(/\d+ bugun olib ketadi/)
    await chip.click()
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
    const qator = page.locator('.zakaz-jadval tbody tr', { hasText: 'Zalog Sinov' })
    await expect(qator).toBeVisible()
    await expect(page.locator('.zakaz-jadval tbody tr', { hasText: 'Storno Mijoz' })).toHaveCount(0)
    await expect(qator.getByRole('link', { name: "Zalog Sinov — qo'ng'iroq qilish" })).toHaveAttribute('href', 'tel:+998907770022')
    await page.screenshot({ path: 'test-results/zakazlar/2-bugun-tasmasi-keng.png', animations: 'disabled' })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: 'test-results/zakazlar/2-bugun-tasmasi-telefon.png', animations: 'disabled' })
    await page.setViewportSize({ width: 1280, height: 860 })
    await chip.click()  // qayta bosilsa filtr olinadi
    await expect(chip).toHaveAttribute('aria-pressed', 'false')
  })
  const b = await apiSorov(page, 'POST', `/zakazlar/${z.id}/berish/`, { zaloglar: [{ turi: 'hujjat', hujjat_turi: 'Haydovchilik guvohnomasi', hujjat_raqami: 'TEST-0001' }] })
  expect(b.holat, JSON.stringify(b)).toBe('berildi')

  await bolim(page, 'Kassa')
  await test.step('zalog tekshiruvi: «Joyida»', async () => {
    await nav(page).getByRole('button', { name: 'Zaloglar', exact: true }).click()
    const qator = page.locator('.tasdiq-qator', { hasText: `zakaz #${z.raqam}` })
    await qator.getByRole('button', { name: 'Joyida' }).click()
    await expect(qator).toContainText('· joyida')
  })

  await test.step('inkassatsiya: naqd pulni rahbarga', async () => {
    await nav(page).getByRole('button', { name: 'Inkassatsiya', exact: true }).click()
    await expect(page.getByRole('radiogroup', { name: 'Kimga' }).getByRole('radio', { checked: true })).toContainText('Rahbar')  // bitta rahbar — o'zi tanlanadi
    const klav = page.getByRole('group', { name: 'Raqamli klaviatura' })
    for (const k of ['1', '000', '0', '0']) await klav.getByRole('button', { name: k, exact: true }).click()
    await expect(page.locator('.pos-summa')).toContainText('100 000')
    await page.getByLabel('Izoh').fill('Kun oxiri')
    await page.getByRole('button', { name: 'Inkassatsiyani yozish' }).click()
    await expect(page.getByText('Inkassatsiya yozildi — rahbar Telegramda tasdiqlaydi.')).toBeVisible()
  })
  expect(xatolar).toEqual([])

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const rahbar = await ctx.newPage()
  const xatolar2 = xatolarniKuzat(rahbar)
  await kirish(rahbar, 'Rahbar', '1111')
  await test.step("smenalar tarixi: yopilgan smenani tuzatish", async () => {
    await bolim(rahbar, 'Kassa')
    await nav(rahbar).getByRole('button', { name: 'Smenalar tarixi', exact: true }).click()
    const yopilgan = rahbar.locator('.tasdiq-qator', { has: rahbar.getByRole('button', { name: 'Tuzatish' }) }).first()
    await yopilgan.getByLabel('Izoh').fill('Qayta sanaldi')
    await yopilgan.getByRole('button', { name: 'Tuzatish' }).click()
    await expect(rahbar.getByText('Smena tuzatildi.')).toBeVisible()
    await expect(rahbar.locator('.tasdiq-qator', { hasText: 'Qayta sanaldi' }).first()).toBeVisible()
  })
  await test.step("dashboard: filial tanlovi", async () => {
    await bolim(rahbar, 'Dashboard')
    const filial = rahbar.getByLabel('Filial', { exact: true })
    await filial.selectOption({ label: 'Filial: Chilonzor filiali' })
    await rahbar.waitForLoadState('networkidle')
    await expect(filial).not.toHaveValue('')
    await filial.selectOption('')
    await rahbar.waitForLoadState('networkidle')
  })
  expect(xatolar2).toEqual([])
  await ctx.close()
})
