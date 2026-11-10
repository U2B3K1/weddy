// Telefon (390px, maket 2026-11-10): pastki panel — Bosh, Zakazlar, Kassa, Profil; «Profil» menyusi yuqori panel ustida; xodim belgisi — menyu
// (profil rasmi va «Chiqish»).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

test('telefon: pastki panel, chap menyu va xodim menyusi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await kirish(page, 'Rahbar', '1111')
  const tab = page.getByRole('navigation', { name: "Asosiy bo'limlar" })

  await test.step("pastki panel (maket): Bosh, Zakazlar, Kassa, Profil; «Kassa» — to'lov qabul", async () => {
    await expect(tab.getByRole('button')).toHaveText(['Bosh', 'Zakazlar', 'Kassa', 'Profil'])
    // Kassa — bosh ekran: kassadagi naqd, Kirim / Chiqim; «Kirim» — to'lov qabul, «‹ Kassa» — orqaga
    await tab.getByRole('button', { name: 'Kassa' }).click()
    await expect(tab.getByRole('button', { name: 'Kassa' })).toHaveClass(/faol/)
    await expect(page.getByRole('region', { name: 'Kassadagi naqd' })).toBeVisible()
    await page.getByRole('button', { name: 'Kirim', exact: true }).click()
    await expect(page.locator('.kassa-orqaga')).toBeVisible()
    await page.locator('.kassa-orqaga').click()
    await expect(page.getByRole('region', { name: 'Kassadagi naqd' })).toBeVisible()
    // Zakazlar — uch tab, rasmli kartalar; «Yangi zakaz» — ro'yxat ostidagi katta tugma (pastki panelda «+» yo'q)
    await tab.getByRole('button', { name: 'Zakazlar' }).click()
    await expect(page.getByRole('tab', { name: 'Barchasi', selected: true })).toBeVisible()
    await page.getByRole('tab', { name: 'Kechikkan' }).click()
    await page.getByRole('tab', { name: 'Barchasi' }).click()
    await page.getByRole('button', { name: 'Yangi zakaz' }).click()
    await expect(page.getByRole('heading', { name: 'Yangi zakaz', level: 1 })).toBeVisible()
    await expect(tab.getByRole('button', { name: 'Zakazlar' })).toHaveClass(/faol/)  // yangi zakaz — Zakazlar oqimi (maket)
  })

  await test.step("shapka qatori: filial, lupa (qidiruv ochiladi), qo'ng'iroqcha", async () => {
    await expect(page.getByRole('search')).toBeHidden()
    await page.getByRole('button', { name: 'Zakaz qidirish' }).click()
    await expect(page.getByRole('search').getByLabel('Zakaz qidirish')).toBeVisible()
    await page.getByRole('button', { name: 'Zakaz qidirish' }).click()
    await expect(page.getByRole('search')).toBeHidden()
  })

  await test.step("«Profil» — alohida sahifa: xodim kartasi va qolgan bo'limlar (maket)", async () => {
    await tab.getByRole('button', { name: 'Profil' }).click()
    const profil = page.getByRole('region', { name: 'Profil' })
    await expect(profil).toContainText('Rahbar')
    for (const nom of ['Liboslar', 'Mijozlar', 'Hisobotlar', 'Sozlama']) await expect(page.locator('.profil-sahifa').getByRole('button', { name: nom, exact: true })).toBeVisible()
    await expect(page.locator('.profil-sahifa').getByRole('button', { name: 'Chiqish' })).toBeVisible()
    await page.screenshot({ path: 'test-results/mobil/profil.png' })
    await page.locator('.profil-sahifa').getByRole('button', { name: 'Liboslar', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Liboslar', level: 1 })).toBeVisible()
    await expect(tab.getByRole('button', { name: 'Profil' })).toHaveClass(/faol/)  // Profil ichidagi bo'lim — «Profil» belgilangan
  })

  await test.step('shapkadagi belgi — profil rasmi va «Chiqish» menyusi', async () => {
    await page.getByRole('button', { name: 'Rahbar: profil va chiqish' }).click()
    const menyu = page.getByRole('menu')
    await expect(menyu.getByRole('menuitem', { name: 'Profil rasmini yuklash' })).toBeVisible()
    await menyu.getByRole('menuitem', { name: 'Ilovadan chiqish' }).click({ trial: true, timeout: 5000 })
    await page.screenshot({ path: 'test-results/mobil/xodim-menyu.png' })
    await menyu.locator('input[type=file]').setInputFiles('public/kelinlar/2.jpg')
    await expect(page.locator('.shapka-xodim img')).toBeVisible()
    await page.getByRole('button', { name: 'Rahbar: profil va chiqish' }).click()
    await page.getByRole('menu').getByRole('menuitem', { name: 'Rasmni olib tashlash' }).click()
    await expect(page.locator('.shapka-xodim img')).toHaveCount(0)
  })
  expect(xatolar).toEqual([])
})
