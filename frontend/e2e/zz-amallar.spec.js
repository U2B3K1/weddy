// Brauzerda hali sinalmagan tahrirlash/qo'shish/o'chirish amallari (PROGRESS: 33–41-qismlar).
// Fayl nomi «zz-» bilan — eng oxirida ishlaydi: filial qo'shadi, sozlamalarni o'zgartiradi, boshqa testlarga xalaqit bermasin.
import { expect, test } from '@playwright/test'
import { bolimga, QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

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

// _guruh — faqat o'qish uchun: guruhlar doim ochiq. Keng ekranda Sozlama ro'yxati chap panelda — Sozlama ichida bo'lsak,
// asosiy menyudagi «Sozlama» tugmasi yo'q, to'g'ridan-to'g'ri ro'yxatdan tanlanadi
async function sozlama(page, _guruh, nom) {
  const menyu = page.getByRole('navigation', { name: 'Sozlama menyusi' })
  if (!(await menyu.isVisible())) await bolimga(page, 'Sozlama')
  await menyu.getByRole('button', { name: nom, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

test('sozlama: filial, mavsumiy narx, tayyor chegirma, SMS shabloni', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')

  await test.step('filial: qo\'shish, tahrirlash, nofaol/faol', async () => {
    await sozlama(page, 'Salon va xodimlar', 'Filiallar')
    // yangi filial formasi — panel tepasidagi «Filial qo'shish» bilan ochiladi (kanvas), ko'rinadigan yorliqlar bilan (B-23)
    await page.getByRole('button', { name: "Filial qo'shish" }).click()
    const yangiFilial = page.locator('.stack', { has: page.locator('h4', { hasText: 'Yangi filial' }) }).last()
    await yangiFilial.getByLabel('Filial nomi').fill('Chilonzor')
    await yangiFilial.getByLabel('Manzil').fill('Bunyodkor 1')
    await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Filial qo'shildi.")).toBeVisible()
    const qator = page.locator('.tasdiq', { hasText: 'Chilonzor' })
    await expect(qator).toContainText('Bunyodkor 1')
    await qator.getByText('Tahrirlash').click()
    await qator.getByLabel('Nomi').fill('Chilonzor filiali')
    await qator.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Filial saqlandi.')).toBeVisible()
    const yangi = page.locator('.tasdiq', { hasText: 'Chilonzor filiali' })
    await yangi.getByText('Tahrirlash').click()  // faol/nofaol — tahrir ichida (qatorda faqat holat yorlig'i)
    await yangi.getByRole('button', { name: 'Nofaol qilish' }).click()
    await expect(yangi.locator('.soz-holat')).toHaveText('Nofaol')
    await yangi.getByRole('button', { name: 'Faollashtirish' }).click()
    await expect(yangi.locator('.soz-holat')).toHaveText('Faol')
  })

  await test.step('mavsumiy narx: qoida qo\'shish, tahrirlash, o\'chirish, olib tashlash', async () => {
    await sozlama(page, 'Narx va chegirma', 'Mavsumiy narx')
    const yoqilgan = page.getByLabel('Mavsumiy narx yoqilgan')  // panel sarlavhasidagi almashtirgich
    if (!(await yoqilgan.isChecked())) await yoqilgan.check()
    await page.getByText("Qoida qo'shish").click()
    await page.getByLabel('Nomi *', { exact: true }).fill('Dam olish kunlari')  // majburiy maydon « *» bilan (B-29)
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
    await page.getByRole('alertdialog').getByRole('button', { name: 'Ha, olib tashlash' }).click()  // tasdiq (B-07)
    await expect(page.getByText('Qoida olib tashlandi.')).toBeVisible()
    await expect(qoida).toHaveCount(0)
  })

  await test.step('tayyor chegirma: qo\'shish, summaga o\'tkazish, nofaol', async () => {
    await sozlama(page, 'Narx va chegirma', 'Tayyor chegirmalar')
    await page.getByRole('button', { name: "Chegirma qo'shish" }).click()  // forma panel tepasidagi tugma bilan ochiladi (kanvas)
    await page.getByPlaceholder('Nomi (masalan, Doimiy mijoz)').fill('Doimiy mijoz')
    await page.locator('.soz-qosh').getByLabel('Qiymat').fill('10')
    await page.getByRole('region', { name: 'Tayyor chegirmalar' }).getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Tayyor chegirma qo'shildi.")).toBeVisible()
    const qator = page.locator('.tasdiq', { hasText: 'Doimiy mijoz' })
    await expect(qator).toContainText('Doimiy mijoz · 10%')
    await qator.getByRole('button', { name: 'Tahrirlash' }).click()
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
    await page.getByRole('button', { name: /^Eskiz SMS/ }).click()  // xizmat kartasi — sozlamasi kartalar ostida ochiladi
    await page.getByLabel(/^Yuboruvchi nomi/).fill('LIBOSA')
    await page.getByLabel('«Ertaga olib ketish» shabloni').fill('{salon}: ertaga {sana} libosni olib ketasiz.')
    await page.getByRole('region', { name: 'Eskiz SMS sozlamasi' }).getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Saqlandi.', { exact: true })).toBeVisible()
    await sozlama(page, 'Salon va xodimlar', 'Filiallar')
    await sozlama(page, "Ko'rinish va xabarlar", 'Integratsiyalar')  // qayta ochilganda serverdan o'qiladi
    await page.getByRole('button', { name: /^Eskiz SMS/ }).click()
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
    // B-34: jadval; qo'shish va tahrirlash — oynada
    await page.getByRole('button', { name: "Salonchi qo'shish", exact: true }).click()  // tablar qatori o'ngidagi tilla tugma
    const oyna = page.getByRole('dialog', { name: "Salonchi qo'shish" })
    await oyna.getByLabel('Ism').fill('Gulnora')
    await oyna.getByLabel('Salon nomi').fill('Gul salon')
    await oyna.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Salonchi qo'shildi.")).toBeVisible()
    const qator = page.locator('.r2s-jadval tbody tr', { hasText: 'Gulnora' })
    await expect(qator).toContainText('Gul salon')
    await qator.getByRole('button', { name: /Gulnora/ }).click()  // kanvas: tanlangan salonchi o'ng panelda, «Tahrirlash» — o'sha yerda
    await page.getByRole('region', { name: 'Gulnora tafsiloti' }).getByRole('button', { name: 'Tahrirlash' }).click()
    const tahrir = page.getByRole('dialog', { name: 'Gulnora' })
    await tahrir.getByLabel('Telefon').fill('+998901234567')
    await tahrir.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Salonchi saqlandi.')).toBeVisible()
    await expect(qator).toContainText('+998 90 123 45 67')
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
    // rahbar qarori — qo'ng'iroqcha menyusidagi «Qaroringiz kerak» bo'limida
    await bolim(page, 'Dashboard')
    await page.getByRole('button', { name: /^Bildirishnomalar/ }).click()
    const sorov = page.getByRole('region', { name: 'Qaroringiz kerak' }).locator('.tasdiq-qator', { hasText: `#${z.raqam}` })
    await expect(sorov).toContainText("chegirma 100 000 so'm")
    await sorov.getByRole('button', { name: 'Tasdiqlash' }).click()
    await expect(sorov).toHaveCount(0)
    const d = await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)
    expect([d.chegirma, d.holat, d.salonchi?.ism, d.libos_qatorlari.map((l) => l.artikul)]).toEqual([100_000, 'vaqtinchalik', 'Gulnora', [ikkinchi.artikul]])
  })
  expect(xatolar).toEqual([])
})

test('hisobot → xarajatlar: xarajat turi, kiritish, tuzatish, bekor qilish, doimiy xarajat', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Hisobotlar')
  await page.getByRole('tab', { name: 'Xarajatlar', exact: true }).click()

  await test.step('yangi xarajat turi', async () => {
    const turlar = page.locator('details', { has: page.locator('summary', { hasText: /^Xarajat turlari$/ }) })
    await turlar.locator('summary').click()
    await turlar.getByLabel('Yangi xarajat turi').fill('Gul bezak')
    await turlar.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Xarajat turi qo'shildi.")).toBeVisible()
  })

  await test.step('xarajat kiritish (oyna), summasini tuzatish va bekor qilish', async () => {
    await page.getByRole('button', { name: 'Xarajat kiritish', exact: true }).click()  // tablar qatori o'ngidagi tilla tugma (kanvas)
    const oyna = page.getByRole('dialog', { name: "Xarajat qo'shish" })
    await oyna.getByLabel('Xarajat turi').selectOption({ label: 'Gul bezak' })
    await oyna.getByLabel("Summa, so'm").fill('250000')
    await oyna.getByLabel('Izoh').fill("To'y zali uchun")
    await oyna.getByRole('button', { name: 'Xarajat kiritish' }).click()
    await expect(page.getByText('Xarajat yozildi.')).toBeVisible()
    await expect(oyna).toBeHidden()
    const qator = page.locator('.r2-xarajat-jadval tbody tr', { hasText: "To'y zali uchun" })
    await expect(qator).toContainText('Gul bezak')
    await expect(qator).toContainText('250 000')
    await qator.getByRole('button', { name: 'Tuzatish' }).click()
    const tuzatish = page.getByRole('dialog', { name: /^Xarajatni tuzatish/ })
    await tuzatish.getByLabel("Summa, so'm").fill('200000')
    await tuzatish.getByRole('button', { name: 'Saqlash' }).click()
    await expect(page.getByText('Xarajat tuzatildi.')).toBeVisible()
    await expect(qator).toContainText('200 000')
    await qator.getByRole('button', { name: 'Tuzatish' }).click()
    await tuzatish.getByRole('button', { name: 'Bekor qilish' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Ha, bekor qilish' }).click()  // tasdiq (B-07)
    await expect(page.getByText('Xarajat bekor qilindi.')).toBeVisible()
    await expect(qator).toContainText('Rad etilgan')
  })

  await test.step("doimiy oylik xarajat: qo'shish, summani o'zgartirish, o'chirish", async () => {
    const blok = page.getByRole('region', { name: 'Doimiy xarajatlar' })  // kanvas: o'ng ustundagi panel
    await blok.getByRole('button', { name: '+ Doimiy xarajat' }).click()
    await blok.getByLabel('Xarajat turi').selectOption({ label: 'Gul bezak' })
    await blok.getByLabel("Summa, so'm").fill('300000')
    await blok.getByLabel('Izoh').last().fill('Har oy gul')
    await blok.getByRole('button', { name: "Doimiy xarajat qo'shish" }).click()
    await expect(page.getByText("Doimiy xarajat qo'shildi.")).toBeVisible()
    const qator = blok.locator('.tasdiq', { hasText: 'Har oy gul' })
    await qator.getByRole('button', { name: 'Tahrirlash' }).click()
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
    await page.getByRole('alertdialog').getByRole('button', { name: "Ha, o'chirish" }).click()  // tasdiq (B-07)
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
    await t.locator('.aks-forma', { hasText: 'Bir dona narxi' }).getByRole('button', { name: "Qo'shish" }).click()
    await expect(t.locator('.dona')).toHaveCount(oldin + 1)
    const dona = (await t.locator('.dona').last().evaluate((e) => e.firstChild.textContent)).trim()  // yorliq — birinchi matn
    await t.getByRole('button', { name: "Ta'mirga berish" }).click()  // panel pastidagi tugma formani ochadi
    await t.getByLabel('Dona', { exact: true }).selectOption({ label: dona })
    await t.getByLabel('Nima qilinadi').fill('Gulini tikish')
    await t.getByRole('button', { name: "Ta'mirga yuborish" }).click()
    await expect(t.getByRole('status')).toHaveText("Dona ta'mirga berildi.")  // xabar ochiq aksessuar ichida
    const qator = t.locator('.tasdiq', { hasText: 'Gulini tikish' })
    await qator.getByPlaceholder("Narxi, so'm").fill('30000')
    await qator.getByRole('button', { name: 'Tugatish' }).click()
    await expect(page.getByText(`${dona}: ta'mir tugadi.`)).toBeVisible()
  })
  expect(xatolar).toEqual([])
})

test("kassa: garov tekshiruvi, inkassatsiya; rahbar: smena tuzatish, dashboard filial bo'yicha", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Sotuvchi', '2222')

  // Tayyorlov (API): smenada bo'lish, bugun olib ketiladigan zakaz — to'liq to'lab, hujjat garovi bilan berish
  const smena = await apiSorov(page, 'GET', '/kassa/smena/')
  if (!smena.ochiq) await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  else await apiSorov(page, 'POST', '/kassa/smena/qoshilish/')
  const bosh = await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${iso(0)}&gacha=${iso(1)}`)
  const libos = bosh.find((l) => !l.band && !l.qulflangan && l.ijara_narxi > 0)  // naqd tushsin — inkassatsiyaga pul kerak
  expect(libos, JSON.stringify(bosh)).toBeTruthy()
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770022', fio: 'Garov Sinov', dan: iso(0), gacha: iso(1), liboslar: [libos.id] })
  expect(z.id, JSON.stringify(z)).toBeTruthy()
  const t = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: z.jami })
  expect(t.detail, JSON.stringify(t)).toBeUndefined()

  await test.step("zakazlar: ko'rsatkich kartasi-filtr, «Bugun» ustuni va qo'ng'iroq tugmasi", async () => {
    await bolim(page, 'Zakazlar')
    const chip = page.getByRole('region', { name: "Zakazlar ko'rsatkichlari" }).getByRole('button', { name: /^Bugun olib ketadi: [1-9]\d*$/ })
    await expect(chip).toBeVisible()
    // o'ng ustun faqat keng ekranda (1440+; 1280 da jadval ustunlari sig'masin): bugun olib ketadiganlar ism bilan
    const ustun = page.getByRole('complementary', { name: 'Bugun' })
    await expect(ustun).toHaveCount(0)
    await page.setViewportSize({ width: 1600, height: 900 })
    await expect(ustun.getByRole('region', { name: /^Olib ketadi: \d+$/ })).toContainText('Garov Sinov')
    await page.screenshot({ path: 'test-results/zakazlar/1-bugun-ustuni-1600.png', animations: 'disabled' })
    await page.setViewportSize({ width: 1280, height: 860 })
    await chip.click()
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
    const qator = page.locator('.zakaz-jadval tbody tr', { hasText: 'Garov Sinov' })
    await expect(qator).toBeVisible()
    await expect(page.locator('.zakaz-jadval tbody tr', { hasText: 'Storno Mijoz' })).toHaveCount(0)
    await expect(qator.getByRole('link', { name: "Garov Sinov — qo'ng'iroq qilish" })).toHaveAttribute('href', 'tel:+998907770022')
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
  await test.step('garov tekshiruvi: «Joyida»', async () => {
    await page.getByRole('tab', { name: 'Garovlar', exact: true }).click()
    // kanvas: jadval qatoridagi katakcha «joyida» deb belgilaydi
    const qator = page.locator('.zalog-jadval tbody tr', { hasText: `#${z.raqam}` })
    await qator.getByRole('checkbox').click()
    await expect(qator).toContainText('joyida ✓')
  })

  await test.step('inkassatsiya: naqd pulni rahbarga', async () => {
    await page.getByRole('tab', { name: 'Inkassatsiya', exact: true }).click()
    await expect(page.getByRole('radiogroup', { name: 'Kimga' }).getByRole('radio', { checked: true })).toContainText('Rahbar')  // bitta rahbar — o'zi tanlanadi
    const klav = page.getByRole('group', { name: 'Raqamli klaviatura' })
    for (const k of ['1', '000', '0', '0']) await klav.getByRole('button', { name: k, exact: true }).click()
    await expect(page.locator('.pos-summa')).toContainText('100 000')
    await page.getByLabel('Izoh').fill('Kun oxiri')
    await page.getByRole('button', { name: 'Rahbarga topshirish' }).click()  // C-27: tugma kimga berilishini aytadi
    await expect(page.getByText('Inkassatsiya yozildi — rahbar Telegramda tasdiqlaydi.')).toBeVisible()
  })
  expect(xatolar).toEqual([])

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const rahbar = await ctx.newPage()
  const xatolar2 = xatolarniKuzat(rahbar)
  await kirish(rahbar, 'Rahbar', '1111')
  await test.step("smenalar tarixi: yopilgan smenani tuzatish", async () => {
    await bolim(rahbar, 'Kassa')
    await rahbar.getByRole('tab', { name: 'Smenalar tarixi', exact: true }).click()
    // kanvas: jadvaldan yopilgan smena tanlanadi, o'ngdagi tafsilotda «Tuzatish» — oyna ochiladi
    await rahbar.locator('.tarix-jadval tbody tr', { hasText: 'Yopilgan' }).first().click()
    const tafsilot = rahbar.getByRole('region', { name: 'Smena tafsiloti' })
    await tafsilot.getByRole('button', { name: 'Tuzatish' }).click()
    const oyna = rahbar.getByRole('dialog', { name: /^Smenani tuzatish/ })
    await oyna.getByLabel('Izoh').fill('Qayta sanaldi')
    await oyna.getByRole('button', { name: 'Tuzatishni saqlash' }).click()
    await expect(oyna).toHaveCount(0)
    await expect(rahbar.getByText('Smena tuzatildi.')).toBeVisible()
    await expect(tafsilot).toContainText('Qayta sanaldi')
  })
  await test.step("dashboard: filial tanlovi", async () => {
    await bolim(rahbar, 'Dashboard')
    const filial = rahbar.getByLabel('Filial', { exact: true })
    await filial.selectOption({ label: 'Chilonzor filiali' })
    await rahbar.waitForLoadState('networkidle')
    await expect(filial).not.toHaveValue('')
    await filial.selectOption('')
    await rahbar.waitForLoadState('networkidle')
  })
  expect(xatolar2).toEqual([])
  await ctx.close()
})
