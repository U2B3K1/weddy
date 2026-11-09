// R2 «Boshqaruv» (D2): libos pasporti, birlashgan «Zaloglar» hisoboti, Sozlamada yagona saqlash usuli (rekvizitlar),
// mijoz kartasidan «Yangi zakaz». Ma'lumot yaratilmaydi (rekvizit manzili o'zgaradi va asliga qaytariladi).
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const bolim = async (page, nom) => {
  const asosiy = nav(page).getByRole('button', { name: 'Asosiy', exact: true })
  if (await asosiy.isVisible()) await asosiy.click()
  await nav(page).getByRole('button', { name: nom, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

test('libos pasporti: hozir kimda, kelgusi bronlar; samaradorlik faqat rahbarga', async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Liboslar')
  await page.getByRole('tab', { name: "Ro'yxat" }).click()
  await test.step("ko'rsatkich kartasi-filtr va chapdagi filtr ustuni (maket uslubi)", async () => {
    const kpi = page.getByRole('region', { name: "Liboslar ko'rsatkichlari" })
    const faol = kpi.getByRole('button', { name: /^Faol liboslar: \d+$/ })
    await expect(faol).toHaveAttribute('aria-pressed', 'true')  // standart filtr
    const filtr = page.getByRole('complementary', { name: 'Filtrlar' })  // 1280 px — filtr ustuni bor, tablar yashirin
    await expect(page.getByRole('tablist', { name: 'Kategoriya' })).toHaveCount(0)
    const kartalar = page.locator('.libos-tor .libos-karta')
    const jami = await kartalar.count()
    // «Ijaraga tayyor» kartasi — filtr ustunidagi «Ijaraga tayyor» bilan bir xil holat va son
    const tayyor = kpi.getByRole('button', { name: /^Ijaraga tayyor: \d+$/ })
    const soni = Number((await tayyor.getAttribute('aria-label')).split(': ')[1])
    await tayyor.click()
    await expect(tayyor).toHaveAttribute('aria-pressed', 'true')
    await expect(filtr.getByRole('button', { name: /^Ijaraga tayyor/ })).toHaveAttribute('aria-pressed', 'true')
    await expect(kartalar).toHaveCount(soni)
    await page.screenshot({ path: 'test-results/liboslar/1-kpi-filtr-1280.png', animations: 'disabled' })
    await filtr.getByRole('button', { name: 'Filtrlarni tozalash' }).click()
    await expect(faol).toHaveAttribute('aria-pressed', 'true')
    await expect(kartalar).toHaveCount(jami)
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(page.getByRole('tablist', { name: 'Kategoriya' })).toBeVisible()  // telefonda filtrlar asboblar panelida
    await page.screenshot({ path: 'test-results/liboslar/2-telefon.png', animations: 'disabled' })
    await page.setViewportSize({ width: 1280, height: 860 })
  })
  await page.locator('.libos-karta', { hasText: 'E2E-1' }).click()
  const pasport = page.getByRole('region', { name: 'Libos pasporti' })
  await expect(pasport).toContainText('Hozir')
  await expect(pasport).toContainText('Kelgusi bronlar')
  await expect(pasport).toContainText("O'zini oqlashi")
  await expect(pasport).toContainText("Ijara narxi bo'yicha jami")
  // ro'yxatdagi bronlar soni serverdagi bilan bir xil (ko'pi bilan 4 tasi ko'rinadi, qolgani «Yana N ta»)
  const lid = await page.evaluate(async () => {
    const h = { 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'), Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` }
    const l = await (await fetch('http://127.0.0.1:8001/api/liboslar/', { headers: h })).json()
    const id = l.find((x) => x.artikul === 'E2E-1').id
    return (await (await fetch(`http://127.0.0.1:8001/api/liboslar/${id}/pasport/`, { headers: h })).json()).kelgusi.length
  })
  await expect(pasport.locator('.r2p-bronlar li')).toHaveCount(Math.min(lid, 4))

  // sotuvchi: pasport bor, lekin tannarx/qoplash yo'q
  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const sotuvchi = await ctx.newPage()
  await kirish(sotuvchi, 'Sotuvchi', '2222')
  await bolim(sotuvchi, 'Liboslar')
  await sotuvchi.getByRole('tab', { name: "Ro'yxat" }).click()
  await sotuvchi.locator('.libos-karta', { hasText: 'E2E-1' }).click()
  const sp = sotuvchi.getByRole('region', { name: 'Libos pasporti' })
  await expect(sp).toContainText('Kelgusi bronlar')
  await expect(sp).not.toContainText("O'zini oqlashi")
  await ctx.close()
  expect(xatolar).toEqual([])
})

test('hisobot: ikki zalog hisoboti bitta — «Zaloglar», ostida turi bo\'yicha', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Hisobotlar')
  await page.getByRole('tab', { name: 'Umumiy hisobot', exact: true }).click()
  const tur = page.getByLabel('Hisobot turi')
  await expect(tur.locator('option', { hasText: 'Zalog statistikasi' })).toHaveCount(0)
  await expect(tur.locator('option', { hasText: 'Zaloglar reestri' })).toHaveCount(0)
  await tur.selectOption({ label: 'Zaloglar' })
  const h = page.getByRole('region', { name: 'Zaloglar' })
  await expect(h).toBeVisible()
  await expect(h.locator('.r2h-qoshimcha')).toContainText("Davrda olinganlar — turi bo'yicha")
  await expect(h.locator('.r2h-qoshimcha tbody tr')).toHaveCount(3)  // Pul, Hujjat, Tillo buyum
  expect(xatolar).toEqual([])
})

test('sozlama: rekvizitlar umumiy «Saqlash» paneli orqali (B-37); kassada «sverka» yo\'q', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  const sozlama = async (_guruh, nom) => {  // bo'limlar Sozlama sahifasidagi chap ro'yxatda (Ndiz)
    await bolim(page, 'Sozlama')
    await page.getByRole('navigation', { name: 'Sozlama menyusi' }).getByRole('button', { name: nom, exact: true }).click()
  }
  await sozlama('Salon va xodimlar', 'Kassa')
  await expect(page.getByText('Smena yopishda terminal hisobotini solishtirish')).toBeVisible()
  await expect(page.locator('.sozlama-mazmun')).not.toContainText('sverka')

  await sozlama('Salon va xodimlar', 'Rekvizitlar')
  await expect(page.getByRole('button', { name: 'Rekvizitlarni saqlash' })).toHaveCount(0)
  const manzil = page.getByLabel('Manzil', { exact: true })
  const asl = await manzil.inputValue()
  await manzil.fill('Toshkent, Navoiy 1')
  const panel = page.getByRole('region', { name: "Saqlanmagan o'zgarishlar" })
  await panel.getByRole('button', { name: 'Saqlash' }).click()
  await expect(page.getByText('Rekvizitlar saqlandi.')).toBeVisible()
  await expect(panel).toHaveCount(0)
  await sozlama('Salon va xodimlar', 'Kassa')
  await sozlama('Salon va xodimlar', 'Rekvizitlar')
  await expect(manzil).toHaveValue('Toshkent, Navoiy 1')
  // asliga qaytarish; «Bekor qilish» ham tekshiriladi
  await manzil.fill('vaqtincha')
  await panel.getByRole('button', { name: 'Bekor qilish' }).click()
  await expect(manzil).toHaveValue('Toshkent, Navoiy 1')
  await manzil.fill(asl)
  await panel.getByRole('button', { name: 'Saqlash' }).click()
  await expect(page.getByText('Rekvizitlar saqlandi.')).toBeVisible()
  expect(xatolar).toEqual([])
})

test("mijoz kartasidan «Yangi zakaz» — Kassa › Yangi zakaz ochiladi", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Mijozlar')
  await page.locator('.mijoz-jadval tbody tr', { hasText: 'Storno Mijoz' }).click()
  await expect(page.getByRole('heading', { name: 'Storno Mijoz' })).toBeVisible()
  await page.locator('.karta-bosh').getByRole('button', { name: 'Yangi zakaz' }).click()
  await expect(page.getByRole('heading', { name: 'Storno Mijoz' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: 'Yangi zakaz', exact: true })).toHaveAttribute('aria-selected', 'true')
  expect(xatolar).toEqual([])
})

// Ilovaning o'z tokenlari bilan API so'rovi (sozlamani tez almashtirish uchun)
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

test("C-25: sotuvchi qo'shgan libos unga «kutmoqda» bo'lib ko'rinadi, rahbar rad etadi", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  const eski = await apiSorov(page, 'GET', '/sozlamalar/')
  await apiSorov(page, 'PATCH', '/sozlamalar/', { libos_tasdigi: true, sotuvchi_libos_qoshadi: true })
  try {
    const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
    const s = await ctx.newPage()
    await kirish(s, 'Sotuvchi', '2222')
    await bolim(s, 'Liboslar')
    await s.getByRole('tab', { name: "Ro'yxat" }).click()
    await s.getByRole('button', { name: "Libos qo'shish" }).click()
    const oyna = s.getByRole('dialog', { name: "Libos qo'shish" })
    await oyna.getByRole('textbox', { name: /^Artikul/ }).fill('RAD-1')
    await oyna.getByRole('textbox', { name: /^Nomi/ }).fill('Rad sinovi')
    await oyna.getByRole('button', { name: /^Qo'shish/ }).click()
    await expect(s.getByText("Libos rahbar tasdig'iga yuborildi.")).toBeVisible()
    // sotuvchi o'zi qo'shganini ko'radi (faqat ko'rish, tugmasiz)
    const blok = s.locator('.diqqat-blok', { hasText: "Rahbar tasdig'ini kutmoqda" })
    await expect(blok).toContainText('RAD-1')
    await expect(blok.getByRole('button')).toHaveCount(0)
    await ctx.close()

    await bolim(page, 'Liboslar')
    await page.getByRole('tab', { name: "Ro'yxat" }).click()
    const q = page.locator('.diqqat-blok .tasdiq', { hasText: 'RAD-1' })
    await q.getByRole('button', { name: 'Rad etish' }).click()
    const d = page.getByRole('dialog', { name: 'RAD-1 rad etilsinmi?' })
    await d.getByLabel('Sabab (ixtiyoriy)').fill('takror yozuv')
    await d.getByRole('button', { name: 'Ha, rad etish' }).click()
    await expect(page.getByText("RAD-1 rad etildi — arxivga o'tdi.")).toBeVisible()
    await expect(page.locator('.diqqat-blok .tasdiq', { hasText: 'RAD-1' })).toHaveCount(0)
  } finally {
    await apiSorov(page, 'PATCH', '/sozlamalar/', { libos_tasdigi: eski.libos_tasdigi, sotuvchi_libos_qoshadi: eski.sotuvchi_libos_qoshadi })
  }
  expect(xatolar).toEqual([])
})

test("C-11: Kunlik kassa va Xodimlar nazoratida «Seyf farqi» ustuni", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Hisobotlar')
  await page.getByRole('tab', { name: 'Umumiy hisobot', exact: true }).click()
  // ustunlar serverdan (davrda smena bo'lmasa jadval chizilmaydi); jadval bo'lsa — sarlavhada ham
  const kassa = await apiSorov(page, 'GET', '/hisobotlar/h/kassa/')
  expect(kassa.ustunlar.map((u) => u.nom)).toContain('Seyf farqi')
  const nazorat = await apiSorov(page, 'GET', '/hisobotlar/h/nazorat/')
  expect(nazorat.ustunlar.map((u) => u.nom)).toContain('Seyf farqi (ochganda)')
  await page.getByLabel('Hisobot turi').selectOption({ label: 'Kunlik kassa' })
  const h = page.getByRole('region', { name: 'Kunlik kassa' })
  await expect(h).toBeVisible()
  if (kassa.qatorlar.length) await expect(h.getByRole('columnheader', { name: 'Seyf farqi' })).toBeVisible()  // «Batafsil» siz ham
  expect(xatolar).toEqual([])
})

test("C-21: Sozlama › Avans qaytarish — «Avans qancha» (foiz va misol), umumiy panel bilan saqlanadi", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolim(page, 'Sozlama')
  await page.getByRole('navigation', { name: 'Sozlama menyusi' }).getByRole('button', { name: 'Avans qaytarish', exact: true }).click()
  const avans = page.locator('fieldset', { hasText: 'Avans qancha' })
  await expect(avans.getByLabel("Birinchi to'lov to'liq avans")).toBeChecked()
  await avans.getByRole('radio').nth(1).check()
  await avans.getByLabel('Avans, zakaz summasidan foiz').fill('30')
  await expect(avans).toContainText("3 000 000 lik zakazda 30% → avans 900 000")
  const panel = page.getByRole('region', { name: "Saqlanmagan o'zgarishlar" })
  await panel.getByRole('button', { name: 'Saqlash' }).click()
  await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
  expect((await apiSorov(page, 'GET', '/sozlamalar/')).avans_foizi).toBe(30)
  await avans.getByLabel("Birinchi to'lov to'liq avans").check()  // asliga qaytariladi
  await panel.getByRole('button', { name: 'Saqlash' }).click()
  await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
  expect((await apiSorov(page, 'GET', '/sozlamalar/')).avans_foizi).toBeNull()
  expect(xatolar).toEqual([])
})
